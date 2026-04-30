from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
from loguru import logger
from ultralytics import YOLO

from edge.detect.inference_device import resolve_inference_device

JOINT_N = 17  # YOLOv8 pose 기준 관절 수


class KeypointDetector:
    def __init__(
        self,
        model_path: str = "edge/models/el_keypoints.pt",
        conf_threshold: float = 0.3,
        inference_device_request: str = "auto",
    ) -> None:
        self.inference_device = resolve_inference_device(inference_device_request)
        self.model = YOLO(model_path)
        self._patch_head()
        self.model.to(self.inference_device.resolved)
        self.conf_threshold = conf_threshold
        logger.info(
            f"KeypointDetector 초기화 완료: model={model_path}, "
            f"device={self.inference_device.resolved}"
        )

    def _patch_head(self) -> None:
        from ultralytics.nn.modules.head import Detect
        for module in self.model.model.modules():
            if hasattr(module, "detect") and callable(getattr(module, "detect", None)):
                module.detect = Detect.forward
                logger.info("KeypointDetector: Pose head.detect 패치 완료")

    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """프레임에서 사람을 감지하고 17개 관절 좌표를 반환.

        반환 형식:
            [{ bbox, confidence, keypoints: [[x, y], ...] (17개) }, ...]
        """
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
            kpts_data = results[0].keypoints.data.cpu().numpy()  # (N, 17, 3)
            xyxy = boxes.xyxy.cpu().numpy()    # (N, 4)
            confs = boxes.conf.cpu().numpy()   # (N,)
            for i in range(len(xyxy)):
                x1, y1, x2, y2 = map(int, xyxy[i])
                raw = kpts_data[i] if i < len(kpts_data) else np.zeros((JOINT_N, 3))
                keypoints = [[float(raw[j][0]), float(raw[j][1])] for j in range(JOINT_N)]
                persons.append({
                    "bbox": [x1, y1, x2, y2],
                    "confidence": float(confs[i]),
                    "keypoints": keypoints,
                })
        return persons
