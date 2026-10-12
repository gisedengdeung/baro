from __future__ import annotations

from typing import Dict

from edge.capture.serial_comm import SerialComm


class BuzzerController:
    def __init__(self, serial: SerialComm) -> None:
        self.serial = serial
        self._is_alert_on = False

    def trigger_medium(self) -> None:
        self.serial.send_command("b_medium")
        self._is_alert_on = True

    def trigger_high(self) -> None:
        self.serial.send_command("b_high")
        self._is_alert_on = True

    def trigger_critical(self) -> None:
        self.serial.send_command("b_critical")
        self._is_alert_on = True

    def stop(self) -> None:
        self.serial.send_command("b_stop")
        self._is_alert_on = False

    def get_status(self) -> Dict[str, bool]:
        return {"is_alert_on": self._is_alert_on}
