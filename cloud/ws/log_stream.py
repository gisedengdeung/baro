from __future__ import annotations

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from cloud.dependencies import get_current_user_ws, get_websocket_manager
from cloud.models.auth import UserPublic
from cloud.services.websocket_manager import WebSocketManager

router = APIRouter()


@router.websocket("")
@router.websocket("/")
async def logs_ws(
    websocket: WebSocket,
    edge_id: str | None = Query(None),
    _user: UserPublic = Depends(get_current_user_ws),
    manager: WebSocketManager = Depends(get_websocket_manager),
) -> None:
    channel = f"logs:{edge_id}" if edge_id else "logs"
    await manager.connect(websocket, channel)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
