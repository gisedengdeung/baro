from __future__ import annotations

import json
import threading
import time
from typing import Callable, Optional

import serial
from loguru import logger


class SerialComm:
    """아두이노 시리얼 통신과 비상 정지 콜백을 담당합니다."""

    def __init__(self, port: str, baud_rate: int, mock_mode: bool = False) -> None:
        self.port = port
        self.baud_rate = baud_rate
        self.mock_mode = mock_mode

        self._serial: Optional[serial.Serial] = None
        self._lock = threading.Lock()

        self._is_listening = False
        self._listener_thread: Optional[threading.Thread] = None

        self._lock_system_callback: Optional[Callable[[str], None]] = None
        self._is_locked_checker: Optional[Callable[[], bool]] = None

        if not self.mock_mode:
            self._connect()

    def _connect(self) -> None:
        with self._lock:
            try:
                if self._serial and self._serial.is_open:
                    self._serial.close()
                self._serial = serial.Serial(self.port, self.baud_rate, timeout=1)
                time.sleep(2)
                logger.info(f"시리얼 연결 성공: {self.port} @ {self.baud_rate}")
            except serial.SerialException as exc:
                logger.error(f"시리얼 연결 실패, mock 전환: {exc}")
                self.mock_mode = True
                self._serial = None

    def set_lock_system_callback(self, callback: Callable[[str], None]) -> None:
        self._lock_system_callback = callback

    def set_is_locked_checker(self, checker: Callable[[], bool]) -> None:
        self._is_locked_checker = checker

    def _listening_loop(self) -> None:
        logger.info("시리얼 리스너 시작")
        while self._is_listening:
            line = self.read_line()
            if not line:
                time.sleep(0.1)
                continue

            if not line.lstrip().startswith("{"):
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            is_auto_off = (
                data.get("type") == "STATUS"
                and data.get("source") == "AUTO"
                and data.get("power") == "OFF"
            )
            if not is_auto_off:
                continue

            already_locked = self._is_locked_checker() if self._is_locked_checker else False
            if already_locked:
                continue

            if self._lock_system_callback:
                self._lock_system_callback("Hardware auto power-off detected")

        logger.info("시리얼 리스너 종료")

    def start_listening(self) -> None:
        if self.mock_mode:
            return
        if self._is_listening:
            return
        self._is_listening = True
        self._listener_thread = threading.Thread(target=self._listening_loop, daemon=True)
        self._listener_thread.start()

    def send_command(self, command: str) -> None:
        if self.mock_mode:
            logger.info(f"[MOCK] 시리얼 명령 전송: {command}")
            return

        with self._lock:
            try:
                if not self._serial or not self._serial.is_open:
                    self._connect()
                if not self._serial:
                    return
                self._serial.write(f"{command}\n".encode("utf-8"))
            except serial.SerialException as exc:
                logger.error(f"시리얼 송신 실패: {exc}")
                self._connect()

    def read_line(self) -> Optional[str]:
        if self.mock_mode:
            return None

        with self._lock:
            if not self._serial or not self._serial.is_open:
                return None
            try:
                if self._serial.in_waiting <= 0:
                    return None
                return self._serial.readline().decode("utf-8", errors="ignore").strip()
            except serial.SerialException as exc:
                logger.error(f"시리얼 수신 실패: {exc}")
                self._connect()
                return None

    def close(self) -> None:
        self._is_listening = False
        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=1)

        with self._lock:
            if self._serial and self._serial.is_open:
                self._serial.close()
