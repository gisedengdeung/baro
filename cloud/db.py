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
            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY,
                edge_id TEXT NOT NULL,
                incident_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                zone_id TEXT,
                status TEXT NOT NULL DEFAULT 'OPEN',
                details_json TEXT NOT NULL,
                snapshot_path TEXT,
                detected_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mobile_devices (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                fcm_token TEXT NOT NULL UNIQUE,
                edge_scope_json TEXT NOT NULL,
                last_notified_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS evacuation_exits (
                id TEXT PRIMARY KEY,
                edge_id TEXT NOT NULL,
                name TEXT NOT NULL,
                x REAL NOT NULL,
                y REAL NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS evacuation_nodes (
                id TEXT PRIMARY KEY,
                edge_id TEXT NOT NULL,
                name TEXT NOT NULL,
                x REAL NOT NULL,
                y REAL NOT NULL,
                kind TEXT NOT NULL DEFAULT 'WAYPOINT',
                meta_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS evacuation_edges (
                id TEXT PRIMARY KEY,
                edge_id TEXT NOT NULL,
                from_node_id TEXT NOT NULL,
                to_node_id TEXT NOT NULL,
                distance REAL NOT NULL,
                is_blocked INTEGER NOT NULL DEFAULT 0,
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

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_incidents_created_at
            ON incidents(created_at DESC);
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_incidents_status
            ON incidents(status);
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_incidents_edge_id
            ON incidents(edge_id);
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_mobile_devices_user_id
            ON mobile_devices(user_id);
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_mobile_devices_fcm_token
            ON mobile_devices(fcm_token);
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_evacuation_nodes_edge_id
            ON evacuation_nodes(edge_id);
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_evacuation_edges_edge_id
            ON evacuation_edges(edge_id);
            """
        )

        conn.commit()

    logger.info(f"SQLite 초기화 완료: {path}")



def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _apply_pragmas(conn)
    return conn
