from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EdgeHeartbeat(BaseModel):
    edge_id: str = Field(default="edge-default")
    system_is_active: bool = False
    operation_mode: str = "STOPPED"
    is_locked: bool = False
    conveyor_is_on: bool = False
    conveyor_speed: int = 0
    is_alert_on: bool = False
    risk_level: str = "SAFE"
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SystemStatus(BaseModel):
    api_server_status: str = "RUNNING"
    edge_status: EdgeHeartbeat | None = None
