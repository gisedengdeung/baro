from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from cloud.dependencies import get_current_user_ws, get_websocket_manager
from cloud.models.auth import UserPublic
from cloud.services.websocket_manager import WebSocketManager

router = APIRouter()


@router.websocket("")
@router.websocket("/")
async def alerts_ws(
    websocket: WebSocket,
    _user: UserPublic = Depends(get_current_user_ws),
    manager: WebSocketManager = Depends(get_websocket_manager),
) -> None:
    await manager.connect(websocket, "alerts")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, "alerts")
