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

        # 1. 엣지 테이블
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS edges (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TEXT NOT NULL
            );
            """
        )

        # 2. 이벤트 로그 테이블
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
                clip_created_at TEXT,
                FOREIGN KEY(edge_id) REFERENCES edges(id) ON DELETE CASCADE
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

        # 3. 위험 구역 테이블
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS danger_zones (
                id TEXT PRIMARY KEY,
                edge_id TEXT NOT NULL,
                name TEXT NOT NULL,
                points_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(edge_id) REFERENCES edges(id) ON DELETE CASCADE
            );
            """
        )

        # 4. 사용자 테이블
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

        # 5. 인증 토큰 테이블
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

        conn.execute("CREATE INDEX IF NOT EXISTS idx_event_logs_timestamp ON event_logs(timestamp DESC);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_event_logs_edge_id ON event_logs(edge_id);")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_event_logs_event_uid_not_null ON event_logs(event_uid) WHERE event_uid IS NOT NULL;")
        
        conn.execute("CREATE INDEX IF NOT EXISTS idx_danger_zones_edge_id ON danger_zones(edge_id);")
        
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_auth_refresh_sessions_token_jti ON auth_refresh_sessions(token_jti);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_auth_refresh_sessions_user_id ON auth_refresh_sessions(user_id);")

        # 6. 안전점수 일별 기록 테이블
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS safety_score_daily (
                date TEXT PRIMARY KEY,
                final_score INTEGER NOT NULL DEFAULT 100,
                deductions_json TEXT NOT NULL DEFAULT '[]',
                weather_deduction INTEGER NOT NULL DEFAULT 0,
                accident_free_streak INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )

        # 7. 일별 ASOS 기상 요약 테이블
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_weather_summary (
                date TEXT PRIMARY KEY,
                station_no TEXT NOT NULL,
                station_name TEXT NOT NULL,
                avg_temp REAL,
                max_temp REAL,
                min_temp REAL,
                avg_humidity REAL,
                max_wind REAL,
                total_rain REAL,
                summary_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

        # 8. 공장 설정값 테이블
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS factory_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

        # 초기 엣지 디바이스 데이터 삽입
        conn.execute(
            """
            INSERT OR IGNORE INTO edges (id, name, is_active, created_at)
            VALUES ('edge-default', '메인 컨베이어 카메라', 1, datetime('now', 'utc'));
            """
        )

        # 초기 공장 설정값 (더미 데이터 - 실제 값으로 교체 필요)
        for key, value in [
            ("industry_type", "식료품제조업"),
            ("worker_count", "80"),    # 총 근무자 수
            ("factory_location_label", "수원"),
            ("factory_address", ""),
            ("location_lat", ""),
            ("location_lon", ""),
            ("location_nx", "60"),     # 기상청 격자 X (경기 수원 기준 더미)
            ("location_ny", "121"),    # 기상청 격자 Y (경기 수원 기준 더미)
            ("kma_asos_station_no", "119"),
            ("kma_asos_station_name", "수원"),
        ]:
            conn.execute(
                """
                INSERT OR IGNORE INTO factory_config (key, value, updated_at)
                VALUES (?, ?, datetime('now', 'utc'));
                """,
                (key, value),
            )

        conn.commit()

    logger.info(f"SQLite 초기화 완료: {path}")


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _apply_pragmas(conn)
    return conn
