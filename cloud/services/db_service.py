from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List

from cloud.db import get_connection
from cloud.models.events import LogMessage
from cloud.services.websocket_manager import WebSocketManager


class DBService:
    def __init__(self, websocket_manager: WebSocketManager, db_path: str) -> None:
        self.websocket_manager = websocket_manager
        self.db_path = db_path

    async def log_event(self, event_data: Dict[str, Any]) -> LogMessage:
        message = LogMessage(**event_data)

        def _write() -> None:
            with get_connection(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO event_logs (
                        edge_id, event_type, details_json,
                        log_risk_level, operation_mode, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        message.edge_id,
                        message.event_type,
                        json.dumps(message.details, ensure_ascii=False),
                        message.log_risk_level,
                        message.operation_mode,
                        message.timestamp.isoformat(),
                    ),
                )
                conn.commit()

        await asyncio.to_thread(_write)

        await self.websocket_manager.broadcast(
            "logs",
            {"type": "LOG", "data": message.model_dump(mode="json")},
        )

        if message.log_risk_level in {"CRITICAL", "HIGH"}:
            await self.websocket_manager.broadcast(
                "alerts",
                {
                    "type": "SYSTEM_ALERT",
                    "level": message.log_risk_level,
                    "message": message.details.get("description", message.event_type),
                    "edge_id": message.edge_id,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        return message

    def get_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT edge_id, event_type, details_json,
                       log_risk_level, operation_mode, timestamp
                FROM event_logs
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        events: List[Dict[str, Any]] = []
        for row in rows:
            try:
                details = json.loads(row["details_json"])
            except json.JSONDecodeError:
                details = {}

            events.append(
                {
                    "edge_id": row["edge_id"],
                    "event_type": row["event_type"],
                    "details": details,
                    "log_risk_level": row["log_risk_level"],
                    "operation_mode": row["operation_mode"],
                    "timestamp": row["timestamp"],
                }
            )

        return events
