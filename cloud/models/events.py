from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field


class LogMessage(BaseModel):
    edge_id: str = Field(default="edge-default")
    event_type: str
    details: Dict[str, Any] = Field(default_factory=dict)
    log_risk_level: str = Field(default="INFO")
    operation_mode: str = Field(default="STOPPED")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AlertMessage(BaseModel):
    edge_id: str = Field(default="edge-default")
    level: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
