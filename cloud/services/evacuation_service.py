from __future__ import annotations

import heapq
import json
import math
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from cloud.db import get_connection
from cloud.services.zone_service import ZoneService


class EvacuationService:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _dist(x1: float, y1: float, x2: float, y2: float) -> float:
        return math.hypot(x1 - x2, y1 - y2)

    @staticmethod
    def _node_from_row(row: Any) -> Dict[str, Any]:
        try:
            meta = json.loads(row["meta_json"])
        except json.JSONDecodeError:
            meta = {}
        return {
            "id": row["id"],
            "edge_id": row["edge_id"],
            "name": row["name"],
            "x": float(row["x"]),
            "y": float(row["y"]),
            "kind": row["kind"],
            "meta": meta,
        }

    def list_exits(self, edge_id: str | None = None) -> List[Dict[str, Any]]:
        params: List[Any] = []
        where = ""
        if edge_id:
            where = "WHERE edge_id = ?"
            params.append(edge_id)
        query = f"""
            SELECT id, edge_id, name, x, y, description
            FROM evacuation_exits
            {where}
            ORDER BY updated_at DESC
        """
        with get_connection(self.db_path) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [
            {
                "id": row["id"],
                "edge_id": row["edge_id"],
                "name": row["name"],
                "x": float(row["x"]),
                "y": float(row["y"]),
                "description": row["description"],
            }
            for row in rows
        ]

    def upsert_exit(self, payload: Dict[str, Any], exit_id: str | None = None) -> Dict[str, Any]:
        item_id = exit_id or str(uuid4())
        now = self._now_iso()
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO evacuation_exits (id, edge_id, name, x, y, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    edge_id = excluded.edge_id,
                    name = excluded.name,
                    x = excluded.x,
                    y = excluded.y,
                    description = excluded.description,
                    updated_at = excluded.updated_at
                """,
                (
                    item_id,
                    payload["edge_id"],
                    payload["name"],
                    payload["x"],
                    payload["y"],
                    payload.get("description"),
                    now,
                    now,
                ),
            )
            conn.commit()
        return self.get_exit(item_id)

    def get_exit(self, exit_id: str) -> Optional[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT id, edge_id, name, x, y, description FROM evacuation_exits WHERE id = ?",
                (exit_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "edge_id": row["edge_id"],
            "name": row["name"],
            "x": float(row["x"]),
            "y": float(row["y"]),
            "description": row["description"],
        }

    def delete_exit(self, exit_id: str) -> bool:
        with get_connection(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM evacuation_exits WHERE id = ?", (exit_id,))
            conn.commit()
            return cursor.rowcount > 0

    def list_nodes(self, edge_id: str | None = None) -> List[Dict[str, Any]]:
        params: List[Any] = []
        where = ""
        if edge_id:
            where = "WHERE edge_id = ?"
            params.append(edge_id)
        query = f"""
            SELECT id, edge_id, name, x, y, kind, meta_json
            FROM evacuation_nodes
            {where}
            ORDER BY updated_at DESC
        """
        with get_connection(self.db_path) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._node_from_row(row) for row in rows]

    def upsert_node(self, payload: Dict[str, Any], node_id: str | None = None) -> Dict[str, Any]:
        item_id = node_id or str(uuid4())
        now = self._now_iso()
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO evacuation_nodes (id, edge_id, name, x, y, kind, meta_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    edge_id = excluded.edge_id,
                    name = excluded.name,
                    x = excluded.x,
                    y = excluded.y,
                    kind = excluded.kind,
                    meta_json = excluded.meta_json,
                    updated_at = excluded.updated_at
                """,
                (
                    item_id,
                    payload["edge_id"],
                    payload["name"],
                    payload["x"],
                    payload["y"],
                    payload.get("kind", "WAYPOINT"),
                    json.dumps(payload.get("meta", {}), ensure_ascii=False),
                    now,
                    now,
                ),
            )
            conn.commit()
        return self.get_node(item_id)

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, edge_id, name, x, y, kind, meta_json
                FROM evacuation_nodes
                WHERE id = ?
                """,
                (node_id,),
            ).fetchone()
        return self._node_from_row(row) if row else None

    def delete_node(self, node_id: str) -> bool:
        with get_connection(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM evacuation_nodes WHERE id = ?", (node_id,))
            conn.execute(
                "DELETE FROM evacuation_edges WHERE from_node_id = ? OR to_node_id = ?",
                (node_id, node_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def list_edges(self, edge_id: str | None = None) -> List[Dict[str, Any]]:
        params: List[Any] = []
        where = ""
        if edge_id:
            where = "WHERE edge_id = ?"
            params.append(edge_id)
        query = f"""
            SELECT id, edge_id, from_node_id, to_node_id, distance, is_blocked
            FROM evacuation_edges
            {where}
            ORDER BY updated_at DESC
        """
        with get_connection(self.db_path) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [
            {
                "id": row["id"],
                "edge_id": row["edge_id"],
                "from_node_id": row["from_node_id"],
                "to_node_id": row["to_node_id"],
                "distance": float(row["distance"]),
                "is_blocked": bool(row["is_blocked"]),
            }
            for row in rows
        ]

    def upsert_edge(self, payload: Dict[str, Any], edge_id: str | None = None) -> Dict[str, Any]:
        item_id = edge_id or str(uuid4())
        now = self._now_iso()
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO evacuation_edges (id, edge_id, from_node_id, to_node_id, distance, is_blocked, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    edge_id = excluded.edge_id,
                    from_node_id = excluded.from_node_id,
                    to_node_id = excluded.to_node_id,
                    distance = excluded.distance,
                    is_blocked = excluded.is_blocked,
                    updated_at = excluded.updated_at
                """,
                (
                    item_id,
                    payload["edge_id"],
                    payload["from_node_id"],
                    payload["to_node_id"],
                    payload["distance"],
                    1 if payload.get("is_blocked") else 0,
                    now,
                ),
            )
            conn.commit()
        return self.get_edge(item_id)

    def get_edge(self, edge_id: str) -> Optional[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, edge_id, from_node_id, to_node_id, distance, is_blocked
                FROM evacuation_edges
                WHERE id = ?
                """,
                (edge_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "edge_id": row["edge_id"],
            "from_node_id": row["from_node_id"],
            "to_node_id": row["to_node_id"],
            "distance": float(row["distance"]),
            "is_blocked": bool(row["is_blocked"]),
        }

    def delete_edge(self, edge_id: str) -> bool:
        with get_connection(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM evacuation_edges WHERE id = ?", (edge_id,))
            conn.commit()
            return cursor.rowcount > 0

    def _resolve_start_node(
        self,
        nodes_by_id: Dict[str, Dict[str, Any]],
        edge_id: str,
        zone_id: str | None,
        zone_service: ZoneService | None,
    ) -> Optional[str]:
        if not nodes_by_id:
            return None

        if zone_id and zone_service is not None:
            zone = zone_service.get_zone(zone_id)
            if zone and zone.get("points"):
                points = zone["points"]
                cx = sum(float(p["x"]) for p in points) / len(points)
                cy = sum(float(p["y"]) for p in points) / len(points)
                nearest_id = min(
                    nodes_by_id,
                    key=lambda node_id: self._dist(cx, cy, nodes_by_id[node_id]["x"], nodes_by_id[node_id]["y"]),
                )
                return nearest_id

        non_exit_nodes = [node_id for node_id, node in nodes_by_id.items() if node.get("kind") != "EXIT"]
        if non_exit_nodes:
            return sorted(non_exit_nodes)[0]

        return sorted(nodes_by_id.keys())[0]

    def _resolve_exit_nodes(
        self,
        nodes_by_id: Dict[str, Dict[str, Any]],
        edge_id: str,
    ) -> List[str]:
        exits = [node_id for node_id, node in nodes_by_id.items() if node.get("kind") == "EXIT"]
        if exits:
            return exits

        exit_rows = self.list_exits(edge_id=edge_id)
        exit_node_ids: List[str] = []
        for ex in exit_rows:
            nearest = min(
                nodes_by_id,
                key=lambda node_id: self._dist(ex["x"], ex["y"], nodes_by_id[node_id]["x"], nodes_by_id[node_id]["y"]),
            )
            if nearest not in exit_node_ids:
                exit_node_ids.append(nearest)
        return exit_node_ids

    def get_route(
        self,
        edge_id: str,
        zone_id: str | None,
        incident_type: str | None,
        zone_service: ZoneService | None = None,
    ) -> Dict[str, Any]:
        nodes = [n for n in self.list_nodes(edge_id=edge_id) if n["edge_id"] == edge_id]
        if not nodes:
            raise ValueError("No evacuation nodes configured")

        nodes_by_id = {n["id"]: n for n in nodes}
        start_node_id = self._resolve_start_node(nodes_by_id, edge_id, zone_id, zone_service)
        if start_node_id is None:
            raise ValueError("Unable to resolve start node")

        exit_node_ids = self._resolve_exit_nodes(nodes_by_id, edge_id)
        if not exit_node_ids:
            raise ValueError("No evacuation exits configured")

        edges = [e for e in self.list_edges(edge_id=edge_id) if not e["is_blocked"]]
        graph: Dict[str, List[Tuple[str, float]]] = {node_id: [] for node_id in nodes_by_id}
        for edge in edges:
            a = edge["from_node_id"]
            b = edge["to_node_id"]
            if a not in nodes_by_id or b not in nodes_by_id:
                continue
            dist = float(edge["distance"])
            graph[a].append((b, dist))
            graph[b].append((a, dist))

        pq: List[Tuple[float, str]] = [(0.0, start_node_id)]
        distances: Dict[str, float] = {start_node_id: 0.0}
        previous: Dict[str, str] = {}

        while pq:
            current_dist, node_id = heapq.heappop(pq)
            if current_dist > distances.get(node_id, float("inf")):
                continue
            for neighbor, cost in graph.get(node_id, []):
                nd = current_dist + cost
                if nd < distances.get(neighbor, float("inf")):
                    distances[neighbor] = nd
                    previous[neighbor] = node_id
                    heapq.heappush(pq, (nd, neighbor))

        reachable_exits = [eid for eid in exit_node_ids if eid in distances]
        if not reachable_exits:
            raise ValueError("No reachable evacuation route")

        end_node_id = min(reachable_exits, key=lambda eid: distances[eid])
        total_distance = float(distances[end_node_id])

        path_ids = [end_node_id]
        while path_ids[-1] != start_node_id:
            path_ids.append(previous[path_ids[-1]])
        path_ids.reverse()

        steps = [f"{idx+1}. {nodes_by_id[nid]['name']}" for idx, nid in enumerate(path_ids)]
        polyline = [{"x": nodes_by_id[nid]["x"], "y": nodes_by_id[nid]["y"]} for nid in path_ids]

        return {
            "edge_id": edge_id,
            "zone_id": zone_id,
            "incident_type": incident_type,
            "start_node_id": start_node_id,
            "end_node_id": end_node_id,
            "total_distance": round(total_distance, 2),
            "estimated_seconds": round(total_distance / 1.2, 2),
            "polyline": polyline,
            "steps": steps,
            "node_ids": path_ids,
        }
