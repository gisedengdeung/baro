from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field


class ControlCommand(BaseModel):
    edge_id: str = Field(default="edge-default")
    command: str
    data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ControlResponse(BaseModel):
    status: str = "success"
    message: str
    edge_id: str = "edge-default"


class CommandListResponse(BaseModel):
    commands: list[ControlCommand]
