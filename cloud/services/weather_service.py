from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from loguru import logger

from cloud.services.safety_service import WEATHER_MAX_DEDUCTION, SafetyService

KST = ZoneInfo("Asia/Seoul")

ASOS_STATION_NAMES: dict[str, str] = {
    "108": "서울",
    "112": "인천",
    "119": "수원",
}


class WeatherService:
    """
    기상청 ASOS 시간자료를 호출해 SafetyService의 기상 위험도를 업데이트합니다.

    필요 환경변수:
      KMA_API_KEY          공공데이터포털 인증키
      KMA_ASOS_STATION_NO  기상관측소 지점번호 (108=서울, 112=인천, 119=수원 ...)
    """

    ASOS_URL = (
        "https://apis.data.go.kr/1360000/AsosHourlyInfoService/getWthrDataList"
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

    async def refresh(self) -> None:
        """기상 데이터 조회 → 위험도 계산 → SafetyService 업데이트"""
        try:
            asos_data = await self._fetch_asos_hourly()
            risk, details = self._calculate_weather_risk(asos_data)
            self.safety_service.update_weather_deduction(risk, details)
            logger.info(f"기상 위험도 업데이트: +{risk}점 (조건 {len(details)}개)")
        except Exception as exc:
            logger.warning(f"기상 API 호출 실패, 기존 위험도 유지: {exc}")

    # ── API 호출 ───────────────────────────────────────────────────────────────

    async def _fetch_asos_hourly(self) -> dict[str, Any]:
        # ASOS 시간자료는 공식 문서 기준 전일(D-1)까지 제공된다.
        # 오늘 자료를 찌르지 않고 어제부터 과거 3일을 하루 범위로 조회한다.
        cursor = datetime.now(KST).date() - timedelta(days=1)
        last_status = "응답 없음"
        async with httpx.AsyncClient(timeout=10) as client:
            for offset in range(0, 3):
                target = cursor - timedelta(days=offset)
                date_str = target.strftime("%Y%m%d")
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
                    "stnIds":     self.station_no,
                }
                resp = await client.get(self.ASOS_URL, params=params)
                resp.raise_for_status()

                payload = resp.json()
                response = payload.get("response", {})
                header = response.get("header", {})
                body = response.get("body", {})
                result_code = header.get("resultCode")
                result_msg = header.get("resultMsg")
                total_count = body.get("totalCount")
                last_status = (
                    f"{target.isoformat()} "
                    f"resultCode={result_code}, resultMsg={result_msg}, totalCount={total_count}"
                )

                items = body.get("items", {}).get("item", [])
                if isinstance(items, dict):
                    items = [items]
                if items:
                    return items[-1]

        raise RuntimeError(f"최근 3일 ASOS 관측값이 없습니다. 마지막 응답: {last_status}")

    # ── 감점 계산 ──────────────────────────────────────────────────────────────

    def _calculate_weather_risk(
        self,
        asos: dict[str, Any],
    ) -> tuple[int, list[dict]]:
        triggered: list[dict] = []
        observed_at = asos.get("tm")

        # ASOS 실측값 파싱
        try:
            temp     = float(asos.get("ta", 0) or 0)       # 기온 (C)
            humidity = float(asos.get("hm", 100) or 100)   # 상대습도 (%)
            wind     = float(asos.get("ws", 0) or 0)       # 풍속 (m/s)
            rain     = float(asos.get("rn", 0) or 0)       # 강수량 (mm/h)
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
            "label": "ASOS 최근 관측값",
            "status": "ok",
            "station_no": self.station_no,
            "station_name": ASOS_STATION_NAMES.get(self.station_no, f"관측소 {self.station_no}"),
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
