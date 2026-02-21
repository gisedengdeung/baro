from __future__ import annotations

from typing import Any, Dict, List

from loguru import logger

from shared.enums import OperationMode


class RuleEngine:
    """모드/위험요인 기반으로 제어 액션을 결정합니다."""

    def __init__(self) -> None:
        self.last_system_state: str | None = None
        logger.info("RuleEngine 초기화 완료")

    def decide_actions(
        self,
        mode: str,
        risk_analysis: Dict[str, Any],
        conveyor_is_on: bool,
        current_speed_percent: int,
    ) -> List[Dict[str, Any]]:
        actions: List[Dict[str, Any]] = []
        risk_factors = risk_analysis.get("risk_factors", [])

        if mode in {"STOP", OperationMode.STOPPED.value, "STOPPED"}:
            if conveyor_is_on:
                actions.append({"type": "POWER_OFF", "details": {"reason": "system_stopped_by_user"}})
            return actions

        has_intrusion = any(f["type"] == "ZONE_INTRUSION" for f in risk_factors)
        is_falling = any(f["type"] == "POSTURE_FALLING" for f in risk_factors)
        is_crouching = any(f["type"] == "POSTURE_CROUCHING" for f in risk_factors)
        has_sensor_alert = any(f["type"] == "SENSOR_ALERT" for f in risk_factors)

        log_action: Dict[str, Any] | None = None

        if is_falling or has_sensor_alert:
            if has_sensor_alert:
                reason = "sensor_alert"
                log_type = "LOG_CRITICAL_SENSOR"
            else:
                reason = "falling_detected"
                log_type = "LOG_CRITICAL_FALLING"

            actions.append({"type": "POWER_OFF", "details": {"reason": reason}})
            actions.append({"type": "TRIGGER_ALARM_CRITICAL", "details": {"reason": reason}})
            actions.append({"type": "LOCK_SYSTEM", "details": {"reason": reason}})
            log_action = {"type": log_type, "details": {}}

        elif mode == OperationMode.MAINTENANCE.value:
            if conveyor_is_on:
                actions.append({"type": "POWER_OFF", "details": {"reason": "maintenance_mode_active"}})

            if has_intrusion:
                actions.append({"type": "TRIGGER_ALARM_CRITICAL", "details": {"reason": "LOTO_zone_intrusion"}})
                log_action = {"type": "LOG_LOTO_ACTIVE", "details": {}}
            else:
                actions.append({"type": "STOP_ALARM", "details": {"reason": "maintenance_zone_clear"}})
                log_action = {"type": "LOG_MAINTENANCE_SAFE", "details": {}}

        elif mode == OperationMode.AUTOMATIC.value:
            if has_intrusion:
                if current_speed_percent != 50:
                    actions.append({"type": "REDUCE_SPEED_50", "details": {"reason": "zone_intrusion"}})
                actions.append({"type": "TRIGGER_ALARM_HIGH", "details": {"reason": "intrusion"}})
                log_action = {"type": "LOG_INTRUSION_SLOWDOWN", "details": {}}
            elif is_crouching:
                actions.append({"type": "TRIGGER_ALARM_MEDIUM", "details": {"reason": "crouching"}})
                log_action = {"type": "LOG_CROUCHING_WARN", "details": {}}
            else:
                if not conveyor_is_on:
                    actions.append({"type": "POWER_ON", "details": {"reason": "normal_operation"}})
                if current_speed_percent < 100:
                    actions.append({"type": "RESUME_FULL_SPEED", "details": {"reason": "safety_zone_clear"}})
                actions.append({"type": "STOP_ALARM", "details": {"reason": "safety_zone_clear"}})
                log_action = {"type": "LOG_NORMAL_OPERATION", "details": {}}

        current_state = log_action["type"] if log_action else "NO_ACTION"
        if current_state != self.last_system_state:
            if log_action:
                actions.append(log_action)
            self.last_system_state = current_state

        return actions
