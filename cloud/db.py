from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from loguru import logger



def _apply_pragmas(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA synchronous=NORMAL;")


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table});").fetchall()
    return any(row[1] == column for row in rows)


def _ensure_columns(conn: sqlite3.Connection, table: str, columns: Iterable[str]) -> None:
    for definition in columns:
        column_name = definition.split()[0]
        if _column_exists(conn, table, column_name):
            continue
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition};")



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
                timestamp TEXT NOT NULL,
                event_uid TEXT,
                clip_status TEXT NOT NULL DEFAULT 'NONE',
                clip_path TEXT,
                clip_started_at TEXT,
                clip_ended_at TEXT,
                clip_duration_sec REAL,
                clip_created_at TEXT
            );
            """
        )

        _ensure_columns(
            conn,
            "event_logs",
            [
                "event_uid TEXT",
                "clip_status TEXT NOT NULL DEFAULT 'NONE'",
                "clip_path TEXT",
                "clip_started_at TEXT",
                "clip_ended_at TEXT",
                "clip_duration_sec REAL",
                "clip_created_at TEXT",
            ],
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
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'admin',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_refresh_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_jti TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                revoked_at TEXT,
                created_at TEXT NOT NULL,
                last_used_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
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
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_event_logs_event_uid
            ON event_logs(event_uid);
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_users_email
            ON users(email);
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_auth_refresh_sessions_token_jti
            ON auth_refresh_sessions(token_jti);
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_auth_refresh_sessions_user_id
            ON auth_refresh_sessions(user_id);
            """
        )

        conn.commit()

    logger.info(f"SQLite 초기화 완료: {path}")



def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _apply_pragmas(conn)
    return conn
