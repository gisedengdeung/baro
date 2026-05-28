from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from cloud.api.safety import _annotate_event_deductions
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
                    "SELECT final_score, accident_free_streak, closed_at FROM safety_score_daily WHERE date = ?",
                    ("2026-05-19",),
                ).fetchone()
                today = conn.execute(
                    "SELECT final_score FROM safety_score_daily WHERE date = ?",
                    ("2026-05-20",),
                ).fetchone()

            self.assertEqual(yesterday["final_score"], 100)
            self.assertEqual(yesterday["accident_free_streak"], 3)
            self.assertIsNotNone(yesterday["closed_at"])
            self.assertIsNone(today)

    def test_weather_refresh_failure_preserves_existing_risk(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = self._db_path(tmpdir)
            init_db(db_path)
            service = SafetyService(db_path)
            existing_details = [{"key": "strong_wind", "points": 5}]
            service.update_weather_deduction(5, existing_details)

            class FailingWeatherService(WeatherService):
                async def _fetch_ultra_short_nowcast(self):
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

    def test_sensor_pinch_events_are_deducted_with_daily_cap(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = self._db_path(tmpdir)
            init_db(db_path)
            service = SafetyService(db_path)

            with get_connection(db_path) as conn:
                for minute in range(3):
                    conn.execute(
                        """
                        INSERT INTO event_logs
                            (edge_id, event_type, details_json, log_risk_level, operation_mode, timestamp)
                        VALUES ('edge-default', 'LOG_CRITICAL_SENSOR', '{}', 'CRITICAL', 'RUNNING', ?)
                        """,
                        (f"2026-05-22T11:0{minute}:00",),
                    )
                conn.commit()

            score_data = service._get_score_for_date("2026-05-22")
            event_deduction = score_data["event_deduction"]
            event = event_deduction["events"][0]

            self.assertEqual(event_deduction["base"], 40)
            self.assertLess(score_data["score"], 100)
            self.assertEqual(event["event_type"], "LOG_CRITICAL_SENSOR")
            self.assertEqual(event["label"], "끼임 감지")
            self.assertEqual(event["points_per"], 20)
            self.assertEqual(event["daily_cap"], 2)
            self.assertEqual(event["count"], 3)

    def test_daily_report_event_deduction_annotations_respect_time_order_and_cap(self):
        events = [
            {"id": 3, "event_type": "LOG_CRITICAL_SENSOR", "timestamp": "2026-05-22T11:02:00"},
            {"id": 1, "event_type": "LOG_CRITICAL_SENSOR", "timestamp": "2026-05-22T11:00:00"},
            {"id": 2, "event_type": "LOG_CRITICAL_SENSOR", "timestamp": "2026-05-22T11:01:00"},
        ]

        _annotate_event_deductions(events, 1.25)
        by_id = {event["id"]: event for event in events}

        self.assertEqual(by_id[1]["deduction_points"], 20)
        self.assertEqual(by_id[1]["deduction_adjusted_points"], 25)
        self.assertEqual(by_id[1]["deduction_multiplier"], 1.25)
        self.assertTrue(by_id[1]["deduction_applied"])
        self.assertEqual(by_id[2]["deduction_points"], 20)
        self.assertEqual(by_id[2]["deduction_adjusted_points"], 25)
        self.assertTrue(by_id[2]["deduction_applied"])
        self.assertEqual(by_id[3]["deduction_points"], 0)
        self.assertEqual(by_id[3]["deduction_adjusted_points"], 0)
        self.assertFalse(by_id[3]["deduction_applied"])

    def test_daily_report_recalculates_past_scores_from_events(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = self._db_path(tmpdir)
            init_db(db_path)
            service = SafetyService(db_path)

            with get_connection(db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO safety_score_daily
                        (date, final_score, deductions_json, weather_deduction, accident_free_streak, created_at)
                    VALUES ('2026-05-22', 100, '[]', 0, 0, '2026-05-22T00:00:00')
                    """
                )
                conn.execute(
                    """
                    INSERT INTO daily_weather_summary
                        (date, station_no, station_name, summary_json, created_at, updated_at)
                    VALUES ('2026-05-22', '119', '수원', '{}', '2026-05-23T00:00:00', '2026-05-23T00:00:00')
                    """
                )
                conn.execute(
                    """
                    INSERT INTO event_logs
                        (edge_id, event_type, details_json, log_risk_level, operation_mode, timestamp)
                    VALUES ('edge-default', 'LOG_CRITICAL_SENSOR', '{}', 'CRITICAL', 'RUNNING', '2026-05-22T11:00:00')
                    """
                )
                conn.commit()

            report = service.get_daily_report(days=1)

            self.assertEqual(report[0]["date"], "2026-05-22")
            self.assertLess(report[0]["score"], 100)

    def test_daily_report_keeps_past_default_score_without_weather_summary(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = self._db_path(tmpdir)
            init_db(db_path)
            service = SafetyService(db_path)

            with get_connection(db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO safety_score_daily
                        (date, final_score, deductions_json, weather_deduction, accident_free_streak, created_at)
                    VALUES ('2026-05-22', 100, '[]', 0, 0, '2026-05-22T00:00:00')
                    """
                )
                conn.execute(
                    """
                    INSERT INTO event_logs
                        (edge_id, event_type, details_json, log_risk_level, operation_mode, timestamp)
                    VALUES ('edge-default', 'LOG_CRITICAL_SENSOR', '{}', 'CRITICAL', 'RUNNING', '2026-05-22T11:00:00')
                    """
                )
                conn.commit()

            report = service.get_daily_report(days=1)

            self.assertEqual(report[0]["date"], "2026-05-22")
            self.assertEqual(report[0]["score"], 100)
            self.assertIsNone(report[0]["daily_weather"])

    def test_daily_report_recalculates_today_score_without_weather_summary(self):
        class _TodayDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 5, 22, 12, 0, tzinfo=tz)

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = self._db_path(tmpdir)
            init_db(db_path)
            service = SafetyService(db_path)

            with get_connection(db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO safety_score_daily
                        (date, final_score, deductions_json, weather_deduction, accident_free_streak, created_at)
                    VALUES ('2026-05-22', 100, '[]', 0, 0, '2026-05-22T00:00:00')
                    """
                )
                conn.execute(
                    """
                    INSERT INTO event_logs
                        (edge_id, event_type, details_json, log_risk_level, operation_mode, timestamp)
                    VALUES ('edge-default', 'LOG_CRITICAL_SENSOR', '{}', 'CRITICAL', 'RUNNING', '2026-05-22T11:00:00')
                    """
                )
                conn.commit()

            with patch.object(safety_module, "datetime", _TodayDateTime):
                report = service.get_daily_report(days=1)

            self.assertEqual(report[0]["date"], "2026-05-22")
            self.assertLess(report[0]["score"], 100)
            self.assertIsNone(report[0]["daily_weather"])

    def test_daily_report_preserves_finalized_past_scores(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = self._db_path(tmpdir)
            init_db(db_path)
            service = SafetyService(db_path)

            with get_connection(db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO safety_score_daily
                        (date, final_score, deductions_json, weather_deduction, accident_free_streak, created_at)
                    VALUES ('2026-05-22', 72, '[]', 0, 0, '2026-05-22T00:00:00')
                    """
                )
                conn.execute(
                    """
                    INSERT INTO event_logs
                        (edge_id, event_type, details_json, log_risk_level, operation_mode, timestamp)
                    VALUES ('edge-default', 'LOG_CRITICAL_SENSOR', '{}', 'CRITICAL', 'RUNNING', '2026-05-22T11:00:00')
                    """
                )
                conn.commit()

            report = service.get_daily_report(days=1)

            self.assertEqual(report[0]["date"], "2026-05-22")
            self.assertEqual(report[0]["score"], 72)

    def test_daily_report_preserves_closed_default_scores(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = self._db_path(tmpdir)
            init_db(db_path)
            service = SafetyService(db_path)

            with get_connection(db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO safety_score_daily
                        (date, final_score, deductions_json, weather_deduction, accident_free_streak, created_at, closed_at)
                    VALUES ('2026-05-22', 100, '[]', 0, 0, '2026-05-22T00:00:00', '2026-05-23T00:00:00')
                    """
                )
                conn.execute(
                    """
                    INSERT INTO daily_weather_summary
                        (date, station_no, station_name, summary_json, created_at, updated_at)
                    VALUES ('2026-05-22', '119', '수원', '{}', '2026-05-23T00:00:00', '2026-05-23T00:00:00')
                    """
                )
                conn.execute(
                    """
                    INSERT INTO event_logs
                        (edge_id, event_type, details_json, log_risk_level, operation_mode, timestamp)
                    VALUES ('edge-default', 'LOG_CRITICAL_SENSOR', '{}', 'CRITICAL', 'RUNNING', '2026-05-22T11:00:00')
                    """
                )
                conn.commit()

            report = service.get_daily_report(days=1)

            self.assertEqual(report[0]["date"], "2026-05-22")
            self.assertEqual(report[0]["score"], 100)
            self.assertEqual(report[0]["closed_at"], "2026-05-23T00:00:00")

    def test_ultra_short_nowcast_weather_risk_uses_grid_location(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = self._db_path(tmpdir)
            init_db(db_path)
            service = SafetyService(db_path)
            service.set_config("factory_location_label", "서울")
            service.set_config("location_nx", "60")
            service.set_config("location_ny", "127")

            class StubWeatherService(WeatherService):
                async def _fetch_ultra_short_nowcast(self):
                    nx, ny, label = self._get_grid_location()
                    return {
                        "source": "ultra_short_nowcast",
                        "location_label": label,
                        "nx": nx,
                        "ny": ny,
                        "tm": "2026-05-20 15:00",
                        "ta": "34",
                        "hm": "25",
                        "ws": "15",
                        "rn": "1mm 미만",
                    }

            asyncio.run(StubWeatherService("api-key", "119", service).refresh())

            today = datetime.now(safety_module.KST).date().isoformat()
            with get_connection(db_path) as conn:
                row = conn.execute(
                    "SELECT weather_deduction, deductions_json FROM safety_score_daily WHERE date = ?",
                    (today,),
                ).fetchone()

            details = json.loads(row["deductions_json"])
            observation = details[0]
            self.assertEqual(row["weather_deduction"], 15)
            self.assertEqual(observation["source"], "ultra_short_nowcast")
            self.assertEqual(observation["location_name"], "서울")
            self.assertEqual(observation["nx"], "60")
            self.assertEqual(observation["ny"], "127")
            self.assertEqual(observation["values"]["rain_mm"], 0.5)

    def test_ultra_short_nowcast_upper_bound_rain_label_applies_risk(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = self._db_path(tmpdir)
            init_db(db_path)
            service = SafetyService(db_path)

            class StubWeatherService(WeatherService):
                async def _fetch_ultra_short_nowcast(self):
                    return {
                        "source": "ultra_short_nowcast",
                        "tm": "2026-05-20 15:00",
                        "ta": "20",
                        "hm": "60",
                        "ws": "1",
                        "rn": "50.0mm 이상",
                    }

            asyncio.run(StubWeatherService("api-key", "119", service).refresh())

            today = datetime.now(safety_module.KST).date().isoformat()
            with get_connection(db_path) as conn:
                row = conn.execute(
                    "SELECT weather_deduction, deductions_json FROM safety_score_daily WHERE date = ?",
                    (today,),
                ).fetchone()

            details = json.loads(row["deductions_json"])
            observation = details[0]
            self.assertEqual(row["weather_deduction"], 3)
            self.assertEqual(observation["values"]["rain_mm"], 50.0)
            self.assertEqual(details[1]["key"], "heavy_rain")

    def test_ultra_short_nowcast_base_time_uses_40_minute_delay(self):
        base_date, base_time = WeatherService._get_ultra_short_base(
            datetime(2026, 5, 25, 16, 39, tzinfo=safety_module.KST)
        )
        self.assertEqual(base_date, "20260525")
        self.assertEqual(base_time, "1500")

        base_date, base_time = WeatherService._get_ultra_short_base(
            datetime(2026, 5, 25, 16, 40, tzinfo=safety_module.KST)
        )
        self.assertEqual(base_date, "20260525")
        self.assertEqual(base_time, "1600")


if __name__ == "__main__":
    unittest.main()
