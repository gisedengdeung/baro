from __future__ import annotations

from contextlib import asynccontextmanager
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from cloud.api import auth, control, edge, edges, logs, safety, signaling, status, streaming, zones
from cloud.config import load_config
from cloud.dependencies import require_browser_auth
from cloud.db import init_db
from cloud.services.auth_service import AuthConfig, AuthService
from cloud.services.clip_service import ClipService
from cloud.services.command_queue import CommandQueueService
from cloud.services.db_service import DBService
from cloud.services.edge_auth import EdgeAuthService
from cloud.services.llm_service import LLMService
from cloud.services.location_service import LocationService
from cloud.services.safety_service import SafetyService
from cloud.services.signaling_store import SignalingStore
from cloud.services.status_store import StatusStore
from cloud.services.weather_service import WeatherService
from cloud.services.websocket_manager import WebSocketManager
from cloud.services.zone_service import ZoneService
from cloud.ws import alert_stream, log_stream

KST = ZoneInfo("Asia/Seoul")


async def _weather_loop(weather_service: WeatherService, interval_sec: int) -> None:
    """서버 시작 시 즉시 1회 실행, 이후 설정된 주기마다 반복"""
    await weather_service.refresh()
    while True:
        await asyncio.sleep(interval_sec)
        await weather_service.refresh()


async def _midnight_close_loop(
    safety_service: SafetyService,
    weather_service: WeatherService | None = None,
) -> None:
    """매일 자정 KST에 당일 점수 확정 + 무사고 스트릭 업데이트"""
    while True:
        now = datetime.now(KST)
        next_midnight = (
            datetime(now.year, now.month, now.day, tzinfo=KST) + timedelta(days=1)
        )
        await asyncio.sleep((next_midnight - now).total_seconds())
        safety_service.close_day()
        if weather_service:
            target_date = (datetime.now(KST).date() - timedelta(days=1)).isoformat()
            try:
                await weather_service.save_daily_asos_summary(target_date)
            except Exception as exc:
                logger.warning(f"일별 ASOS 기상 요약 저장 실패: {exc}")
        logger.info("자정 마감 완료")

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

    safety_service = SafetyService(db_path=cfg.local_db_path)
    app.state.safety_service = safety_service
    app.state.location_service = LocationService(kakao_rest_api_key=cfg.kakao_rest_api_key)

    weather_service: WeatherService | None = None
    if cfg.kma_api_key:
        weather_service = WeatherService(
            api_key=cfg.kma_api_key,
            station_no=cfg.kma_asos_station_no,
            safety_service=safety_service,
        )
    app.state.weather_service = weather_service

    llm_service: LLMService | None = None
    if cfg.openai_api_key:
        llm_service = LLMService(
            api_key=cfg.openai_api_key,
            db_path=cfg.local_db_path,
            safety_service=safety_service,
        )
    else:
        logger.warning("OPENAI_API_KEY 미설정 - AI 분석 기능 비활성화")
    app.state.llm_service = llm_service

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

    # 백그라운드 태스크
    bg_tasks = [asyncio.create_task(_midnight_close_loop(safety_service, weather_service))]
    if weather_service:
        bg_tasks.append(
            asyncio.create_task(
                _weather_loop(weather_service, cfg.weather_refresh_interval_sec)
            )
        )
    else:
        logger.warning("KMA_API_KEY 미설정 - 기상 감점 비활성화")

    yield

    for task in bg_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


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
app.include_router(
    safety.router,
    prefix="/api/safety",
    tags=["Safety"],
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
