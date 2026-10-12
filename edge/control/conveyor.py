from __future__ import annotations

from typing import Dict

from loguru import logger

from edge.capture.serial_comm import SerialComm


class ConveyorController:
    def __init__(self, serial: SerialComm) -> None:
        self.serial = serial
        self.is_on = False
        self.speed_percent = 0

    def power_on(self, reason: str = "System start") -> None:
        if self.is_on:
            return
        logger.info(f"컨베이어 전원 ON: {reason}")
        self.serial.send_command("p1")
        self.serial.send_command("s255")
        self.is_on = True
        self.speed_percent = 100

    def power_off(self, reason: str = "System stop") -> None:
        if not self.is_on and self.speed_percent == 0:
            return
        logger.warning(f"컨베이어 전원 OFF: {reason}")
        self.serial.send_command("p0")
        self.is_on = False
        self.speed_percent = 0

    def set_speed(self, percent: int, reason: str = "speed_update") -> None:
        if percent < 0 or percent > 100:
            logger.warning(f"속도 값 범위 오류: {percent}")
            return
        if self.speed_percent == percent:
            return

        pwm = int((percent / 100) * 255)
        self.serial.send_command(f"s{pwm}")
        self.speed_percent = percent
        self.is_on = percent > 0
        logger.info(f"컨베이어 속도 변경: {percent}% (PWM={pwm}) reason={reason}")

    def get_status(self) -> Dict[str, int | bool]:
        return {"conveyor_is_on": self.is_on, "conveyor_speed": self.speed_percent}
