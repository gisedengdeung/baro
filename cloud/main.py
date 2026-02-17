from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cloud.api import control, edge, logs, signaling, status, streaming, zones
from cloud.config import load_config
from cloud.db import init_db
from cloud.services.command_queue import CommandQueueService
from cloud.services.db_service import DBService
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
    app.state.websocket_manager = websocket_manager
    app.state.command_queue = CommandQueueService()
    app.state.signaling_store = SignalingStore(
        offer_ttl_sec=cfg.signaling_offer_ttl_sec,
        answer_ttl_sec=cfg.signaling_answer_ttl_sec,
        ice_ttl_sec=cfg.signaling_ice_ttl_sec,
    )
    app.state.status_store = StatusStore()
    app.state.zone_service = ZoneService(db_path=cfg.local_db_path)
    app.state.db_service = DBService(
        websocket_manager=websocket_manager,
        db_path=cfg.local_db_path,
    )
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

app.include_router(control.router, prefix="/api/control", tags=["Control"])
app.include_router(logs.router, prefix="/api/logs", tags=["Logs"])
app.include_router(zones.router, prefix="/api/zones", tags=["Zones"])
app.include_router(status.router, prefix="/api/status", tags=["Status"])
app.include_router(signaling.router, prefix="/api/signaling", tags=["Signaling"])
app.include_router(edge.router, prefix="/api/edge", tags=["Edge"])
app.include_router(streaming.router, prefix="/api/streaming", tags=["Streaming"])
app.include_router(log_stream.router, prefix="/ws/logs", tags=["WebSocket"])
app.include_router(alert_stream.router, prefix="/ws/alerts", tags=["WebSocket"])


@app.get("/")
def root():
    return {"status": "Smart Safety Cloud API is running"}
