from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from cloud.db import get_connection

KST = ZoneInfo("Asia/Seoul")


class ZoneService:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def get_all_zones(self) -> List[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, name, points_json
                FROM danger_zones
                ORDER BY updated_at DESC
                """
            ).fetchall()

        zones: List[Dict[str, Any]] = []
        for row in rows:
            try:
                points = json.loads(row["points_json"])
            except json.JSONDecodeError:
                points = []
            zones.append({"id": row["id"], "name": row["name"], "points": points})

        return zones

    def get_zone(self, zone_id: str) -> Optional[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, name, points_json
                FROM danger_zones
                WHERE id = ?
                """,
                (zone_id,),
            ).fetchone()

        if row is None:
            return None

        try:
            points = json.loads(row["points_json"])
        except json.JSONDecodeError:
            points = []

        return {"id": row["id"], "name": row["name"], "points": points}

    def add_or_update_zone(self, zone_id: str, zone_data: Dict[str, Any]) -> bool:
        payload = dict(zone_data)
        payload.pop("id", None)

        name = payload.get("name", "Unnamed Zone")
        points = payload.get("points", [])

        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO danger_zones (id, name, points_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    points_json = excluded.points_json,
                    updated_at = excluded.updated_at
                """,
                (
                    zone_id,
                    name,
                    json.dumps(points, ensure_ascii=False),
                    datetime.now(KST).isoformat(),
                ),
            )
            conn.commit()

        return True

    def delete_zone(self, zone_id: str) -> bool:
        with get_connection(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM danger_zones WHERE id = ?", (zone_id,))
            conn.commit()
            return cursor.rowcount > 0
