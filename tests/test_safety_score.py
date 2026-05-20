from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from cloud.db import get_connection, init_db
from cloud.services import safety_service as safety_module
from cloud.services.safety_service import SafetyService
from cloud.services.weather_service import WeatherService


class _FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 5, 20, 0, 0, 1, tzinfo=tz)


class SafetyScoreTest(unittest.TestCase):
    def _db_path(self, tmpdir: str) -> str:
        return str(Path(tmpdir) / "cloud.db")

    def test_close_day_finalizes_previous_day(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = self._db_path(tmpdir)
            init_db(db_path)

            service = SafetyService(db_path)
            with get_connection(db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO safety_score_daily
                        (date, final_score, deductions_json, weather_deduction, accident_free_streak, created_at)
                    VALUES (?, 100, '[]', 0, 2, ?)
                    """,
                    ("2026-05-18", "2026-05-18T00:00:00"),
                )
                conn.commit()

            with patch.object(safety_module, "datetime", _FixedDateTime):
                service.close_day()

            with get_connection(db_path) as conn:
                yesterday = conn.execute(
                    "SELECT final_score, accident_free_streak FROM safety_score_daily WHERE date = ?",
                    ("2026-05-19",),
                ).fetchone()
                today = conn.execute(
                    "SELECT final_score FROM safety_score_daily WHERE date = ?",
                    ("2026-05-20",),
                ).fetchone()

            self.assertEqual(yesterday["final_score"], 100)
            self.assertEqual(yesterday["accident_free_streak"], 3)
            self.assertIsNone(today)

    def test_weather_refresh_failure_preserves_existing_risk(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = self._db_path(tmpdir)
            init_db(db_path)
            service = SafetyService(db_path)
            existing_details = [{"key": "strong_wind", "points": 5}]
            service.update_weather_deduction(5, existing_details)

            class FailingWeatherService(WeatherService):
                async def _fetch_asos_hourly(self):
                    raise RuntimeError("timeout")

            asyncio.run(FailingWeatherService("api-key", "119", service).refresh())

            today = datetime.now(safety_module.KST).date().isoformat()
            with get_connection(db_path) as conn:
                row = conn.execute(
                    "SELECT weather_deduction, deductions_json FROM safety_score_daily WHERE date = ?",
                    (today,),
                ).fetchone()

            self.assertEqual(row["weather_deduction"], 5)
            self.assertEqual(json.loads(row["deductions_json"]), existing_details)


if __name__ == "__main__":
    unittest.main()
