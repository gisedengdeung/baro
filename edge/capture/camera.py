from __future__ import annotations

from typing import Optional

import cv2
import numpy as np
from loguru import logger


class Camera:
    def __init__(self, source: int = 0) -> None:
        self.source = source
        self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            logger.warning(f"카메라 소스 열기 실패: {source}")

    def read(self) -> Optional[np.ndarray]:
        if not self.cap or not self.cap.isOpened():
            return None
        ok, frame = self.cap.read()
        return frame if ok else None

    def release(self) -> None:
        if self.cap:
            self.cap.release()
