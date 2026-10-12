from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from loguru import logger

from shared.enums import OperationMode


@dataclass
class SystemState:
    system_is_active: bool = False
    operation_mode: OperationMode = OperationMode.STOPPED
    is_locked: bool = False
    test_is_active: bool = False
    test_target_speed: int = 0
    zones: List[Dict[str, Any]] = field(default_factory=list)


class SystemStateManager:
    def __init__(self) -> None:
        self._state = SystemState()
        logger.info("SystemStateManager 초기화 완료")

    def start_automatic_mode(self) -> None:
        if self._state.is_locked:
            logger.warning("잠금 상태에서는 AUTOMATIC 전환 불가")
            return
        self._state.system_is_active = True
        self._state.operation_mode = OperationMode.AUTOMATIC
        self._state.test_is_active = False
        self._state.test_target_speed = 0

    def start_maintenance_mode(self) -> None:
        if self._state.is_locked:
            logger.warning("잠금 상태에서는 MAINTENANCE 전환 불가")
            return
        self._state.system_is_active = True
        self._state.operation_mode = OperationMode.MAINTENANCE
        self._state.test_is_active = False
        self._state.test_target_speed = 0

    def start_test_mode(self, speed_percent: int) -> bool:
        if self._state.is_locked:
            logger.warning("잠금 상태에서는 TEST 전환 불가")
            return False
        if self._state.operation_mode != OperationMode.STOPPED:
            logger.warning(f"TEST 전환 불가: 현재 모드={self._state.operation_mode.value}")
            return False

        safe_speed = max(0, min(100, int(speed_percent)))
        self._state.system_is_active = True
        self._state.operation_mode = OperationMode.TEST
        self._state.test_is_active = True
        self._state.test_target_speed = safe_speed
        return True

    def set_test_speed(self, speed_percent: int) -> bool:
        if self._state.is_locked:
            logger.warning("잠금 상태에서는 TEST 속도 변경 불가")
            return False
        if self._state.operation_mode != OperationMode.TEST:
            logger.warning(f"TEST 속도 변경 불가: 현재 모드={self._state.operation_mode.value}")
            return False

        self._state.test_target_speed = max(0, min(100, int(speed_percent)))
        self._state.test_is_active = True
        self._state.system_is_active = True
        return True

    def stop_test_mode(self) -> None:
        self._state.system_is_active = False
        self._state.operation_mode = OperationMode.STOPPED
        self._state.test_is_active = False
        self._state.test_target_speed = 0

    def stop_system_globally(self) -> None:
        self._state.system_is_active = False
        self._state.operation_mode = OperationMode.STOPPED
        self._state.test_is_active = False
        self._state.test_target_speed = 0

    def lock_system(self, reason: str) -> None:
        if self._state.is_locked:
            return
        self._state.is_locked = True
        self._state.system_is_active = False
        self._state.operation_mode = OperationMode.STOPPED
        self._state.test_is_active = False
        self._state.test_target_speed = 0
        logger.critical(f"시스템 LOCKED: {reason}")

    def reset_system(self) -> None:
        self._state.is_locked = False
        self._state.system_is_active = False
        self._state.operation_mode = OperationMode.STOPPED
        self._state.test_is_active = False
        self._state.test_target_speed = 0

    def set_zones(self, zones: List[Dict[str, Any]]) -> None:
        self._state.zones = zones

    def get_status(self) -> Dict[str, Any]:
        return {
            "system_is_active": self._state.system_is_active,
            "operation_mode": self._state.operation_mode.value,
            "is_locked": self._state.is_locked,
            "test_is_active": self._state.test_is_active,
            "test_speed": self._state.test_target_speed,
            "zones_count": len(self._state.zones),
        }

    def is_active(self) -> bool:
        return self._state.system_is_active and not self._state.is_locked

    def is_locked_status(self) -> bool:
        return self._state.is_locked

    def get_mode(self) -> OperationMode:
        return self._state.operation_mode

    def get_test_target_speed(self) -> int:
        return self._state.test_target_speed

    @property
    def zones(self) -> List[Dict[str, Any]]:
        return self._state.zones
