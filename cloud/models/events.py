from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class LogMessage(BaseModel):
    edge_id: str = Field(default="edge-default")
    event_type: str
    details: Dict[str, Any] = Field(default_factory=dict)
    log_risk_level: str = Field(default="INFO")
    operation_mode: str = Field(default="STOPPED")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_uid: Optional[str] = Field(default=None)
    clip_status: str = Field(default="NONE")
    clip_path: Optional[str] = Field(default=None)
    clip_started_at: Optional[datetime] = Field(default=None)
    clip_ended_at: Optional[datetime] = Field(default=None)
    clip_duration_sec: Optional[float] = Field(default=None)
    clip_created_at: Optional[datetime] = Field(default=None)


class AlertMessage(BaseModel):
    edge_id: str = Field(default="edge-default")
    level: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
