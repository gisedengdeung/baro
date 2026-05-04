from __future__ import annotations

from fastapi import HTTPException, Request, WebSocket, WebSocketException, status

from cloud.models.auth import UserPublic
from cloud.services.auth_service import ACCESS_COOKIE_NAME, AuthService
from cloud.services.clip_service import ClipService
from cloud.services.command_queue import CommandQueueService
from cloud.services.db_service import DBService
from cloud.services.edge_auth import EdgeAuthService
from cloud.services.safety_service import SafetyService
from cloud.services.signaling_store import SignalingStore
from cloud.services.status_store import StatusStore
from cloud.services.weather_service import WeatherService
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


def get_auth_service(request: Request) -> AuthService:
    return _get_state_attr(request, "auth_service")


def get_clip_service(request: Request) -> ClipService:
    return _get_state_attr(request, "clip_service")


def get_safety_service(request: Request) -> SafetyService:
    return _get_state_attr(request, "safety_service")


def get_weather_service(request: Request) -> WeatherService:
    svc = getattr(request.app.state, "weather_service", None)
    if svc is None:
        raise HTTPException(
            status_code=503,
            detail="날씨 서비스 비활성화 (KMA_API_KEY 미설정)",
        )
    return svc


def get_edge_auth_service(request: Request) -> EdgeAuthService:
    return _get_state_attr(request, "edge_auth_service")


def get_auth_service_ws(websocket: WebSocket) -> AuthService:
    return _get_state_attr(websocket, "auth_service")


def get_current_user(request: Request) -> UserPublic:
    auth_service = get_auth_service(request)
    return auth_service.get_current_user_from_request(request)


def require_browser_auth(request: Request) -> UserPublic:
    return get_current_user(request)


def get_current_user_ws(websocket: WebSocket) -> UserPublic:
    auth_service = get_auth_service_ws(websocket)
    token = websocket.cookies.get(ACCESS_COOKIE_NAME)
    if not token:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Not authenticated",
        )

    try:
        return auth_service.get_user_from_access_token(token)
    except HTTPException as exc:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=exc.detail if isinstance(exc.detail, str) else "Unauthorized",
        ) from exc


def require_signaling_browser_auth(
    request: Request,
    sender: str | None,
    receiver: str | None,
) -> UserPublic | None:
    if sender == "browser" or receiver == "browser":
        return get_current_user(request)
    return None


def require_edge_request_auth(request: Request) -> str:
    auth_service = get_edge_auth_service(request)
    return auth_service.authenticate(request)
