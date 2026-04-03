from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from cloud.db import get_connection
from cloud.models.events import LogMessage
from cloud.services.websocket_manager import WebSocketManager

KST = ZoneInfo("Asia/Seoul")


class DBService:
    def __init__(self, websocket_manager: WebSocketManager, db_path: str) -> None:
        self.websocket_manager = websocket_manager
        self.db_path = db_path

    @staticmethod
    def _row_to_event(row: Any, include_internal: bool = False) -> Dict[str, Any]:
        try:
            details = json.loads(row["details_json"])
        except json.JSONDecodeError:
            details = {}

        clip_status = row["clip_status"] if row["clip_status"] else "NONE"
        has_clip = bool(clip_status == "READY" and row["clip_path"])

        payload = {
            "id": row["id"],
            "edge_id": row["edge_id"],
            "event_type": row["event_type"],
            "details": details,
            "log_risk_level": row["log_risk_level"],
            "operation_mode": row["operation_mode"],
            "timestamp": row["timestamp"],
            "event_uid": row["event_uid"],
            "clip_status": clip_status,
            "clip_started_at": row["clip_started_at"],
            "clip_ended_at": row["clip_ended_at"],
            "clip_duration_sec": row["clip_duration_sec"],
            "clip_created_at": row["clip_created_at"],
            "has_clip": has_clip,
        }
        if include_internal:
            payload["clip_path"] = row["clip_path"]
        return payload

    async def log_event(self, event_data: Dict[str, Any]) -> LogMessage:
        message = LogMessage(**event_data)

        def _write() -> int:
            with get_connection(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO event_logs (
                        edge_id, event_type, details_json,
                        log_risk_level, operation_mode, timestamp,
                        event_uid, clip_status, clip_path,
                        clip_started_at, clip_ended_at, clip_duration_sec, clip_created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        message.edge_id,
                        message.event_type,
                        json.dumps(message.details, ensure_ascii=False),
                        message.log_risk_level,
                        message.operation_mode,
                        message.timestamp.isoformat(),
                        message.event_uid,
                        message.clip_status,
                        message.clip_path,
                        message.clip_started_at.isoformat() if message.clip_started_at else None,
                        message.clip_ended_at.isoformat() if message.clip_ended_at else None,
                        message.clip_duration_sec,
                        message.clip_created_at.isoformat() if message.clip_created_at else None,
                    ),
                )
                conn.commit()
                return int(cursor.lastrowid)

        inserted_id = await asyncio.to_thread(_write)

        event_payload = {
            **message.model_dump(mode="json"),
            "id": inserted_id,
            "has_clip": bool(message.clip_status == "READY" and message.clip_path),
        }
        await self.websocket_manager.broadcast(
            "logs",
            {"type": "LOG", "data": event_payload},
        )

        if message.log_risk_level in {"CRITICAL", "HIGH"}:
            await self.websocket_manager.broadcast(
                "alerts",
                {
                    "type": "SYSTEM_ALERT",
                    "level": message.log_risk_level,
                    "message": message.details.get("description", message.event_type),
                    "edge_id": message.edge_id,
                    "timestamp": datetime.now(KST).isoformat(),
                },
            )

        return message

    def get_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, edge_id, event_type, details_json,
                       log_risk_level, operation_mode, timestamp,
                       event_uid, clip_status, clip_path, clip_started_at,
                       clip_ended_at, clip_duration_sec, clip_created_at
                FROM event_logs
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [self._row_to_event(row) for row in rows]

    def get_event_by_id(self, log_id: int, include_internal: bool = False) -> Optional[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, edge_id, event_type, details_json,
                       log_risk_level, operation_mode, timestamp,
                       event_uid, clip_status, clip_path, clip_started_at,
                       clip_ended_at, clip_duration_sec, clip_created_at
                FROM event_logs
                WHERE id = ?
                """,
                (log_id,),
            ).fetchone()
        if not row:
            return None
        return self._row_to_event(row, include_internal=include_internal)

    def get_event_by_event_uid(
        self,
        event_uid: str,
        include_internal: bool = False,
    ) -> Optional[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, edge_id, event_type, details_json,
                       log_risk_level, operation_mode, timestamp,
                       event_uid, clip_status, clip_path, clip_started_at,
                       clip_ended_at, clip_duration_sec, clip_created_at
                FROM event_logs
                WHERE event_uid = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (event_uid,),
            ).fetchone()
        if not row:
            return None
        return self._row_to_event(row, include_internal=include_internal)

    def set_clip_ready_by_event_uid(
        self,
        event_uid: str,
        edge_id: str,
        clip_path: str,
        clip_started_at: str,
        clip_ended_at: str,
        duration_sec: float,
    ) -> Optional[Dict[str, Any]]:
        now_iso = datetime.now(KST).isoformat()
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                UPDATE event_logs
                SET clip_status = 'READY',
                    clip_path = ?,
                    clip_started_at = ?,
                    clip_ended_at = ?,
                    clip_duration_sec = ?,
                    clip_created_at = ?
                WHERE event_uid = ?
                  AND edge_id = ?
                """,
                (
                    clip_path,
                    clip_started_at,
                    clip_ended_at,
                    duration_sec,
                    now_iso,
                    event_uid,
                    edge_id,
                ),
            )
            conn.commit()
        return self.get_event_by_event_uid(event_uid, include_internal=True) # include_internal=True 추가

    def set_clip_failed_by_event_uid(
        self,
        event_uid: str,
        edge_id: str,
        error_message: str | None = None,
    ) -> Optional[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, details_json
                FROM event_logs
                WHERE event_uid = ?
                  AND edge_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (event_uid, edge_id),
            ).fetchone()
            if not row:
                return None

            try:
                details = json.loads(row["details_json"])
            except json.JSONDecodeError:
                details = {}

            if error_message:
                details["clip_error"] = error_message

            conn.execute(
                """
                UPDATE event_logs
                SET details_json = ?,
                    clip_status = 'FAILED',
                    clip_path = NULL,
                    clip_duration_sec = NULL,
                    clip_created_at = NULL
                WHERE id = ?
                """,
                (json.dumps(details, ensure_ascii=False), row["id"]),
            )
            conn.commit()
        return self.get_event_by_event_uid(event_uid)

    def list_expired_clip_candidates(self, cutoff_iso: str) -> List[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, clip_path
                FROM event_logs
                WHERE clip_status = 'READY'
                  AND clip_path IS NOT NULL
                  AND clip_created_at IS NOT NULL
                  AND clip_created_at <= ?
                """,
                (cutoff_iso,),
            ).fetchall()
        return [{"id": int(row["id"]), "clip_path": row["clip_path"]} for row in rows]

    def mark_clips_expired(self, log_ids: List[int]) -> int:
        if not log_ids:
            return 0

        placeholders = ",".join("?" for _ in log_ids)
        with get_connection(self.db_path) as conn:
            cursor = conn.execute(
                f"""
                UPDATE event_logs
                SET clip_status = 'EXPIRED',
                    clip_path = NULL
                WHERE id IN ({placeholders})
                """,
                tuple(log_ids),
            )
            conn.commit()
            return cursor.rowcount

    async def broadcast_log_update(self, event_data: Dict[str, Any]) -> None:
        await self.websocket_manager.broadcast(
            "logs",
            {"type": "LOG_UPDATE", "data": event_data},
        )
