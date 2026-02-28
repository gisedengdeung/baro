from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import HTTPException, status

from cloud.db import get_connection
from cloud.services.mobile_push_service import MobilePushService
from cloud.services.websocket_manager import WebSocketManager


class IncidentService:
    def __init__(
        self,
        db_path: str,
        websocket_manager: WebSocketManager,
        mobile_push_service: MobilePushService,
        snapshot_dir: str,
    ) -> None:
        self.db_path = db_path
        self.websocket_manager = websocket_manager
        self.mobile_push_service = mobile_push_service
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _snapshot_url(incident_id: str) -> str:
        return f"/api/incidents/{incident_id}/snapshot"

    @staticmethod
    def _parse_details(raw: Any) -> Dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        try:
            return json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return {}

    def _row_to_dict(self, row: Any) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "edge_id": row["edge_id"],
            "incident_type": row["incident_type"],
            "severity": row["severity"],
            "zone_id": row["zone_id"],
            "status": row["status"],
            "details": self._parse_details(row["details_json"]),
            "snapshot_url": self._snapshot_url(row["id"]) if row["snapshot_path"] else None,
            "detected_at": row["detected_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    async def create_incident(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        incident_id = str(uuid4())
        now = self._now_iso()
        detected_at = payload.get("detected_at") or now

        def _write() -> None:
            with get_connection(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO incidents (
                        id, edge_id, incident_type, severity, zone_id,
                        status, details_json, snapshot_path, detected_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, 'OPEN', ?, NULL, ?, ?, ?)
                    """,
                    (
                        incident_id,
                        payload.get("edge_id", "edge-default"),
                        payload.get("incident_type", "UNKNOWN_INCIDENT"),
                        payload.get("severity", "HIGH"),
                        payload.get("zone_id"),
                        json.dumps(payload.get("details", {}), ensure_ascii=False),
                        detected_at,
                        now,
                        now,
                    ),
                )
                conn.commit()

        await asyncio.to_thread(_write)
        incident = self.get_incident(incident_id)
        if incident is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Incident create failed")

        await self.websocket_manager.broadcast(
            "alerts",
            {
                "type": "INCIDENT_ALERT",
                "level": incident["severity"],
                "message": incident["details"].get("description", incident["incident_type"]),
                "edge_id": incident["edge_id"],
                "timestamp": now,
                "data": incident,
            },
        )
        await self.mobile_push_service.notify_incident(incident)
        return incident

    async def set_snapshot(self, incident_id: str, file_bytes: bytes, filename: str | None = None) -> str:
        incident = self.get_incident(incident_id)
        if incident is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

        suffix = ".jpg"
        if filename and "." in filename:
            ext = "." + filename.rsplit(".", 1)[-1].lower()
            if ext in {".jpg", ".jpeg", ".png", ".webp"}:
                suffix = ext

        snapshot_path = self.snapshot_dir / f"{incident_id}{suffix}"

        def _write_file_and_update_db() -> None:
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot_path.write_bytes(file_bytes)

            with get_connection(self.db_path) as conn:
                conn.execute(
                    """
                    UPDATE incidents
                    SET snapshot_path = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (str(snapshot_path), self._now_iso(), incident_id),
                )
                conn.commit()

        await asyncio.to_thread(_write_file_and_update_db)
        return self._snapshot_url(incident_id)

    def get_snapshot_path(self, incident_id: str) -> Optional[Path]:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT snapshot_path FROM incidents WHERE id = ?",
                (incident_id,),
            ).fetchone()
        if row is None or not row["snapshot_path"]:
            return None
        path = Path(row["snapshot_path"])
        return path if path.exists() else None

    def get_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, edge_id, incident_type, severity, zone_id, status,
                       details_json, snapshot_path, detected_at, created_at, updated_at
                FROM incidents
                WHERE id = ?
                """,
                (incident_id,),
            ).fetchone()
        return self._row_to_dict(row) if row is not None else None

    def list_incidents(
        self,
        limit: int = 100,
        edge_id: str | None = None,
        status_filter: str | None = None,
    ) -> List[Dict[str, Any]]:
        limit = max(1, min(limit, 500))

        clauses: List[str] = []
        params: List[Any] = []
        if edge_id:
            clauses.append("edge_id = ?")
            params.append(edge_id)
        if status_filter:
            clauses.append("status = ?")
            params.append(status_filter)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"""
            SELECT id, edge_id, incident_type, severity, zone_id, status,
                   details_json, snapshot_path, detected_at, created_at, updated_at
            FROM incidents
            {where_sql}
            ORDER BY detected_at DESC
            LIMIT ?
        """
        params.append(limit)

        with get_connection(self.db_path) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def update_status(self, incident_id: str, status_value: str) -> Optional[Dict[str, Any]]:
        now = self._now_iso()
        with get_connection(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE incidents SET status = ?, updated_at = ? WHERE id = ?",
                (status_value, now, incident_id),
            )
            conn.commit()
            if cursor.rowcount <= 0:
                return None
        return self.get_incident(incident_id)
