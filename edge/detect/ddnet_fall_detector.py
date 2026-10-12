from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Optional

import numpy as np
import torch
from loguru import logger

FRAME_L = 20
JOINT_N = 17
FALL_CLASS = 1
FALL_PROB_THRESHOLD = 0.8   # DDNet 낙상 확률 임계값
BBOX_RATIO_THRESHOLD = 1.2  # 가로/세로 비율 (w/h) 임계값


class DDNetFallDetector:
    def __init__(
        self,
        model_path: str = "edge/models/ddnet_deploy_jetson.pt",
        fall_prob_threshold: float = FALL_PROB_THRESHOLD,
        inference_device_request: str = "auto",
    ) -> None:
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if inference_device_request == "cpu":
            self._device = torch.device("cpu")

        with open(model_path, "rb") as f:
            self._model = torch.jit.load(f, map_location=self._device)
        self._model.eval()

        self.fall_prob_threshold = fall_prob_threshold
        self._buffer: deque = deque(maxlen=FRAME_L)
        self._last_result: Optional[Dict[str, Any]] = None

        logger.info(
            f"DDNetFallDetector 초기화 완료: model={model_path}, device={self._device}"
        )

    def update(self, persons: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """매 프레임 호출. 정규화 keypoints를 버퍼에 추가하고 20프레임이 차면 추론."""
        if persons:
            best = max(persons, key=lambda p: p.get("confidence", 0.0))
            kpts_norm = best.get("keypoints_normalized", [])

            # demo.py 방식: 결측치(0,0)는 이전 프레임 값으로 보정
            current = np.full((JOINT_N, 2), np.nan)
            for j, kp in enumerate(kpts_norm[:JOINT_N]):
                x, y = float(kp[0]), float(kp[1])
                if x > 0 or y > 0:
                    current[j] = [x, y]

            if len(self._buffer) > 0:
                prev = self._buffer[-1]
                mask = np.isnan(current)
                current[mask] = prev[mask]

            current[np.isnan(current)] = 0.0
            self._buffer.append(current)

            self._last_person = best
        else:
            self._buffer.append(np.zeros((JOINT_N, 2)))
            self._last_person = None

        if len(self._buffer) < FRAME_L:
            return self._last_result

        self._last_result = self._infer()
        return self._last_result

    def _infer(self) -> Dict[str, Any]:
        try:
            seq = np.array(list(self._buffer), dtype=np.float32)  # (20, 17, 2)
            tensor = torch.FloatTensor(seq).unsqueeze(0).to(self._device)  # (1, 20, 17, 2)

            with torch.no_grad():
                outputs = self._model(tensor)
                probs = torch.nn.functional.softmax(outputs, dim=1)[0]
                prob_normal = float(probs[0].item())
                prob_fall = float(probs[1].item())

            # 1차 판정: DDNet 확률
            raw_fall = prob_fall >= self.fall_prob_threshold

            # 2차 검증: bbox 가로/세로 비율 (demo.py 동일 로직)
            is_falling = False
            if raw_fall and self._last_person is not None:
                w, h = self._last_person.get("bbox_wh", [0, 1])
                h = h if h > 0 else 1
                if w / h >= BBOX_RATIO_THRESHOLD:
                    is_falling = True

            logger.info(
                f"[DDNetFall] prob_fall={prob_fall:.3f} raw_fall={raw_fall} "
                f"is_falling={is_falling}"
            )
            return {
                "is_falling": is_falling,
                "prob_fall": prob_fall,
                "prob_normal": prob_normal,
            }
        except Exception as exc:
            logger.error(f"DDNet 추론 실패: {exc}")
            return {"is_falling": False, "prob_fall": 0.0, "prob_normal": 1.0}
