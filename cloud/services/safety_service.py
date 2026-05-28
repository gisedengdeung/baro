from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from cloud.db import get_connection

KST = ZoneInfo("Asia/Seoul")

# 이벤트 타입별 기본 감점 규칙
DEDUCTION_RULES: dict[str, dict] = {
    "LOG_CRITICAL_FALLING":   {"points": 20, "label": "넘어짐 감지",   "daily_cap": 2},
    "LOG_INTRUSION_SLOWDOWN": {"points": 10, "label": "위험구역 진입", "daily_cap": 2},
    "LOG_CRITICAL_SENSOR":    {"points": 20, "label": "끼임 감지",     "daily_cap": 2},
}

EVENT_TYPE_TO_PUBLIC_LABEL: dict[str, str] = {
    "LOG_CRITICAL_FALLING": "낙상감지",
    "LOG_INTRUSION_SLOWDOWN": "위험구역진입",
    "LOG_CRITICAL_SENSOR": "끼임감지",
}

ACCIDENT_FREE_THRESHOLD  = 80   # 무사고 유지 기준 점수
WEATHER_MAX_DEDUCTION    = 15   # 기상 위험도 상한
SAFETY_WEIGHTS_PATH = Path(__file__).resolve().parents[2] / "config" / "safety_weights.json"
SIZE_RISK_WEIGHTS_PATH = Path(__file__).resolve().parents[2] / "config" / "size_risk_weights.json"


