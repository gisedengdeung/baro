from __future__ import annotations

from typing import Any, Dict

import cv2
import numpy as np
from loguru import logger


class FireDetector:
    """색상 분포 기반의 경량 화재 후보 감지기."""

    def __init__(self, ratio_threshold: float = 0.02) -> None:
        self.ratio_threshold = ratio_threshold
        logger.info(f"FireDetector 초기화 완료: ratio_threshold={ratio_threshold}")

    def analyze(self, frame: np.ndarray) -> Dict[str, Any]:
        try:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            mask_red_1 = cv2.inRange(hsv, (0, 120, 120), (12, 255, 255))
            mask_red_2 = cv2.inRange(hsv, (165, 120, 120), (180, 255, 255))
            mask_orange = cv2.inRange(hsv, (10, 110, 110), (28, 255, 255))
            fire_mask = cv2.bitwise_or(mask_red_1, mask_red_2)
            fire_mask = cv2.bitwise_or(fire_mask, mask_orange)

            ratio = float(cv2.countNonZero(fire_mask)) / float(max(1, frame.shape[0] * frame.shape[1]))
            is_fire = ratio >= self.ratio_threshold
            return {
                "is_fire": is_fire,
                "score": round(ratio, 4),
            }
        except Exception as exc:
            logger.warning(f"화재 감지 실패: {exc}")
            return {"is_fire": False, "score": 0.0}
