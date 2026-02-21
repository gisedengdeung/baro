from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import torch
from loguru import logger
from ultralytics import YOLO


class PersonDetector:
    def __init__(self, model_path: str = "yolov8n.pt", conf_threshold: float = 0.3) -> None:
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = YOLO(model_path)
        self.model.to(self.device)
        self.conf_threshold = conf_threshold
        logger.info(f"PersonDetector 초기화 완료: model={model_path}")

    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        try:
            results = self.model.predict(
                source=frame,
                conf=self.conf_threshold,
                classes=[0],
                device=self.device,
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