class SafetyService:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.weight_data = self._load_weight_data()
        self.size_risk_data = self._load_size_risk_data()

    @staticmethod
    def _load_weight_data() -> dict[str, Any]:
        fallback = {
            "event_mapping": {
                "낙상감지": "떨어짐",
                "위험구역진입": "끼임",
                "끼임감지": "끼임",
            },
            "industry_weights": {
                "제조업_전체": {
                    "떨어짐": 19.14,
                    "끼임": 27.16,
                }
            },
        }
        try:
            with SAFETY_WEIGHTS_PATH.open("r", encoding="utf-8") as fp:
                return json.load(fp)
        except (OSError, json.JSONDecodeError):
            return fallback

    @staticmethod
    def _load_size_risk_data() -> dict[str, Any]:
        fallback = {
            "size_weights": {
                "제조업_전체": {
                    "5인 미만": {"min": 0, "max": 4, "risk": 10},
                    "5~49인": {"min": 5, "max": 49, "risk": 7},
                    "50~299인": {"min": 50, "max": 299, "risk": 3},
                    "300인 이상": {"min": 300, "max": None, "risk": 1},
                }
            }
        }
        try:
            with SIZE_RISK_WEIGHTS_PATH.open("r", encoding="utf-8") as fp:
                return json.load(fp)
        except (OSError, json.JSONDecodeError):
            return fallback

    # ── 공장 설정 ──────────────────────────────────────────────────────────────

    def get_config(self, key: str) -> str | None:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT value FROM factory_config WHERE key = ?", (key,)
            ).fetchone()
        return row["value"] if row else None

    def set_config(self, key: str, value: str) -> None:
        now = datetime.now(KST).isoformat()
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO factory_config (key, value, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (key, value, now),
            )
            conn.commit()

    def get_all_config(self) -> dict[str, str]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT key, value FROM factory_config ORDER BY key"
            ).fetchall()
        return {row["key"]: row["value"] for row in rows}

    # ── 점수 계산 ──────────────────────────────────────────────────────────────

    def _ensure_today_record(self, date_str: str) -> None:
        now = datetime.now(KST).isoformat()
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO safety_score_daily
                    (date, final_score, deductions_json, weather_deduction, accident_free_streak, created_at)
                VALUES (?, 100, '[]', 0, 0, ?)
                """,
                (date_str, now),
            )
            conn.commit()

    def _get_worker_count(self) -> int:
        try:
            return int(self.get_config("worker_count") or "0")
        except ValueError:
            return 0

    def _get_industry_name(self) -> str:
        return self.get_config("industry_type") or "제조업_전체"

    def _get_industry_risk(self, industry: str) -> float:
        industry_weights = self.weight_data.get("industry_weights", {})
        weights = industry_weights.get(industry) or industry_weights.get("제조업_전체", {})
        event_mapping = self.weight_data.get("event_mapping", {})

        accident_types = [
            event_mapping.get(label)
            for label in EVENT_TYPE_TO_PUBLIC_LABEL.values()
        ]
        values = [
            float(weights.get(accident_type, 0.0))
            for accident_type in accident_types
            if accident_type
        ]
        if not values:
            return 0.0
        return sum(values) / len(values)

    def _get_size_risk(self, industry: str, worker_count: int) -> dict[str, Any]:
        size_weights = self.size_risk_data.get("size_weights", {})
        industry_scales = size_weights.get(industry) or size_weights.get("제조업_전체") or {}

        for label, data in industry_scales.items():
            min_count = int(data.get("min") or 0)
            max_count = data.get("max")
            if worker_count < min_count:
                continue
            if max_count is not None and worker_count > int(max_count):
                continue
            return {
                "scale": label,
                "worker_count": worker_count,
                "risk": round(float(data.get("risk", 0.0)), 2),
                "accident_count": int(data.get("accident_count", 0)),
                "fatality_count": int(data.get("fatality_count", 0)),
                "accident_share_pct": float(data.get("accident_share_pct", 0.0)),
                "fatality_share_pct": float(data.get("fatality_share_pct", 0.0)),
            }

        return {
            "scale": "미분류",
            "worker_count": worker_count,
            "risk": 0.0,
            "accident_count": 0,
            "fatality_count": 0,
            "accident_share_pct": 0.0,
            "fatality_share_pct": 0.0,
        }

    @staticmethod
    def _get_difficulty_level(score: float) -> tuple[str, str]:
        if score < 20:
            return "낮음", "ok"
        if score < 35:
            return "보통", "warning"
        if score < 50:
            return "높음", "warning"
        return "매우 높음", "danger"

    @staticmethod
    def _get_difficulty_multiplier(score: float) -> float:
        if score < 20:
            return 1.0
        if score < 35:
            return 1.1
        if score < 50:
            return 1.25
        return 1.4

    def _get_event_deductions(self, date_str: str) -> tuple[int, list[dict]]:
        """오늘 event_logs 로부터 감점 합계와 상세 내역 반환 (daily_cap 적용)"""
        date_start = f"{date_str}T00:00:00"
        date_end   = f"{date_str}T23:59:59"

        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT event_type, timestamp FROM event_logs
                WHERE timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp ASC
                """,
                (date_start, date_end),
            ).fetchall()

        counts: dict[str, int] = {}
        details: list[dict]    = []
        total = 0

        for row in rows:
            etype = row["event_type"]
            if etype not in DEDUCTION_RULES:
                continue
            rule = DEDUCTION_RULES[etype]
            counts[etype] = counts.get(etype, 0) + 1
            n = counts[etype]

            if n <= rule["daily_cap"]:
                total += rule["points"]

            existing = next((d for d in details if d["event_type"] == etype), None)
            if existing:
                existing["count"] = n
                existing["last_at"] = row["timestamp"]
            else:
                details.append({
                    "event_type": etype,
                    "label":      rule["label"],
                    "points_per": rule["points"],
                    "daily_cap":  rule["daily_cap"],
                    "count":      n,
                    "last_at":    row["timestamp"],
                })

        return total, details

    def _get_weather_details(self, date_str: str) -> list[dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT deductions_json FROM safety_score_daily WHERE date = ?",
                (date_str,),
            ).fetchone()
        if not row:
            return []
        try:
            details = json.loads(row["deductions_json"] or "[]")
        except json.JSONDecodeError:
            return []
        return details if isinstance(details, list) else []

    def _has_deductible_events(self, date_str: str) -> bool:
        date_start = f"{date_str}T00:00:00"
        date_end = f"{date_str}T23:59:59"
        placeholders = ",".join("?" for _ in DEDUCTION_RULES)
        params = [date_start, date_end, *DEDUCTION_RULES.keys()]
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                f"""
                SELECT 1
                FROM event_logs
                WHERE timestamp >= ?
                  AND timestamp <= ?
                  AND event_type IN ({placeholders})
                LIMIT 1
                """,
                params,
            ).fetchone()
        return row is not None

    def _get_difficulty(self, weather_risk: int, weather_details: list[dict[str, Any]]) -> dict[str, Any]:
        industry = self._get_industry_name()
        worker_count = self._get_worker_count()
        industry_risk = self._get_industry_risk(industry)
        size_risk_data = self._get_size_risk(industry, worker_count)
        size_risk = size_risk_data["risk"]
        score = industry_risk + size_risk + weather_risk
        level, color = self._get_difficulty_level(score)
        multiplier = self._get_difficulty_multiplier(score)

        return {
            "score": round(score, 1),
            "level": level,
            "color": color,
            "multiplier": multiplier,
            "factors": {
                "industry": {
                    "label": industry,
                    "risk": round(industry_risk, 1),
                },
                "size": {
                    **size_risk_data,
                },
                "weather": {
                    "risk": weather_risk,
                    "details": weather_details,
                },
            },
        }

    def _get_score_for_date(self, date_str: str) -> dict[str, Any]:
        self._ensure_today_record(date_str)

        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT weather_deduction, accident_free_streak FROM safety_score_daily WHERE date = ?",
                (date_str,),
            ).fetchone()

        weather_risk      = int(row["weather_deduction"])
        streak            = int(row["accident_free_streak"])
        event_deduction, event_details = self._get_event_deductions(date_str)
        weather_details = self._get_weather_details(date_str)
        difficulty = self._get_difficulty(weather_risk, weather_details)
        adjusted_event_deduction = event_deduction * difficulty["multiplier"]

        final_score = max(0, round(100 - adjusted_event_deduction, 1))

        return {
            "date":  date_str,
            "score": final_score,
            "difficulty": difficulty,
            "event_deduction": {
                "base": event_deduction,
                "adjusted": round(adjusted_event_deduction, 1),
                "events": event_details,
            },
            "deductions": {
                "weather": 0,
                "size":    0,
                "events":  event_details,
            },
            "accident_free_streak":    streak,
            "is_accident_free":        final_score >= ACCIDENT_FREE_THRESHOLD,
            "accident_free_threshold": ACCIDENT_FREE_THRESHOLD,
        }

    def get_today_score(self) -> dict[str, Any]:
        today = datetime.now(KST).date().isoformat()
        return self._get_score_for_date(today)

    def update_weather_deduction(self, deduction: int, details: list[dict]) -> None:
        """기상 조건은 안전점수 직접 감점이 아니라 작업 난이도 위험도로 저장합니다."""
        today = datetime.now(KST).date().isoformat()
        self._ensure_today_record(today)
        with get_connection(self.db_path) as conn:
            conn.execute(
                "UPDATE safety_score_daily SET weather_deduction = ?, deductions_json = ? WHERE date = ?",
                (deduction, json.dumps(details, ensure_ascii=False), today),
            )
            conn.commit()

    def close_day(self) -> None:
        """자정에 호출 - 직전 날짜 점수 확정 + 무사고 스트릭 업데이트"""
        target_day = datetime.now(KST).date() - timedelta(days=1)
        target_date = target_day.isoformat()
        previous_date = (target_day - timedelta(days=1)).isoformat()
        self._ensure_today_record(target_date)

        score_data  = self._get_score_for_date(target_date)
        final_score = score_data["score"]

        with get_connection(self.db_path) as conn:
            prev_row = conn.execute(
                "SELECT accident_free_streak FROM safety_score_daily WHERE date = ?",
                (previous_date,),
            ).fetchone()
        prev_streak = int(prev_row["accident_free_streak"]) if prev_row else 0
        new_streak  = prev_streak + 1 if final_score >= ACCIDENT_FREE_THRESHOLD else 0

        with get_connection(self.db_path) as conn:
            closed_at = datetime.now(KST).isoformat()
            conn.execute(
                """
                UPDATE safety_score_daily
                SET final_score = ?,
                    accident_free_streak = ?,
                    closed_at = ?
                WHERE date = ?
                """,
                (final_score, new_streak, closed_at, target_date),
            )
            conn.commit()

    def get_history(self, days: int = 7) -> list[dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT date, final_score, accident_free_streak
                FROM safety_score_daily
                ORDER BY date DESC
                LIMIT ?
                """,
                (days,),
            ).fetchall()
        return [
            {
                "date":          row["date"],
                "score":         row["final_score"],
                "accident_free": row["final_score"] >= ACCIDENT_FREE_THRESHOLD,
                "streak":        row["accident_free_streak"],
            }
            for row in rows
        ]

    def get_daily_report(self, days: int = 30) -> list[dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT
                    s.date,
                    s.final_score,
                    s.accident_free_streak,
                    s.weather_deduction,
                    s.deductions_json,
                    s.closed_at,
                    w.station_no,
                    w.station_name,
                    w.avg_temp,
                    w.max_temp,
                    w.min_temp,
                    w.avg_humidity,
                    w.max_wind,
                    w.total_rain,
                    w.summary_json
                FROM safety_score_daily s
                LEFT JOIN daily_weather_summary w ON w.date = s.date
                ORDER BY s.date DESC
                LIMIT ?
                """,
                (days,),
            ).fetchall()

        report: list[dict[str, Any]] = []
        for row in rows:
            weather_details = []
            try:
                weather_details = json.loads(row["deductions_json"] or "[]")
            except json.JSONDecodeError:
                weather_details = []
            try:
                weather_summary = json.loads(row["summary_json"] or "{}") if row["summary_json"] else None
            except json.JSONDecodeError:
                weather_summary = None
            if not weather_summary and row["station_no"]:
                weather_summary = {
                    "station_no": row["station_no"],
                    "station_name": row["station_name"],
                    "avg_temp": row["avg_temp"],
                    "max_temp": row["max_temp"],
                    "min_temp": row["min_temp"],
                    "avg_humidity": row["avg_humidity"],
                    "max_wind": row["max_wind"],
                    "total_rain": row["total_rain"],
                }
            score = row["final_score"]
            difficulty = self._get_difficulty(row["weather_deduction"], weather_details)
            today = datetime.now(KST).date().isoformat()
            # 오늘은 대시보드와 같은 실시간 점수를 보여준다.
            # 과거의 close_day 이전 기본 100점 레코드는 ASOS 일별 기록이 있을 때만 보정한다.
            if (
                not row["closed_at"]
                and
                float(score) == 100.0
                and (row["date"] == today or weather_summary)
                and self._has_deductible_events(row["date"])
            ):
                score = self._get_score_for_date(row["date"])["score"]
            report.append(
                {
                    "date": row["date"],
                    "score": score,
                    "accident_free_streak": row["accident_free_streak"],
                    "weather_deduction": row["weather_deduction"],
                    "weather_details": weather_details if isinstance(weather_details, list) else [],
                    "difficulty": difficulty,
                    "daily_weather": weather_summary,
                    "closed_at": row["closed_at"],
                }
            )
        return report
