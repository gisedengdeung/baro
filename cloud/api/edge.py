from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query

from cloud.dependencies import get_command_queue, get_db_service, get_status_store, get_zone_service
from cloud.models.status import EdgeHeartbeat
from cloud.services.command_queue import CommandQueueService
from cloud.services.db_service import DBService
from cloud.services.status_store import StatusStore
from cloud.services.zone_service import ZoneService

router = APIRouter()


@router.post("/heartbeat")
async def post_heartbeat(
    payload: Dict[str, Any],
    status_store: StatusStore = Depends(get_status_store),
    db_service: DBService = Depends(get_db_service),
):
    heartbeat = EdgeHeartbeat(**payload)
    status_store.update(heartbeat)

    await db_service.websocket_manager.broadcast(
        "logs",
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

    return {"status": "ok", "updated_at": datetime.utcnow().isoformat()}


@router.post("/log")
async def post_log(payload: Dict[str, Any], db_service: DBService = Depends(get_db_service)):
    message = await db_service.log_event(payload)
    return {"status": "ok", "event_type": message.event_type}


@router.get("/commands")
def get_commands(
    edge_id: str = Query("edge-default"),
    command_queue: CommandQueueService = Depends(get_command_queue),
) -> List[Dict[str, Any]]:
    return command_queue.pop_all(edge_id)


@router.get("/zones")
def get_zones(
    edge_id: str = Query("edge-default"),
    zone_service: ZoneService = Depends(get_zone_service),
):
    return zone_service.get_all_zones()
