from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from cloud.dependencies import (
    get_clip_service,
    get_command_queue,
    get_db_service,
    get_status_store,
    require_edge_request_auth,
    get_zone_service,
)
from cloud.models.status import EdgeHeartbeat
from cloud.services.clip_service import ClipService
from cloud.services.command_queue import CommandQueueService
from cloud.services.db_service import DBService
from cloud.services.edge_auth import ensure_authenticated_edge_id
from cloud.services.status_store import StatusStore
from cloud.services.zone_service import ZoneService

router = APIRouter()
KST = ZoneInfo("Asia/Seoul")


@router.post("/heartbeat")
async def post_heartbeat(
    payload: Dict[str, Any],
    authenticated_edge_id: str = Depends(require_edge_request_auth),
    status_store: StatusStore = Depends(get_status_store),
    db_service: DBService = Depends(get_db_service),
):
    payload = dict(payload)
    payload["edge_id"] = ensure_authenticated_edge_id(
        authenticated_edge_id,
        payload.get("edge_id"),
    )
    heartbeat = EdgeHeartbeat(**payload)
    status_store.update(heartbeat)

    await db_service.websocket_manager.broadcast_to_edge(
        "logs",
        heartbeat.edge_id,
        {
            "type": "STATUS_UPDATE",
            "data": {
                "operation_mode": heartbeat.operation_mode,
                "conveyor_status": "RUNNING" if heartbeat.conveyor_is_on and heartbeat.conveyor_speed >= 100 else (
                    "SLOWDOWN" if heartbeat.conveyor_is_on else "STOPPED"
                ),
                "conveyor_speed": heartbeat.conveyor_speed,
                "risk_level": heartbeat.risk_level,
                "is_locked": heartbeat.is_locked,
                "test_is_active": heartbeat.test_is_active,
                "test_speed": heartbeat.test_speed,
            },
        },
    )

    return {"status": "ok", "updated_at": datetime.now(KST).isoformat()}


@router.post("/log")
async def post_log(
    payload: Dict[str, Any],
    authenticated_edge_id: str = Depends(require_edge_request_auth),
    db_service: DBService = Depends(get_db_service),
):
    payload = dict(payload)
    payload["edge_id"] = ensure_authenticated_edge_id(
        authenticated_edge_id,
        payload.get("edge_id"),
    )
    message = await db_service.log_event(payload)
    return {"status": "ok", "event_type": message.event_type}


@router.post("/clips")
async def post_clip(
    edge_id: str = Form("edge-default"),
    event_uid: str = Form(...),
    clip_started_at: str | None = Form(None),
    clip_ended_at: str | None = Form(None),
    duration_sec: float = Form(0.0),
    status: str | None = Form(None),
    error_message: str | None = Form(None),
    file: UploadFile | None = File(None),
    authenticated_edge_id: str = Depends(require_edge_request_auth),
    clip_service: ClipService = Depends(get_clip_service),
):
    edge_id = ensure_authenticated_edge_id(authenticated_edge_id, edge_id)
    normalized_status = (status or "").strip().upper()

    if normalized_status == "FAILED":
        updated = await clip_service.mark_clip_failed(
            edge_id=edge_id,
            event_uid=event_uid,
            error_message=error_message,
        )
        if not updated:
            raise HTTPException(status_code=404, detail=f"event_uid not found: {event_uid}")
        return {"status": "ok", "event_uid": event_uid, "clip_status": "FAILED"}

    if file is None:
        raise HTTPException(status_code=400, detail="Clip file is required unless status=FAILED.")

    if not clip_started_at or not clip_ended_at:
        raise HTTPException(status_code=400, detail="clip_started_at and clip_ended_at are required.")

    try:
        updated = await clip_service.save_uploaded_clip(
            edge_id=edge_id,
            event_uid=event_uid,
            clip_started_at=clip_started_at,
            clip_ended_at=clip_ended_at,
            duration_sec=duration_sec,
            upload=file,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        await clip_service.mark_clip_failed(
            edge_id=edge_id,
            event_uid=event_uid,
            error_message=str(exc),
        )
        raise HTTPException(status_code=500, detail="Clip upload processing failed.") from exc

    return {
        "status": "ok",
        "event_uid": event_uid,
        "clip_status": updated.get("clip_status"),
        "log_id": updated.get("id"),
    }


@router.get("/commands")
def get_commands(
    edge_id: str = Query("edge-default"),
    authenticated_edge_id: str = Depends(require_edge_request_auth),
    command_queue: CommandQueueService = Depends(get_command_queue),
) -> List[Dict[str, Any]]:
    edge_id = ensure_authenticated_edge_id(authenticated_edge_id, edge_id)
    return command_queue.pop_all(edge_id)


@router.get("/zones")
def get_zones(
    edge_id: str = Query("edge-default"),
    authenticated_edge_id: str = Depends(require_edge_request_auth),
    zone_service: ZoneService = Depends(get_zone_service),
):
    edge_id = ensure_authenticated_edge_id(authenticated_edge_id, edge_id)
    return zone_service.get_all_zones(edge_id)
