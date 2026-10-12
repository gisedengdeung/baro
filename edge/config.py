from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class EdgeConfig:
    edge_id: str
    cloud_base_url: str
    shared_secret: str
    camera_source: int
    camera_width: int
    camera_height: int
    serial_port: str
    serial_baud_rate: int
    serial_mock_mode: bool

    command_poll_interval: float
    zone_poll_interval: float
    heartbeat_interval: float

    person_model_path: str
    keypoint_model_path: str
    ddnet_model_path: str
    inference_device_request: str
    person_conf_threshold: float
    keypoint_conf_threshold: float
    ddnet_fall_prob_threshold: float
    visual_overlay_enabled: bool
    draw_zone_polygons: bool
    draw_label_confidence: bool
    clip_pre_seconds: int
    clip_post_seconds: int
    clip_target_fps: int
    clip_width: int
    clip_height: int
    clip_output_dir: str
    clip_min_trigger_level: str


ROOT_DIR = Path(__file__).resolve().parent.parent
EDGE_MODELS_DIR = ROOT_DIR / "edge" / "models"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "y", "on"}


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _resolve_model_path(raw_path: str, default_rel_path: str) -> str:
    # Relative model paths are interpreted from repository root.
    candidate = (raw_path or default_rel_path).strip()
    path = Path(candidate)

    if path.is_absolute():
        return str(path)

    if path.parent == Path("."):
        preferred = EDGE_MODELS_DIR / path.name
        legacy = ROOT_DIR / path.name
        if preferred.exists():
            return str(preferred)
        if legacy.exists():
            return str(legacy)
        return str(preferred)

    return str(ROOT_DIR / path)


def load_config() -> EdgeConfig:
    return EdgeConfig(
        edge_id=os.getenv("EDGE_ID", "edge-default"),
        cloud_base_url=os.getenv("CLOUD_BASE_URL", "http://localhost:8000"),
        shared_secret=_require_env("EDGE_SHARED_SECRET"),
        camera_source=int(os.getenv("EDGE_CAMERA_SOURCE", "0")),
        camera_width=int(os.getenv("EDGE_CAMERA_WIDTH", "1920")),
        camera_height=int(os.getenv("EDGE_CAMERA_HEIGHT", "1080")),
        serial_port=os.getenv("EDGE_SERIAL_PORT", "/dev/ttyUSB0"),
        serial_baud_rate=int(os.getenv("EDGE_SERIAL_BAUD", "9600")),
        serial_mock_mode=_env_bool("EDGE_SERIAL_MOCK", False),
        command_poll_interval=float(os.getenv("EDGE_COMMAND_POLL_INTERVAL", "0.3")),
        zone_poll_interval=float(os.getenv("EDGE_ZONE_POLL_INTERVAL", "5.0")),
        heartbeat_interval=float(os.getenv("EDGE_HEARTBEAT_INTERVAL", "1.0")),
        person_model_path=_resolve_model_path(
            os.getenv("EDGE_PERSON_MODEL_PATH", ""),
            "edge/models/yolov8n.pt",
        ),
        keypoint_model_path=_resolve_model_path(
            os.getenv("EDGE_KEYPOINT_MODEL_PATH", ""),
            "edge/models/yolov8n-pose.pt",
        ),
        ddnet_model_path=_resolve_model_path(
            os.getenv("EDGE_DDNET_MODEL_PATH", ""),
            "edge/models/ddnet_deploy_jetson.pt",
        ),
        inference_device_request=os.getenv("EDGE_INFERENCE_DEVICE", "auto").strip() or "auto",
        person_conf_threshold=float(os.getenv("EDGE_PERSON_CONF", "0.3")),
        keypoint_conf_threshold=float(os.getenv("EDGE_KEYPOINT_CONF", "0.3")),
        ddnet_fall_prob_threshold=float(os.getenv("EDGE_DDNET_FALL_PROB_THRESHOLD", "0.8")),
        visual_overlay_enabled=_env_bool("EDGE_VISUAL_OVERLAY_ENABLED", True),
        draw_zone_polygons=_env_bool("EDGE_DRAW_ZONE_POLYGONS", True),
        draw_label_confidence=_env_bool("EDGE_DRAW_LABEL_CONFIDENCE", False),
        clip_pre_seconds=int(os.getenv("EDGE_CLIP_PRE_SECONDS", "10")),
        clip_post_seconds=int(os.getenv("EDGE_CLIP_POST_SECONDS", "10")),
        clip_target_fps=int(os.getenv("EDGE_CLIP_TARGET_FPS", "10")),
        clip_width=int(os.getenv("EDGE_CLIP_WIDTH", "1280")),
        clip_height=int(os.getenv("EDGE_CLIP_HEIGHT", "720")),
        clip_output_dir=os.getenv("EDGE_CLIP_OUTPUT_DIR", "edge/data/clips"),
        clip_min_trigger_level=os.getenv("EDGE_CLIP_MIN_TRIGGER_LEVEL", "WARNING"),
    )
