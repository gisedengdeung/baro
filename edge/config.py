from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class EdgeConfig:
    edge_id: str
    cloud_base_url: str
    camera_source: int
    serial_port: str
    serial_baud_rate: int
    serial_mock_mode: bool

    command_poll_interval: float
    zone_poll_interval: float
    heartbeat_interval: float

    person_model_path: str
    fall_model_path: str
    person_conf_threshold: float
    fall_conf_threshold: float
    fire_ratio_threshold: float
    entrapment_frame_threshold: int
    incident_cooldown_sec: float
    visual_overlay_enabled: bool
    draw_zone_polygons: bool
    draw_label_confidence: bool


ROOT_DIR = Path(__file__).resolve().parent.parent
EDGE_MODELS_DIR = ROOT_DIR / "edge" / "models"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "y", "on"}


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
        camera_source=int(os.getenv("EDGE_CAMERA_SOURCE", "0")),
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
        fall_model_path=_resolve_model_path(
            os.getenv("EDGE_FALL_MODEL_PATH", ""),
            "edge/models/fall_det_1.pt",
        ),
        person_conf_threshold=float(os.getenv("EDGE_PERSON_CONF", "0.3")),
        fall_conf_threshold=float(os.getenv("EDGE_FALL_CONF", "0.4")),
        fire_ratio_threshold=float(os.getenv("EDGE_FIRE_RATIO_THRESHOLD", "0.02")),
        entrapment_frame_threshold=int(os.getenv("EDGE_ENTRAPMENT_FRAME_THRESHOLD", "8")),
        incident_cooldown_sec=float(os.getenv("EDGE_INCIDENT_COOLDOWN_SEC", "8.0")),
        visual_overlay_enabled=_env_bool("EDGE_VISUAL_OVERLAY_ENABLED", True),
        draw_zone_polygons=_env_bool("EDGE_DRAW_ZONE_POLYGONS", True),
        draw_label_confidence=_env_bool("EDGE_DRAW_LABEL_CONFIDENCE", False),
    )
