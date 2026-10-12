from __future__ import annotations

from dataclasses import dataclass
import re

import torch


_CUDA_DEVICE_PATTERN = re.compile(r"^cuda:(\d+)$")


@dataclass(frozen=True, slots=True)
class InferenceDeviceInfo:
    requested: str
    resolved: str
    cuda_available: bool
    gpu_name: str | None


def resolve_inference_device(requested: str | None) -> InferenceDeviceInfo:
    normalized = (requested or "auto").strip().lower() or "auto"
    cuda_available = bool(torch.cuda.is_available())

    if normalized == "auto":
        resolved = "cuda:0" if cuda_available else "cpu"
    elif normalized == "cpu":
        resolved = "cpu"
    elif normalized == "cuda":
        resolved = "cuda:0"
    elif _CUDA_DEVICE_PATTERN.fullmatch(normalized):
        resolved = normalized
    else:
        raise ValueError(
            "Invalid EDGE_INFERENCE_DEVICE. Use one of: auto, cpu, cuda, cuda:<index>."
        )

    gpu_name: str | None = None
    if resolved.startswith("cuda"):
        if not cuda_available:
            raise RuntimeError(
                f"EDGE_INFERENCE_DEVICE={normalized} requires CUDA, but torch.cuda.is_available() is false."
            )

        match = _CUDA_DEVICE_PATTERN.fullmatch(resolved)
        device_index = int(match.group(1)) if match else 0
        device_count = torch.cuda.device_count()
        if device_index >= device_count:
            raise RuntimeError(
                f"Requested CUDA device index {device_index} is out of range. "
                f"Available device count: {device_count}."
            )
        gpu_name = torch.cuda.get_device_name(device_index)

    return InferenceDeviceInfo(
        requested=normalized,
        resolved=resolved,
        cuda_available=cuda_available,
        gpu_name=gpu_name,
    )
