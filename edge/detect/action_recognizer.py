from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Optional

import numpy as np
import torch
from loguru import logger
from scipy.spatial.distance import cdist

from edge.detect.DDNet_Original import DDNet_Original
from edge.detect.inference_device import resolve_inference_device

# 모델 하이퍼파라미터 (el_action_recognition.pt 학습 기준)
FRAME_L = 40    # 입력 프레임 시퀀스 길이
JOINT_N = 17    # 관절 수 (YOLOv8 pose 기준)
JOINT_D = 2     # 관절 좌표 차원 (x, y)
FEAT_D = 136    # JCD 특징 차원 (17*16/2 상삼각 거리)
FILTERS = 64
CLASS_NUM = 12

# 사고유형 클래스 라벨 (natsort 폴더명 순서 기준)
# N = 사고 미발생, P = 사고 발생
ACTION_LABELS: Dict[int, str] = {
    0: "케이블협착-정상",
    1: "케이블협착-사고",
    2: "감전-정상",
    3: "감전-사고",
    4: "추락-정상",
    5: "추락-사고",
    6: "고소차량협착-정상",
    7: "고소차량협착-사고",
    8: "낙하-정상",
    9: "낙하-사고",
    10: "미확인-정상",
    11: "미확인-사고",
}

# 사고 발생(P) 클래스 인덱스
ACCIDENT_INDICES = {1, 3, 5, 7, 9, 11}


def _compute_jcd(p: np.ndarray) -> np.ndarray:
    """관절 좌표 시퀀스에서 JCD(Joint Coordinate Distance) 행렬 계산.

    Args:
        p: shape (FRAME_L, JOINT_N, JOINT_D)
    Returns:
        M: shape (FRAME_L, FEAT_D) — 정규화된 관절 간 거리 행렬
    """
    iu = np.triu_indices(JOINT_N, 1, JOINT_N)
    M = []
    for f in range(FRAME_L):
        d_m = cdist(p[f], p[f], "euclidean")
        M.append(d_m[iu])
    M = np.stack(M)
    mean = np.mean(M)
    return (M - mean) / (mean + 1e-6)


class ActionRecognizer:
    def __init__(
        self,
        model_path: str = "edge/models/el_action_recognition.pt",
        conf_threshold: float = 0.5,
        inference_device_request: str = "auto",
    ) -> None:
        self.inference_device = resolve_inference_device(inference_device_request)
        self.conf_threshold = conf_threshold

        self._model = DDNet_Original(
            frame_l=FRAME_L,
            joint_n=JOINT_N,
            joint_d=JOINT_D,
            feat_d=FEAT_D,
            filters=FILTERS,
            class_num=CLASS_NUM,
        )
        state_dict = torch.load(model_path, map_location="cpu")
        self._model.load_state_dict(state_dict)
        self._model.to(self.inference_device.resolved)
        self._model.eval()

        # 슬라이딩 윈도우 버퍼: 매 프레임 keypoint를 추가하고 40프레임마다 추론
        self._buffer: deque = deque(maxlen=FRAME_L)
        self._last_result: Optional[Dict[str, Any]] = None

        logger.info(
            f"ActionRecognizer 초기화 완료: model={model_path}, "
            f"device={self.inference_device.resolved}"
        )

    def update(self, persons: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """매 프레임 호출. keypoint를 버퍼에 추가하고 버퍼가 가득 차면 추론.

        Args:
            persons: KeypointDetector.detect() 반환값
        Returns:
            추론 결과 dict 또는 버퍼가 아직 안 찼으면 직전 결과
        """
        if persons:
            # 신뢰도 가장 높은 사람의 keypoint 사용
            best = max(persons, key=lambda p: p["confidence"])
            kpts = best.get("keypoints", [])
            # 관절 수가 부족하면 0으로 패딩
            while len(kpts) < JOINT_N:
                kpts.append([0.0, 0.0])
            self._buffer.append(kpts[:JOINT_N])
        else:
            # 사람이 없는 프레임은 빈 keypoint로 채움
            self._buffer.append([[0.0, 0.0]] * JOINT_N)

        if len(self._buffer) < FRAME_L:
            return self._last_result

        self._last_result = self._infer()
        return self._last_result

    def _infer(self) -> Dict[str, Any]:
        """버퍼의 40프레임 keypoint 시퀀스로 행동 분류 추론."""
        try:
            p = np.array(list(self._buffer), dtype=np.float32)  # (40, 17, 2)

            M = _compute_jcd(p)                                  # (40, 136)
            device = next(self._model.parameters()).device
            M_tensor = torch.from_numpy(M).float().unsqueeze(0).to(device)  # (1, 40, 136)
            P_tensor = torch.from_numpy(p).float().unsqueeze(0).to(device)  # (1, 40, 17, 2)

            with torch.no_grad():
                output = self._model(M_tensor, P_tensor)         # (1, 12)
                probs = torch.softmax(output, dim=1)
                pred_idx = int(output.argmax(dim=1).item())
                confidence = float(probs[0][pred_idx].item())

            is_accident = pred_idx in ACCIDENT_INDICES and confidence >= self.conf_threshold
            return {
                "class_idx": pred_idx,
                "class_name": ACTION_LABELS.get(pred_idx, f"unknown-{pred_idx}"),
                "confidence": confidence,
                "is_accident": is_accident,
            }
        except Exception as exc:
            logger.error(f"행동 인식 추론 실패: {exc}")
            return {
                "class_idx": -1,
                "class_name": "error",
                "confidence": 0.0,
                "is_accident": False,
            }
