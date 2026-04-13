from __future__ import annotations

from contextlib import asynccontextmanager
import asyncio

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cloud.api import auth, control, edge, edges, logs, signaling, status, streaming, zones
from cloud.config import load_config
from cloud.dependencies import require_browser_auth
from cloud.db import init_db
from cloud.services.auth_service import AuthConfig, AuthService
from cloud.services.clip_service import ClipService
from cloud.services.command_queue import CommandQueueService
from cloud.services.db_service import DBService
from cloud.services.edge_auth import EdgeAuthService
from cloud.services.signaling_store import SignalingStore
from cloud.services.status_store import StatusStore
from cloud.services.websocket_manager import WebSocketManager
from cloud.services.zone_service import ZoneService
from cloud.ws import alert_stream, log_stream

cfg = load_config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(cfg.local_db_path)

    websocket_manager = WebSocketManager()
    auth_service = AuthService(
        db_path=cfg.local_db_path,
        config=AuthConfig(
            jwt_secret=cfg.auth_jwt_secret,
            access_ttl_sec=cfg.auth_access_ttl_sec,
            refresh_ttl_sec=cfg.auth_refresh_ttl_sec,
            cookie_secure=cfg.auth_cookie_secure,
            cookie_samesite=cfg.auth_cookie_samesite,
            cookie_domain=cfg.auth_cookie_domain,
        ),
    )
    auth_service.bootstrap_admin(cfg.auth_admin_email, cfg.auth_admin_password)

    app.state.websocket_manager = websocket_manager
    app.state.command_queue = CommandQueueService()
    app.state.signaling_store = SignalingStore(
        offer_ttl_sec=cfg.signaling_offer_ttl_sec,
        answer_ttl_sec=cfg.signaling_answer_ttl_sec,
        ice_ttl_sec=cfg.signaling_ice_ttl_sec,
    )
    app.state.edge_auth_service = EdgeAuthService(
        shared_secret=cfg.edge_shared_secret,
        max_age_sec=cfg.edge_signature_ttl_sec,
    )
    app.state.status_store = StatusStore()
    app.state.zone_service = ZoneService(db_path=cfg.local_db_path)
    app.state.db_service = DBService(
        websocket_manager=websocket_manager,
        db_path=cfg.local_db_path,
    )
    app.state.clip_service = ClipService(
        db_service=app.state.db_service,
        s3_bucket=cfg.aws_s3_bucket,
        aws_region=cfg.aws_region,
        presigned_url_ttl_sec=cfg.clip_presigned_url_ttl_sec,
    )
    app.state.auth_service = auth_service

    yield


app = FastAPI(
    title="Smart Safety Cloud API",
    version="3.1.0",
    description="Edge/Cloud 분리 아키텍처 Cloud 서버 (SQLite)",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(
    control.router,
    prefix="/api/control",
    tags=["Control"],
    dependencies=[Depends(require_browser_auth)],
)
app.include_router(
    logs.router,
    prefix="/api/logs",
    tags=["Logs"],
    dependencies=[Depends(require_browser_auth)],
)
app.include_router(
    zones.router,
    prefix="/api/zones",
    tags=["Zones"],
    dependencies=[Depends(require_browser_auth)],
)
app.include_router(
    status.router,
    prefix="/api/status",
    tags=["Status"],
    dependencies=[Depends(require_browser_auth)],
)
app.include_router(
    edges.router,
    prefix="/api/edges",
    tags=["Edges"],
    dependencies=[Depends(require_browser_auth)],
)
app.include_router(signaling.router, prefix="/api/signaling", tags=["Signaling"])
app.include_router(edge.router, prefix="/api/edge", tags=["Edge"])
app.include_router(streaming.router, prefix="/api/streaming", tags=["Streaming"])
app.include_router(log_stream.router, prefix="/ws/logs", tags=["WebSocket"])
app.include_router(alert_stream.router, prefix="/ws/alerts", tags=["WebSocket"])


@app.get("/")
def root():
    return {"status": "Smart Safety Cloud API is running"}