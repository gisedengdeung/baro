from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
from loguru import logger
from ultralytics import YOLO

from edge.detect.inference_device import resolve_inference_device


class PersonDetector:
    def __init__(
        self,
        model_path: str = "edge/models/yolov8n.pt",
        conf_threshold: float = 0.3,
        inference_device_request: str = "auto",
    ) -> None:
        self.inference_device = resolve_inference_device(inference_device_request)
        self.model = YOLO(model_path)
        self.model.to(self.inference_device.resolved)
        self.conf_threshold = conf_threshold
        gpu_suffix = (
            f", gpu_name={self.inference_device.gpu_name}"
            if self.inference_device.gpu_name
            else ""
        )
        logger.info(
            "PersonDetector 초기화 완료: "
            f"model={model_path}, "
            f"requested_device={self.inference_device.requested}, "
            f"resolved_device={self.inference_device.resolved}, "
            f"cuda_available={self.inference_device.cuda_available}"
            f"{gpu_suffix}"
        )

    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        try:
            results = self.model.predict(
                source=frame,
                conf=self.conf_threshold,
                classes=[0],
                device=self.inference_device.resolved,
                verbose=False,
            )
        except Exception as exc:
            logger.error(f"사람 감지 실패: {exc}")
            return []

        persons: List[Dict[str, Any]] = []
        if results and results[0].boxes is not None:
            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                persons.append(
                    {
                        "bbox": [x1, y1, x2, y2],
                        "confidence": float(box.conf[0].item()),
                    }
                )
        return persons
