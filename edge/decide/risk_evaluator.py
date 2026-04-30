from __future__ import annotations

from typing import Any, Dict, List

from loguru import logger


class RiskEvaluator:
    """탐지 결과를 기반으로 위험 사실 목록을 계산합니다."""

    def __init__(self) -> None:
        logger.info("RiskEvaluator 초기화 완료")

    def evaluate(
        self,
        detection_result: Dict[str, Any],
        sensor_data: Dict[str, Any],
        conveyor_status: bool,
    ) -> Dict[str, List[Dict[str, Any]]]:
        risk_factors: List[Dict[str, Any]] = []

        # 행동 인식: 사고 유형 감지
        action_result = detection_result.get("action_result")
        if action_result and action_result.get("is_accident"):
            risk_factors.append({
                "type": "ACTION_ACCIDENT",
                "class_name": action_result.get("class_name", "unknown"),
                "confidence": action_result.get("confidence", 0.0),
            })

        # 안전 장비 미착용 감지
        violations = detection_result.get("violations", [])
        for v in violations:
            if v.get("is_violation"):
                risk_factors.append({
                    "type": "SAFETY_EQUIPMENT_VIOLATION",
                    "class_name": v.get("class_name", "unknown"),
                    "bbox": v.get("bbox"),
                })

        # 구역 침입 감지
        zone_alerts = detection_result.get("danger_zone_alerts", [])
        if zone_alerts:
            risk_factors.append({"type": "ZONE_INTRUSION", "details": zone_alerts})

        # 하드웨어 센서 경보
        for sensor_type, sensor_info in sensor_data.get("sensors", {}).items():
            if sensor_info.get("is_alert"):
                risk_factors.append({"type": "SENSOR_ALERT", "sensor_type": sensor_type})

        return {"risk_factors": risk_factors}
