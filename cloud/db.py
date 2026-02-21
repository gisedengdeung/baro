from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterator

from loguru import logger



def _apply_pragmas(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA synchronous=NORMAL;")



def init_db(db_path: str) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as conn:
        _apply_pragmas(conn)

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS event_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                edge_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                details_json TEXT NOT NULL,
                log_risk_level TEXT NOT NULL,
                operation_mode TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS danger_zones (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                points_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_event_logs_timestamp
            ON event_logs(timestamp DESC);
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_event_logs_edge_id
            ON event_logs(edge_id);
            """
        )

        conn.commit()

    logger.info(f"SQLite 초기화 완료: {path}")



def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _apply_pragmas(conn)
    return conn
