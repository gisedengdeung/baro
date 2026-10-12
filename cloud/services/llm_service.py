from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from openai import AsyncOpenAI

from cloud.db import get_connection
from cloud.services.safety_service import SafetyService

KST = ZoneInfo("Asia/Seoul")

EVENT_LABEL_MAP: dict[str, str] = {
    "LOG_CRITICAL_FALLING": "넘어짐(낙상) 감지",
    "LOG_INTRUSION_SLOWDOWN": "위험구역 침입 감지",
    "LOG_HELMET_MISSING": "안전모 미착용",
    "LOG_FIRE_DETECTED": "화재 감지",
    "LOG_SLIP_DETECTED": "미끄러짐 감지",
    "LOG_RESTRICTED_AREA": "제한구역 진입",
    "LOG_EQUIPMENT_FAULT": "장비 이상",
    "LOG_POSTURE_RISK": "위험 자세 감지",
}

SYSTEM_PROMPT = """당신은 산업 현장 안전 전문가 AI입니다.
공장의 오늘 안전 데이터를 분석하고 관리자에게 실용적인 조치 권고를 제공합니다.

반드시 아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{
  "summary": "오늘의 안전 상황 전반 요약 (2~3문장)",
  "warnings": [
    {
      "event_label": "이벤트 이름",
      "count": 발생횟수,
      "threshold": 당신이_판단한_주의기준횟수,
      "message": "해당 이벤트에 대한 구체적인 유의 문구와 조치사항"
    }
  ],
  "recommendations": ["권고사항1", "권고사항2", "권고사항3"]
}

warnings는 오늘 발생한 이벤트 중 당신이 판단했을 때 주의가 필요한 것만 포함하세요.
threshold(기준횟수)는 이벤트의 위험도와 업종 특성을 고려해 당신이 직접 결정하세요.
count가 threshold 이상인 이벤트에만 경고를 포함하세요.
이벤트가 없거나 모두 threshold 미만이면 warnings는 빈 배열로 하세요.
recommendations는 항상 2~3개 포함하세요."""


class LLMService:
    def __init__(self, api_key: str, db_path: str, safety_service: SafetyService) -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.db_path = db_path
        self.safety_service = safety_service

    def _get_today_events(self) -> list[dict[str, Any]]:
        today = datetime.now(KST).date().isoformat()
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT event_type, log_risk_level, COUNT(*) as cnt
                FROM event_logs
                WHERE timestamp >= ? AND timestamp < ?
                GROUP BY event_type, log_risk_level
                ORDER BY cnt DESC
                """,
                (f"{today}T00:00:00", f"{today}T23:59:59"),
            ).fetchall()

        return [
            {
                "event_type": row["event_type"],
                "label": EVENT_LABEL_MAP.get(row["event_type"], row["event_type"]),
                "count": row["cnt"],
                "risk_level": row["log_risk_level"],
            }
            for row in rows
        ]

    def _build_user_message(self, score_data: dict[str, Any], events: list[dict]) -> str:
        difficulty = score_data.get("difficulty", {})
        factors = difficulty.get("factors", {})
        event_deduction = score_data.get("event_deduction", {})
        weather_details = factors.get("weather", {}).get("details", [])
        weather_obs = next(
            (d for d in weather_details if d.get("key") == "weather_observation"), None
        )
        weather_triggers = [
            d["label"]
            for d in weather_details
            if d.get("key") not in ("weather_observation", "weather_api_error")
        ]

        lines: list[str] = [
            f"=== 오늘의 안전 데이터 ({score_data.get('date', '')}) ===",
            "",
            "[안전점수]",
            f"- 오늘 점수: {score_data.get('score')}점 / 100점",
            f"- 무사고 연속: {score_data.get('accident_free_streak')}일",
            "",
            "[금일 위험도]",
            f"- 종합 위험도: {difficulty.get('score')}점 ({difficulty.get('level')}, 감점 배율 ×{difficulty.get('multiplier')})",
            f"- 업종: {factors.get('industry', {}).get('label', '미설정')} (위험도 {factors.get('industry', {}).get('risk', 0)}점)",
            f"- 규모: {factors.get('size', {}).get('scale', '미분류')} (위험도 {factors.get('size', {}).get('risk', 0)}점)",
            f"- 기상 위험도: {factors.get('weather', {}).get('risk', 0)}점",
        ]

        if weather_obs and weather_obs.get("values"):
            v = weather_obs["values"]
            lines.append(
                f"  (기온 {v.get('temp_c')}°C, 습도 {v.get('humidity_pct')}%, 풍속 {v.get('wind_mps')}m/s, 강수 {v.get('rain_mm')}mm)"
            )
        if weather_triggers:
            lines.append(f"  기상 경보: {', '.join(weather_triggers)}")

        lines += [
            "",
            "[AI 감지 이벤트 감점]",
            f"- 기본 감점: {event_deduction.get('base', 0)}점",
            f"- 배율 적용 후 최종 감점: {event_deduction.get('adjusted', 0)}점",
            "",
            "[오늘 감지된 이벤트]",
        ]

        if events:
            for e in events:
                lines.append(f"- {e['label']}: {e['count']}회 (위험등급: {e['risk_level']})")
        else:
            lines.append("- 감지된 이벤트 없음")

        return "\n".join(lines)

    async def explain(self) -> dict[str, Any]:
        score_data = self.safety_service.get_today_score()
        events = self._get_today_events()
        user_message = self._build_user_message(score_data, events)

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            max_tokens=1200,
            temperature=0.3,
        )

        raw = response.choices[0].message.content or "{}"
        try:
            analysis = json.loads(raw)
        except json.JSONDecodeError:
            analysis = {"summary": raw, "warnings": [], "recommendations": []}

        return {
            "date": score_data.get("date"),
            "score": score_data.get("score"),
            "analysis": analysis,
            "event_summary": events,
        }
