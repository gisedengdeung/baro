from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from cloud.dependencies import (
    get_db_service,
    get_llm_service,
    get_location_service,
    get_safety_service,
    get_weather_service,
)
from cloud.services.db_service import DBService
from cloud.services.llm_service import LLMService
from cloud.services.location_service import LocationService
from cloud.services.safety_service import SafetyService
from cloud.services.weather_service import WeatherService

router = APIRouter()
KST = ZoneInfo("Asia/Seoul")
DAILY_REPORT_EVENT_RISK_LEVELS = {"CRITICAL"}


class ConfigUpdateRequest(BaseModel):
    key: str
    value: str


@router.get("/score")
def get_today_score(
    safety: SafetyService = Depends(get_safety_service),
) -> dict[str, Any]:
    return safety.get_today_score()


@router.get("/history")
def get_history(
    days: int = 7,
    safety: SafetyService = Depends(get_safety_service),
) -> list[dict[str, Any]]:
    if not 1 <= days <= 90:
        raise HTTPException(status_code=400, detail="days 는 1~90 사이여야 합니다")
    return safety.get_history(days)


@router.get("/daily-report")
def get_daily_report(
    days: int = 30,
    safety: SafetyService = Depends(get_safety_service),
    db_service: DBService = Depends(get_db_service),
) -> list[dict[str, Any]]:
    if not 1 <= days <= 90:
        raise HTTPException(status_code=400, detail="days 는 1~90 사이여야 합니다")

    report = safety.get_daily_report(days)
    if not report:
        return []

    oldest = min(item["date"] for item in report)
    newest = max(item["date"] for item in report)
    events = db_service.get_events_between(
        f"{oldest}T00:00:00",
        f"{newest}T23:59:59",
    )
    events_by_date: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        if event.get("log_risk_level") not in DAILY_REPORT_EVENT_RISK_LEVELS:
            continue
        day = str(event.get("timestamp", ""))[:10]
        events_by_date.setdefault(day, []).append(event)

    for item in report:
        item_events = events_by_date.get(item["date"], [])
        counts: dict[str, int] = {}
        for event in item_events:
            event_type = event.get("event_type", "UNKNOWN")
            counts[event_type] = counts.get(event_type, 0) + 1
        item["events"] = item_events
        item["event_counts"] = counts
        item["event_total"] = len(item_events)
    return report


@router.get("/config")
def get_config(
    safety: SafetyService = Depends(get_safety_service),
) -> dict[str, str]:
    return safety.get_all_config()


@router.patch("/config")
def update_config(
    body: ConfigUpdateRequest,
    safety: SafetyService = Depends(get_safety_service),
) -> dict[str, str]:
    safety.set_config(body.key, body.value)
    return {"key": body.key, "value": body.value}


@router.get("/location/search")
async def search_location(
    query: str,
    location: LocationService = Depends(get_location_service),
) -> list[dict[str, Any]]:
    try:
        return await location.search_address(query)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/weather/refresh")
async def refresh_weather(
    weather: WeatherService = Depends(get_weather_service),
) -> dict[str, Any]:
    """기상 데이터 수동 새로고침 (평소엔 자동으로 1시간마다 실행됨)"""
    result = await weather.refresh(raise_on_error=True)
    return {"status": "ok", **result}


@router.post("/weather/daily-summary")
async def refresh_daily_weather_summary(
    date: str | None = None,
    weather: WeatherService = Depends(get_weather_service),
) -> dict[str, Any]:
    target_date = date or (datetime.now(KST).date() - timedelta(days=1)).isoformat()
    result = await weather.save_daily_asos_summary(target_date)
    return {"status": "ok", "data": result}


@router.post("/explain")
async def explain_safety(
    llm: LLMService = Depends(get_llm_service),
) -> dict[str, Any]:
    """오늘의 안전 데이터를 AI가 분석해 한국어 안전 진단 + 유의 문구를 반환합니다."""
    return await llm.explain()
