from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any, Dict, List
from uuid import uuid4

from loguru import logger

from cloud.db import get_connection


class MobilePushService:
    """FCM 연동 전 단계: 디바이스 토큰 관리 + 알림 fan-out 추적."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).isoformat()

    def register_device(
        self,
        user_id: str,
        platform: str,
        fcm_token: str,
        edge_scope: List[str],
    ) -> Dict[str, Any]:
        now = self._now_iso()

        with get_connection(self.db_path) as conn:
            existing = conn.execute(
                "SELECT id FROM mobile_devices WHERE fcm_token = ?",
                (fcm_token,),
            ).fetchone()

            if existing is None:
                device_id = str(uuid4())
                conn.execute(
                    """
                    INSERT INTO mobile_devices (
                        id, user_id, platform, fcm_token, edge_scope_json,
                        last_notified_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?)
                    """,
                    (
                        device_id,
                        user_id,
                        platform,
                        fcm_token,
                        json.dumps(edge_scope, ensure_ascii=False),
                        now,
                        now,
                    ),
                )
            else:
                device_id = existing["id"]
                conn.execute(
                    """
                    UPDATE mobile_devices
                    SET user_id = ?, platform = ?, edge_scope_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        user_id,
                        platform,
                        json.dumps(edge_scope, ensure_ascii=False),
                        now,
                        device_id,
                    ),
                )
            conn.commit()

        return self.get_device(device_id)

    def get_device(self, device_id: str) -> Dict[str, Any]:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, user_id, platform, fcm_token, edge_scope_json,
                       last_notified_at, created_at, updated_at
                FROM mobile_devices
                WHERE id = ?
                """,
                (device_id,),
            ).fetchone()

        if row is None:
            raise KeyError("device not found")

        try:
            edge_scope = json.loads(row["edge_scope_json"])
        except json.JSONDecodeError:
            edge_scope = []

        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "platform": row["platform"],
            "fcm_token": row["fcm_token"],
            "edge_scope": edge_scope,
            "last_notified_at": row["last_notified_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def delete_device(self, device_id: str, user_id: str) -> bool:
        with get_connection(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM mobile_devices WHERE id = ? AND user_id = ?",
                (device_id, user_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    async def notify_incident(self, incident: Dict[str, Any]) -> int:
        edge_id = incident.get("edge_id", "")

        def _load_targets() -> List[Dict[str, Any]]:
            with get_connection(self.db_path) as conn:
                rows = conn.execute(
                    """
                    SELECT id, user_id, fcm_token, edge_scope_json
                    FROM mobile_devices
                    """
                ).fetchall()

            targets: List[Dict[str, Any]] = []
            for row in rows:
                try:
                    scope = json.loads(row["edge_scope_json"])
                except json.JSONDecodeError:
                    scope = []

                if scope and edge_id not in scope:
                    continue

                targets.append(
                    {
                        "id": row["id"],
                        "user_id": row["user_id"],
                        "fcm_token": row["fcm_token"],
                    }
                )
            return targets

        targets = await asyncio.to_thread(_load_targets)
        if not targets:
            return 0

        # NOTE: FCM/APNs 실연동 전 단계이므로 전달 대상 수를 기록만 수행.
        logger.info(
            "모바일 푸시 대상 {}건 (incident_id={}, type={}, edge={})",
            len(targets),
            incident.get("id"),
            incident.get("incident_type"),
            edge_id,
        )

        now = self._now_iso()

        def _mark_notified() -> None:
            with get_connection(self.db_path) as conn:
                conn.executemany(
                    "UPDATE mobile_devices SET last_notified_at = ?, updated_at = ? WHERE id = ?",
                    [(now, now, t["id"]) for t in targets],
                )
                conn.commit()

        await asyncio.to_thread(_mark_notified)
        return len(targets)
