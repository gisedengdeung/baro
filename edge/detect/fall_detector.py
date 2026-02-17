from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import torch
from loguru import logger
from ultralytics import YOLO


class FallDetector:
    def __init__(self, model_path: str = "fall_det_1.pt", conf_threshold: float = 0.4) -> None:
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = YOLO(model_path)
        self.model.to(self.device)
        self.conf_threshold = conf_threshold
        logger.info(f"FallDetector 초기화 완료: model={model_path}")

    @staticmethod
    def _calculate_iou(box_a: np.ndarray, box_b: np.ndarray) -> float:
        x_a = max(box_a[0], box_b[0])
        y_a = max(box_a[1], box_b[1])
        x_b = min(box_a[2], box_b[2])
        y_b = min(box_a[3], box_b[3])

        inter = max(0, x_b - x_a) * max(0, y_b - y_a)
        area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
        area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])

        denom = float(area_a + area_b - inter)
        if denom <= 0:
            return 0.0
        return inter / denom

    def analyze(self, frame: np.ndarray, persons: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not persons:
            return []

        try:
            fall_results = self.model.predict(
                source=frame,
                conf=self.conf_threshold,
                device=self.device,
                verbose=False,
            )
        except Exception as exc:
            logger.error(f"넘어짐 감지 실패: {exc}")
            return persons

        fall_boxes: List[np.ndarray] = []
        if fall_results and fall_results[0].boxes:
            for box in fall_results[0].boxes:
                class_name = self.model.names[int(box.cls)]
                if class_name == "Fall-Detected":
                    fall_boxes.append(box.xyxy[0].cpu().numpy().astype(int))

        for person in persons:
            person_bbox = np.array(person["bbox"])
            analysis = {
                "is_falling": False,
                "is_crouching": False,
                "risk_level": "low",
                "description": "Normal",
            }

            x1, y1, x2, y2 = person_bbox
            width = x2 - x1
            height = y2 - y1
            if height <= 0:
                person["pose_analysis"] = analysis
                continue

            is_model_falling = any(self._calculate_iou(person_bbox, fb) > 0.5 for fb in fall_boxes)
            is_ratio_falling = width > height * 1.4
            if is_model_falling and is_ratio_falling:
                analysis = {
                    "is_falling": True,
                    "is_crouching": False,
                    "risk_level": "critical",
                    "description": "Falling Detected (Verified by BBox Ratio)",
                }

            person["pose_analysis"] = analysis

        return persons
