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

        persons = detection_result.get("persons", [])
        for idx, person in enumerate(persons):
            analysis = person.get("pose_analysis", {})
            if analysis.get("is_falling"):
                risk_factors.append({"type": "POSTURE_FALLING", "person_id": idx})
            elif analysis.get("is_crouching"):
                risk_factors.append({"type": "POSTURE_CROUCHING", "person_id": idx})

        zone_alerts = detection_result.get("danger_zone_alerts", [])
        if zone_alerts:
            risk_factors.append({"type": "ZONE_INTRUSION", "details": zone_alerts})

        fire = detection_result.get("fire_detection", {})
        if fire.get("is_fire"):
            risk_factors.append({"type": "FIRE_DETECTED", "score": fire.get("score", 0.0)})

        entrapment = detection_result.get("entrapment_detection", {})
        if entrapment.get("is_entrapment"):
            risk_factors.append(
                {
                    "type": "ENTRAPMENT_DETECTED",
                    "zone_id": entrapment.get("zone_id"),
                    "person_index": entrapment.get("person_index"),
                    "score": entrapment.get("score"),
                }
            )

        for sensor_type, sensor_info in sensor_data.get("sensors", {}).items():
            if sensor_info.get("is_alert"):
                risk_factors.append({"type": "SENSOR_ALERT", "sensor_type": sensor_type})

        return {"risk_factors": risk_factors}
