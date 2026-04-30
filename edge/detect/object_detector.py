from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
from loguru import logger
from ultralytics import YOLO

from edge.detect.inference_device import resolve_inference_device

# 안전장비 미착용 클래스 인덱스
VIOLATION_CLASSES: Dict[int, str] = {
    1: "안전모미착용",
    3: "안전대미착용",
    5: "절연장갑미착용",
    13: "스마트스틱미착용",
}


class ObjectDetector:
    def __init__(
        self,
        model_path: str = "edge/models/el_object_detection.pt",
        conf_threshold: float = 0.3,
        inference_device_request: str = "auto",
    ) -> None:
        self.inference_device = resolve_inference_device(inference_device_request)
        self.model = YOLO(model_path)
        self.model.to(self.inference_device.resolved)
        self.conf_threshold = conf_threshold
        logger.info(
            f"ObjectDetector 초기화 완료: model={model_path}, "
            f"device={self.inference_device.resolved}"
        )

    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """프레임에서 안전장비 착용 여부 및 작업자를 감지."""
        try:
            results = self.model.predict(
                source=frame,
                conf=self.conf_threshold,
                device=self.inference_device.resolved,
                verbose=False,
            )
        except Exception as exc:
            logger.error(f"객체 감지 실패: {exc}")
            return []

        detections: List[Dict[str, Any]] = []
        if results and results[0].boxes is not None:
            for box in results[0].boxes:
                cls_id = int(box.cls[0].item())
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                detections.append({
                    "class_id": cls_id,
                    "class_name": self.model.names[cls_id],
                    "bbox": [x1, y1, x2, y2],
                    "confidence": float(box.conf[0].item()),
                    "is_violation": cls_id in VIOLATION_CLASSES,
                    "violation_type": VIOLATION_CLASSES.get(cls_id),
                })
        return detections
