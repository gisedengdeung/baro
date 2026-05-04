from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from cloud.dependencies import get_safety_service, get_weather_service
from cloud.services.safety_service import SafetyService
from cloud.services.weather_service import WeatherService

router = APIRouter()


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


@router.post("/weather/refresh")
async def refresh_weather(
    weather: WeatherService = Depends(get_weather_service),
) -> dict[str, str]:
    """기상 데이터 수동 새로고침 (평소엔 자동으로 1시간마다 실행됨)"""
    await weather.refresh()
    return {"status": "ok"}
