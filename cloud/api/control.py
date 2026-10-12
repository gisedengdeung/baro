from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from cloud.dependencies import get_command_queue, get_status_store, get_zone_service
from cloud.models.control import ControlResponse
from cloud.services.command_queue import CommandQueueService
from cloud.services.status_store import StatusStore
from cloud.services.zone_service import ZoneService

router = APIRouter()


def _get_edge_status_or_409(status_store: StatusStore, edge_id: str):
    edge_status = status_store.get(edge_id)
    if edge_status is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Edge status unavailable for edge_id={edge_id}",
        )
    return edge_status


@router.post("/start_automatic", response_model=ControlResponse)
def start_automatic_mode(
    edge_id: str = Query("edge-default"),
    confirmed: bool = Query(False),
    command_queue: CommandQueueService = Depends(get_command_queue),
    zone_service: ZoneService = Depends(get_zone_service),
) -> ControlResponse:
    zones = zone_service.get_all_zones(edge_id)
    command_queue.push(edge_id, {"command": "UPDATE_ZONES", "data": zones})
    command_queue.push(edge_id, {"command": "START_AUTOMATIC"})
    return ControlResponse(message=f"START_AUTOMATIC queued ({len(zones)} zones synced)", edge_id=edge_id)


@router.post("/start_maintenance", response_model=ControlResponse)
def start_maintenance_mode(
    edge_id: str = Query("edge-default"),
    command_queue: CommandQueueService = Depends(get_command_queue),
) -> ControlResponse:
    command_queue.push(edge_id, {"command": "START_MAINTENANCE"})
    return ControlResponse(message="START_MAINTENANCE queued", edge_id=edge_id)


@router.post("/stop", response_model=ControlResponse)
def stop_system(
    edge_id: str = Query("edge-default"),
    command_queue: CommandQueueService = Depends(get_command_queue),
) -> ControlResponse:
    command_queue.push(edge_id, {"command": "STOP"})
    return ControlResponse(message="STOP queued", edge_id=edge_id)


@router.post("/reset", response_model=ControlResponse)
def reset_system(
    edge_id: str = Query("edge-default"),
    command_queue: CommandQueueService = Depends(get_command_queue),
) -> ControlResponse:
    command_queue.push(edge_id, {"command": "RESET"})
    return ControlResponse(message="RESET queued", edge_id=edge_id)


@router.post("/test/start", response_model=ControlResponse)
def start_test_run(
    edge_id: str = Query("edge-default"),
    speed_percent: int = Query(30, ge=0, le=100),
    command_queue: CommandQueueService = Depends(get_command_queue),
    status_store: StatusStore = Depends(get_status_store),
) -> ControlResponse:
    edge_status = _get_edge_status_or_409(status_store, edge_id)
    if edge_status.operation_mode != "STOPPED" or edge_status.is_locked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Test run can start only when operation_mode is STOPPED and system is unlocked",
        )

    command_queue.push(edge_id, {"command": "START_TEST_RUN", "data": {"speed_percent": speed_percent}})
    return ControlResponse(message=f"START_TEST_RUN queued (speed={speed_percent}%)", edge_id=edge_id)


@router.post("/test/speed", response_model=ControlResponse)
def set_test_speed(
    edge_id: str = Query("edge-default"),
    speed_percent: int = Query(..., ge=0, le=100),
    command_queue: CommandQueueService = Depends(get_command_queue),
    status_store: StatusStore = Depends(get_status_store),
) -> ControlResponse:
    edge_status = _get_edge_status_or_409(status_store, edge_id)
    if edge_status.operation_mode != "TEST":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Test speed can be set only when operation_mode is TEST",
        )

    command_queue.push(edge_id, {"command": "SET_TEST_SPEED", "data": {"speed_percent": speed_percent}})
    return ControlResponse(message=f"SET_TEST_SPEED queued (speed={speed_percent}%)", edge_id=edge_id)


@router.post("/test/stop", response_model=ControlResponse)
def stop_test_run(
    edge_id: str = Query("edge-default"),
    command_queue: CommandQueueService = Depends(get_command_queue),
) -> ControlResponse:
    command_queue.push(edge_id, {"command": "STOP_TEST_RUN"})
    return ControlResponse(message="STOP_TEST_RUN queued", edge_id=edge_id)


@router.get("/status")
def get_status_alias(
    edge_id: str = Query("edge-default"),
    status_store: StatusStore = Depends(get_status_store),
):
    edge_status = status_store.get(edge_id)
    if edge_status is None:
        return {"api_server_status": "RUNNING", "edge_status": None}
    return {"api_server_status": "RUNNING", "edge_status": edge_status.model_dump(mode="json")}
