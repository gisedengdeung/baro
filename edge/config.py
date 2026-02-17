from __future__ import annotations

import os
from dataclasses import dataclass


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
    visual_overlay_enabled: bool
    draw_zone_polygons: bool
    draw_label_confidence: bool



def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "y", "on"}



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
        person_model_path=os.getenv("EDGE_PERSON_MODEL_PATH", "yolov8n.pt"),
        fall_model_path=os.getenv("EDGE_FALL_MODEL_PATH", "fall_det_1.pt"),
        person_conf_threshold=float(os.getenv("EDGE_PERSON_CONF", "0.3")),
        fall_conf_threshold=float(os.getenv("EDGE_FALL_CONF", "0.4")),
        visual_overlay_enabled=_env_bool("EDGE_VISUAL_OVERLAY_ENABLED", True),
        draw_zone_polygons=_env_bool("EDGE_DRAW_ZONE_POLYGONS", True),
        draw_label_confidence=_env_bool("EDGE_DRAW_LABEL_CONFIDENCE", False),
    )
