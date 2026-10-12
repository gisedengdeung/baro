from __future__ import annotations

from typing import Optional

import cv2
import numpy as np
from loguru import logger


class Camera:
    def __init__(self, source: int = 0, width: int = 1920, height: int = 1080) -> None:
        self.source = source
        self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            logger.warning(f"Failed to open camera source: {source}")
            return

        if width > 0:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(width))
        if height > 0:
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(height))

        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        logger.info(
            f"Camera resolution configured: requested={width}x{height}, actual={actual_width}x{actual_height}"
        )

    def read(self) -> Optional[np.ndarray]:
        if not self.cap or not self.cap.isOpened():
            return None
        ok, frame = self.cap.read()
        return frame if ok else None

    def release(self) -> None:
        if self.cap:
            self.cap.release()
