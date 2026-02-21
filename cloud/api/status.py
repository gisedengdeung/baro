from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from cloud.dependencies import get_status_store
from cloud.models.status import SystemStatus
from cloud.services.status_store import StatusStore

router = APIRouter()


@router.get("", response_model=SystemStatus)
def get_status(
    edge_id: str = Query("edge-default"),
    status_store: StatusStore = Depends(get_status_store),
) -> SystemStatus:
    edge_status = status_store.get(edge_id)
    if edge_status is None:
        edge_status = status_store.get_any()
    return SystemStatus(api_server_status="RUNNING", edge_status=edge_status)
