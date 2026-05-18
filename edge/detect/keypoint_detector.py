from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
from loguru import logger
from ultralytics import YOLO

from edge.detect.inference_device import resolve_inference_device

JOINT_N = 17


class KeypointDetector:
    def __init__(
        self,
        model_path: str = "edge/models/yolov8s-pose.pt",
        conf_threshold: float = 0.3,
        inference_device_request: str = "auto",
    ) -> None:
        self.inference_device = resolve_inference_device(inference_device_request)
        self.model = YOLO(model_path)
        self.model.to(self.inference_device.resolved)
        self.conf_threshold = conf_threshold
        logger.info(
            f"KeypointDetector 초기화 완료: model={model_path}, "
            f"device={self.inference_device.resolved}"
        )

    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        try:
            results = self.model.predict(
                source=frame,
                conf=self.conf_threshold,
                device=self.inference_device.resolved,
                verbose=False,
            )
        except Exception as exc:
            logger.error(f"keypoint 감지 실패: {exc}")
            return []

        persons: List[Dict[str, Any]] = []
        if results and results[0].keypoints is not None and results[0].boxes is not None:
            boxes = results[0].boxes
            kpts_data = results[0].keypoints.data.cpu().numpy()       # (N, 17, 3) 픽셀 좌표
            kpts_norm = results[0].keypoints.xyn.cpu().numpy()        # (N, 17, 2) 정규화 좌표
            xyxy = boxes.xyxy.cpu().numpy()
            xywh = boxes.xywh.cpu().numpy()
            confs = boxes.conf.cpu().numpy()
            for i in range(len(xyxy)):
                x1, y1, x2, y2 = map(int, xyxy[i])
                raw = kpts_data[i] if i < len(kpts_data) else np.zeros((JOINT_N, 3))
                norm = kpts_norm[i] if i < len(kpts_norm) else np.zeros((JOINT_N, 2))
                keypoints = [[float(raw[j][0]), float(raw[j][1])] for j in range(JOINT_N)]
                keypoints_normalized = [[float(norm[j][0]), float(norm[j][1])] for j in range(JOINT_N)]
                w, h = float(xywh[i][2]), float(xywh[i][3])
                persons.append({
                    "bbox": [x1, y1, x2, y2],
                    "bbox_wh": [w, h],
                    "confidence": float(confs[i]),
                    "keypoints": keypoints,
                    "keypoints_normalized": keypoints_normalized,
                })
        return persons
