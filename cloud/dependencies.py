from __future__ import annotations

import time
import json

from fastapi import HTTPException, Request, WebSocket, WebSocketException, status

from cloud.models.auth import UserPublic
from cloud.services.auth_service import ACCESS_COOKIE_NAME, AuthService
from cloud.services.clip_service import ClipService
from cloud.services.command_queue import CommandQueueService
from cloud.services.db_service import DBService
from cloud.services.signaling_store import SignalingStore
from cloud.services.status_store import StatusStore
from cloud.services.websocket_manager import WebSocketManager
from cloud.services.zone_service import ZoneService
from shared.edge_hmac import verify_edge_signature


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


def _load_edge_auth_state(request: Request) -> tuple[str, int]:
    shared_secret = getattr(request.app.state, "edge_shared_secret", None)
    skew_sec = getattr(request.app.state, "edge_auth_skew_sec", 30)
    if not shared_secret:
        raise HTTPException(status_code=500, detail="Edge auth secret not initialized")
    return str(shared_secret), int(skew_sec)


async def require_edge_hmac(request: Request) -> str:
    shared_secret, skew_sec = _load_edge_auth_state(request)

    edge_id = request.headers.get("X-Edge-Id", "").strip()
    timestamp = request.headers.get("X-Edge-Timestamp", "").strip()
    signature = request.headers.get("X-Edge-Signature", "").strip()
    if not edge_id or not timestamp or not signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing edge auth headers")

    try:
        timestamp_i = int(timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid edge timestamp") from exc

    now = int(time.time())
    if abs(now - timestamp_i) > skew_sec:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Edge signature timestamp expired")

    body = await request.body()
    is_valid = verify_edge_signature(
        provided_signature=signature,
        shared_secret=shared_secret,
        edge_id=edge_id,
        timestamp=timestamp,
        method=request.method,
        path=request.url.path,
        query=request.url.query,
        body=body,
    )
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid edge signature")

    edge_id_from_query = request.query_params.get("edge_id")
    if edge_id_from_query and edge_id_from_query != edge_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="edge_id mismatch")

    content_type = request.headers.get("content-type", "").lower()
    edge_id_from_body: str | None = None
    if "application/json" in content_type and body:
        try:
            parsed = json.loads(body.decode("utf-8"))
            if isinstance(parsed, dict):
                raw = parsed.get("edge_id")
                if isinstance(raw, str):
                    edge_id_from_body = raw
        except Exception:
            edge_id_from_body = None
    elif "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        try:
            form = await request.form()
            raw = form.get("edge_id")
            if isinstance(raw, str):
                edge_id_from_body = raw
        except Exception:
            edge_id_from_body = None

    if edge_id_from_body and edge_id_from_body != edge_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="edge_id mismatch")

    request.state.edge_id = edge_id
    return edge_id
