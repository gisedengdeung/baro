from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

IncidentSeverity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
IncidentStatus = Literal["OPEN", "ACKNOWLEDGED", "RESOLVED"]


class IncidentCreateRequest(BaseModel):
    edge_id: str = Field(default="edge-default")
    incident_type: str
    severity: IncidentSeverity = "HIGH"
    zone_id: Optional[str] = None
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(default_factory=dict)


class IncidentStatusUpdateRequest(BaseModel):
    status: IncidentStatus


class IncidentRecord(BaseModel):
    id: str
    edge_id: str
    incident_type: str
    severity: IncidentSeverity
    zone_id: Optional[str] = None
    status: IncidentStatus
    details: Dict[str, Any] = Field(default_factory=dict)
    snapshot_url: Optional[str] = None
    detected_at: datetime
    created_at: datetime
    updated_at: datetime


class IncidentCreateResponse(BaseModel):
    status: str = "ok"
    incident_id: str
    incident: IncidentRecord


class SnapshotUploadResponse(BaseModel):
    status: str = "ok"
    incident_id: str
    snapshot_url: str
