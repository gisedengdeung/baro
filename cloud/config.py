from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class CloudConfig:
    cors_allow_origins: list[str]
    local_db_path: str
    signaling_offer_ttl_sec: int
    signaling_answer_ttl_sec: int
    signaling_ice_ttl_sec: int



def load_config() -> CloudConfig:
    cors_raw = os.getenv("CLOUD_CORS_ALLOW_ORIGINS", "*")
    origins = [x.strip() for x in cors_raw.split(",") if x.strip()]
    return CloudConfig(
        cors_allow_origins=origins or ["*"],
        local_db_path=os.getenv("LOCAL_DB_PATH", "cloud/data/cloud.db"),
        signaling_offer_ttl_sec=int(os.getenv("SIGNALING_OFFER_TTL_SEC", "30")),
        signaling_answer_ttl_sec=int(os.getenv("SIGNALING_ANSWER_TTL_SEC", "30")),
        signaling_ice_ttl_sec=int(os.getenv("SIGNALING_ICE_TTL_SEC", "20")),
    )
