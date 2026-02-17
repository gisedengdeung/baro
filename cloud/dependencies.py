from __future__ import annotations

from fastapi import HTTPException, Request, WebSocket

from cloud.services.command_queue import CommandQueueService
from cloud.services.db_service import DBService
from cloud.services.signaling_store import SignalingStore
from cloud.services.status_store import StatusStore
from cloud.services.websocket_manager import WebSocketManager
from cloud.services.zone_service import ZoneService



def _get_state_attr(obj: Request | WebSocket, name: str):
    value = getattr(obj.app.state, name, None)
    if value is None:
        raise HTTPException(status_code=500, detail=f"Service not initialized: {name}")
    return value



def get_db_service(request: Request) -> DBService:
    return _get_state_attr(request, "db_service")



def get_zone_service(request: Request) -> ZoneService:
    return _get_state_attr(request, "zone_service")



def get_command_queue(request: Request) -> CommandQueueService:
    return _get_state_attr(request, "command_queue")



def get_status_store(request: Request) -> StatusStore:
    return _get_state_attr(request, "status_store")



def get_signaling_store(request: Request) -> SignalingStore:
    return _get_state_attr(request, "signaling_store")



def get_websocket_manager(websocket: WebSocket) -> WebSocketManager:
    return _get_state_attr(websocket, "websocket_manager")
