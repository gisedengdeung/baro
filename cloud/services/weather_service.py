from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from loguru import logger

from cloud.db import get_connection
from cloud.services.safety_service import WEATHER_MAX_DEDUCTION, SafetyService

KST = ZoneInfo("Asia/Seoul")

ASOS_STATION_NAMES: dict[str, str] = {
    "108": "서울",
    "112": "인천",
    "119": "수원",
}

ULTRA_SHORT_NOWCAST_DELAY_MINUTES = 40


class WeatherService:
    """
    기상청 초단기실황을 호출해 SafetyService의 현재 기상 위험도를 업데이트합니다.
    ASOS 시간자료는 일일 마감/사후 기록용으로 남겨둡니다.

    필요 환경변수:
      KMA_API_KEY          공공데이터포털 인증키
      KMA_ASOS_STATION_NO  기상관측소 지점번호 (108=서울, 112=인천, 119=수원 ...)
    """

    ASOS_URL = (
        "https://apis.data.go.kr/1360000/AsosHourlyInfoService/getWthrDataList"
    )
    ULTRA_SHORT_NOWCAST_URL = (
        "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
    )

    def __init__(
        self,
        api_key: str,
        station_no: str,
        safety_service: SafetyService,
    ) -> None:
        self.api_key        = api_key
        self.station_no     = station_no
        self.safety_service = safety_service

    async def refresh(self, *, raise_on_error: bool = False) -> dict[str, Any]:
        """기상 데이터 조회 → 위험도 계산 → SafetyService 업데이트"""
        try:
            nowcast_data = await self._fetch_ultra_short_nowcast()
            risk, details = self._calculate_weather_risk(nowcast_data)
            self.safety_service.update_weather_deduction(risk, details)
            logger.info(f"기상 위험도 업데이트: +{risk}점 (조건 {len(details)}개)")
            return {"risk": risk, "details": details}
        except Exception as exc:
            logger.warning(f"기상 API 호출 실패, 기존 위험도 유지: {exc}")
            if raise_on_error:
                raise
            return {"risk": None, "details": [], "error": str(exc)}

    # ── API 호출 ───────────────────────────────────────────────────────────────

    def _get_grid_location(self) -> tuple[str, str, str]:
        nx = self.safety_service.get_config("location_nx") or "60"
        ny = self.safety_service.get_config("location_ny") or "121"
        label = (
            self.safety_service.get_config("factory_address")
            or self.safety_service.get_config("factory_location_label")
            or "수원"
        )
        return nx, ny, label

    def _get_asos_station(self) -> tuple[str, str]:
        station_no = self.safety_service.get_config("kma_asos_station_no") or self.station_no
        station_name = (
            self.safety_service.get_config("kma_asos_station_name")
            or ASOS_STATION_NAMES.get(station_no)
            or f"관측소 {station_no}"
        )
        return str(station_no), str(station_name)

    @staticmethod
    def _get_ultra_short_base(now: datetime | None = None) -> tuple[str, str]:
        # 초단기실황은 공식표 기준 매시 40분 이후 제공된다.
        target = (now or datetime.now(KST)) - timedelta(minutes=ULTRA_SHORT_NOWCAST_DELAY_MINUTES)
        return target.strftime("%Y%m%d"), target.strftime("%H00")

    async def _fetch_ultra_short_nowcast(self) -> dict[str, Any]:
        nx, ny, location_label = self._get_grid_location()
        base_date, base_time = self._get_ultra_short_base()
        params = {
            "serviceKey": self.api_key,
            "pageNo": "1",
            "numOfRows": "20",
            "dataType": "JSON",
            "base_date": base_date,
            "base_time": base_time,
            "nx": nx,
            "ny": ny,
        }

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(self.ULTRA_SHORT_NOWCAST_URL, params=params)
            resp.raise_for_status()
            payload = resp.json()

        response = payload.get("response", {})
        header = response.get("header", {})
        body = response.get("body", {})
        result_code = header.get("resultCode")
        if result_code != "00":
            raise RuntimeError(f"초단기실황 API 오류: {result_code} {header.get('resultMsg')}")

        items = body.get("items", {}).get("item", [])
        if isinstance(items, dict):
            items = [items]
        if not items:
            raise RuntimeError(
                f"초단기실황 관측값이 없습니다. base_date={base_date}, base_time={base_time}, nx={nx}, ny={ny}"
            )

        values = {item.get("category"): item.get("obsrValue") for item in items}
        return {
            "source": "ultra_short_nowcast",
            "location_label": location_label,
            "nx": nx,
            "ny": ny,
            "base_date": base_date,
            "base_time": base_time,
            "tm": f"{base_date[:4]}-{base_date[4:6]}-{base_date[6:]} {base_time[:2]}:00",
            "ta": values.get("T1H"),
            "hm": values.get("REH"),
            "ws": values.get("WSD"),
            "rn": values.get("RN1"),
            "pty": values.get("PTY"),
            "raw": values,
        }

    async def _fetch_asos_hourly_items(self, target_date: str, station_no: str) -> list[dict[str, Any]]:
        date_str = target_date.replace("-", "")
        params = {
            "serviceKey": self.api_key,
            "pageNo":     "1",
            "numOfRows":  "24",
            "dataType":   "JSON",
            "dataCd":     "ASOS",
            "dateCd":     "HR",
            "startDt":    date_str,
            "startHh":    "00",
            "endDt":      date_str,
            "endHh":      "23",
            "stnIds":     station_no,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(self.ASOS_URL, params=params)
            resp.raise_for_status()
            payload = resp.json()

        response = payload.get("response", {})
        header = response.get("header", {})
        body = response.get("body", {})
        result_code = header.get("resultCode")
        if result_code != "00":
            raise RuntimeError(f"ASOS API 오류: {result_code} {header.get('resultMsg')}")

        items = body.get("items", {}).get("item", [])
        if isinstance(items, dict):
            items = [items]
        if not items:
            raise RuntimeError(f"ASOS 관측값이 없습니다. date={target_date}, station_no={station_no}")
        return items

    async def _fetch_asos_hourly(self) -> dict[str, Any]:
        # ASOS 시간자료는 공식 문서 기준 전일(D-1)까지 제공된다.
        # 오늘 자료를 찌르지 않고 어제부터 과거 3일을 하루 범위로 조회한다.
        cursor = datetime.now(KST).date() - timedelta(days=1)
        last_status = "응답 없음"
        station_no, _ = self._get_asos_station()
        for offset in range(0, 3):
            target = cursor - timedelta(days=offset)
            try:
                items = await self._fetch_asos_hourly_items(target.isoformat(), station_no)
            except Exception as exc:
                last_status = f"{target.isoformat()} {exc}"
                continue
            if items:
                return items[-1]

        raise RuntimeError(f"최근 3일 ASOS 관측값이 없습니다. 마지막 응답: {last_status}")

    async def save_daily_asos_summary(self, target_date: str) -> dict[str, Any]:
        station_no, station_name = self._get_asos_station()
        items = await self._fetch_asos_hourly_items(target_date, station_no)
        temps = [self._parse_float(item.get("ta"), None) for item in items]
        humidities = [self._parse_float(item.get("hm"), None) for item in items]
        winds = [self._parse_float(item.get("ws"), None) for item in items]
        rains = [self._parse_rain(item.get("rn")) for item in items]

        temps = [value for value in temps if value is not None]
        humidities = [value for value in humidities if value is not None]
        winds = [value for value in winds if value is not None]
        rains = [value for value in rains if value is not None]

        def avg(values: list[float]) -> float | None:
            return round(sum(values) / len(values), 1) if values else None

        summary = {
            "date": target_date,
            "station_no": station_no,
            "station_name": station_name,
            "avg_temp": avg(temps),
            "max_temp": round(max(temps), 1) if temps else None,
            "min_temp": round(min(temps), 1) if temps else None,
            "avg_humidity": avg(humidities),
            "max_wind": round(max(winds), 1) if winds else None,
            "total_rain": round(sum(rains), 1) if rains else None,
            "hour_count": len(items),
        }
        now = datetime.now(KST).isoformat()
        with get_connection(self.safety_service.db_path) as conn:
            conn.execute(
                """
                INSERT INTO daily_weather_summary (
                    date, station_no, station_name, avg_temp, max_temp, min_temp,
                    avg_humidity, max_wind, total_rain, summary_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    station_no = excluded.station_no,
                    station_name = excluded.station_name,
                    avg_temp = excluded.avg_temp,
                    max_temp = excluded.max_temp,
                    min_temp = excluded.min_temp,
                    avg_humidity = excluded.avg_humidity,
                    max_wind = excluded.max_wind,
                    total_rain = excluded.total_rain,
                    summary_json = excluded.summary_json,
                    updated_at = excluded.updated_at
                """,
                (
                    target_date,
                    station_no,
                    station_name,
                    summary["avg_temp"],
                    summary["max_temp"],
                    summary["min_temp"],
                    summary["avg_humidity"],
                    summary["max_wind"],
                    summary["total_rain"],
                    json.dumps(summary, ensure_ascii=False),
                    now,
                    now,
                ),
            )
            conn.commit()
        return summary

    # ── 감점 계산 ──────────────────────────────────────────────────────────────

    def _calculate_weather_risk(
        self,
        observation: dict[str, Any],
    ) -> tuple[int, list[dict]]:
        triggered: list[dict] = []
        observed_at = observation.get("tm")

        try:
            temp     = self._parse_float(observation.get("ta"), 0.0)       # 기온 (C)
            humidity = self._parse_float(observation.get("hm"), 100.0)     # 상대습도 (%)
            wind     = self._parse_float(observation.get("ws"), 0.0)       # 풍속 (m/s)
            rain     = self._parse_rain(observation.get("rn"))            # 강수량 (mm/h)
        except (ValueError, TypeError):
            temp = wind = rain = 0
            humidity = 100

        if temp >= 33:
            triggered.append({"key": "high_temp", "label": "고온 (33도 이상)", "points": 5, "value": temp})
        if humidity <= 30:
            triggered.append({"key": "low_humidity", "label": "건조 (습도 30% 이하)", "points": 5, "value": humidity})
        if wind >= 14:
            triggered.append({"key": "strong_wind", "label": "강풍 (14m/s 이상)", "points": 5, "value": wind})
        if rain >= 5:
            triggered.append({"key": "heavy_rain", "label": "강수 (5mm/h 이상)", "points": 3, "value": rain})

        total = min(sum(t["points"] for t in triggered), WEATHER_MAX_DEDUCTION)
        status_detail = {
            "key": "weather_observation",
            "label": "현재 기상 실황",
            "status": "ok",
            "source": observation.get("source", "asos_hourly"),
            "station_no": self.station_no,
            "station_name": ASOS_STATION_NAMES.get(self.station_no, f"관측소 {self.station_no}"),
            "location_name": observation.get("location_label"),
            "nx": observation.get("nx"),
            "ny": observation.get("ny"),
            "base_date": observation.get("base_date"),
            "base_time": observation.get("base_time"),
            "observed_at": observed_at,
            "updated_at": datetime.now(KST).isoformat(),
            "values": {
                "temp_c": temp,
                "humidity_pct": humidity,
                "wind_mps": wind,
                "rain_mm": rain,
            },
        }
        return total, [status_detail, *triggered]

    @staticmethod
    def _parse_float(value: Any, default: float | None) -> float | None:
        if value in (None, ""):
            return default
        return float(value)

    @staticmethod
    def _parse_rain(value: Any) -> float:
        if value in (None, "", "강수없음"):
            return 0.0
        text = str(value).strip()
        if "1mm" in text and "미만" in text:
            return 0.5
        if "~" in text:
            text = text.split("~", 1)[0]
        text = text.replace("mm", "").strip()
        return float(text)
