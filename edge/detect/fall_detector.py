from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
from loguru import logger
from ultralytics import YOLO

from edge.detect.inference_device import resolve_inference_device


class FallDetector:
    def __init__(
        self,
        model_path: str = "edge/models/fall_det_1.pt",
        conf_threshold: float = 0.4,
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
            "FallDetector 초기화 완료: "
            f"model={model_path}, "
            f"requested_device={self.inference_device.requested}, "
            f"resolved_device={self.inference_device.resolved}, "
            f"cuda_available={self.inference_device.cuda_available}"
            f"{gpu_suffix}"
        )

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
        try:
            fall_results = self.model.predict(
                source=frame,
                conf=self.conf_threshold,
                device=self.inference_device.resolved,
                verbose=False,
            )
        except Exception as exc:
            logger.error(f"넘어짐 감지 실패: {exc}")
            return persons

        fall_boxes: List[np.ndarray] = []
        if fall_results and fall_results[0].boxes and len(fall_results[0].boxes):
            raw_confs = [(self.model.names[int(b.cls)], float(b.conf[0])) for b in fall_results[0].boxes]
            logger.info(f"[FallDetector] 원시 감지: {raw_confs}")
            for box in fall_results[0].boxes:
                class_name = self.model.names[int(box.cls)]
                if class_name == "Fallen":
                    fall_boxes.append(box.xyxy[0].cpu().numpy().astype(int))
        else:
            logger.info("[FallDetector] 감지 결과 없음 (conf 임계값 미만 또는 미탐지)")

        if not fall_boxes:
            for person in persons:
                person["pose_analysis"] = {
                    "is_falling": False,
                    "is_crouching": False,
                    "risk_level": "low",
                    "description": "Normal",
                }
            return persons

        # fall 감지된 경우: 기존 person bbox와 IoU 매칭 시도
        # 매칭 안 되면 fall_box를 person으로 직접 추가 (누운 상태라 PersonDetector가 놓친 경우)
        matched_fall_indices: set[int] = set()
        for person in persons:
            person_bbox = np.array(person["bbox"])
            is_falling = False
            for fi, fb in enumerate(fall_boxes):
                if self._calculate_iou(person_bbox, fb) > 0.3:
                    is_falling = True
                    matched_fall_indices.add(fi)
            person["pose_analysis"] = {
                "is_falling": is_falling,
                "is_crouching": False,
                "risk_level": "critical" if is_falling else "low",
                "description": "Falling Detected" if is_falling else "Normal",
            }

        for fi, fb in enumerate(fall_boxes):
            if fi not in matched_fall_indices:
                x1, y1, x2, y2 = fb
                persons.append({
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    "confidence": float(fall_results[0].boxes[fi].conf[0].item()),
                    "pose_analysis": {
                        "is_falling": True,
                        "is_crouching": False,
                        "risk_level": "critical",
                        "description": "Falling Detected (unmatched)",
                    },
                })

        return persons
