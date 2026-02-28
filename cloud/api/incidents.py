from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse

from cloud.dependencies import get_current_user, get_incident_service
from cloud.models.auth import UserPublic
from cloud.models.incidents import (
    IncidentCreateRequest,
    IncidentCreateResponse,
    IncidentRecord,
    IncidentStatusUpdateRequest,
    SnapshotUploadResponse,
)
from cloud.services.incident_service import IncidentService

router = APIRouter()


@router.post("/edge/incidents", response_model=IncidentCreateResponse)
async def create_incident_from_edge(
    payload: IncidentCreateRequest,
    incident_service: IncidentService = Depends(get_incident_service),
) -> IncidentCreateResponse:
    incident = await incident_service.create_incident(payload.model_dump(mode="json"))
    return IncidentCreateResponse(status="ok", incident_id=incident["id"], incident=IncidentRecord(**incident))


@router.post("/edge/incidents/{incident_id}/snapshot", response_model=SnapshotUploadResponse)
async def upload_incident_snapshot(
    incident_id: str,
    request: Request,
    incident_service: IncidentService = Depends(get_incident_service),
) -> SnapshotUploadResponse:
    content_type = request.headers.get("content-type", "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Only image upload is allowed")

    content = await request.body()
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Empty image payload")

    ext = "jpg"
    if "/" in content_type:
        ext = content_type.split("/", 1)[1].split(";", 1)[0].strip() or "jpg"
    snapshot_url = await incident_service.set_snapshot(
        incident_id=incident_id,
        file_bytes=content,
        filename=f"{incident_id}.{ext}",
    )
    return SnapshotUploadResponse(status="ok", incident_id=incident_id, snapshot_url=snapshot_url)


@router.get("/incidents", response_model=List[IncidentRecord])
def list_incidents(
    _user: UserPublic = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=500),
    edge_id: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    incident_service: IncidentService = Depends(get_incident_service),
) -> List[IncidentRecord]:
    items = incident_service.list_incidents(limit=limit, edge_id=edge_id, status_filter=status_filter)
    return [IncidentRecord(**item) for item in items]


@router.get("/incidents/{incident_id}", response_model=IncidentRecord)
def get_incident(
    incident_id: str,
    _user: UserPublic = Depends(get_current_user),
    incident_service: IncidentService = Depends(get_incident_service),
) -> IncidentRecord:
    item = incident_service.get_incident(incident_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return IncidentRecord(**item)


@router.patch("/incidents/{incident_id}/status", response_model=IncidentRecord)
def update_incident_status(
    incident_id: str,
    payload: IncidentStatusUpdateRequest,
    _user: UserPublic = Depends(get_current_user),
    incident_service: IncidentService = Depends(get_incident_service),
) -> IncidentRecord:
    item = incident_service.update_status(incident_id, payload.status)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return IncidentRecord(**item)


@router.get("/incidents/{incident_id}/snapshot")
def get_incident_snapshot(
    incident_id: str,
    _user: UserPublic = Depends(get_current_user),
    incident_service: IncidentService = Depends(get_incident_service),
):
    path = incident_service.get_snapshot_path(incident_id)
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")
    return FileResponse(path)
