from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class CloudConfig:
    cors_allow_origins: list[str]
    local_db_path: str
    signaling_offer_ttl_sec: int
    signaling_answer_ttl_sec: int
    signaling_ice_ttl_sec: int
    edge_shared_secret: str
    edge_signature_ttl_sec: int
    auth_admin_email: str | None
    auth_admin_password: str | None
    auth_jwt_secret: str
    auth_access_ttl_sec: int
    auth_refresh_ttl_sec: int
    auth_cookie_secure: bool
    auth_cookie_samesite: str
    auth_cookie_domain: str | None
    clip_storage_dir: str
    clip_retention_days: int
    clip_cleanup_interval_sec: int
    clip_presigned_url_ttl_sec: int
    aws_s3_bucket: str | None
    aws_region: str
    kma_api_key: str | None
    kma_asos_station_no: str
    openai_api_key: str | None


def _parse_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _parse_env_value(value: str | None, default: str) -> str:
    if value is None:
        return default
    return value.split("#", 1)[0].strip() or default


def load_config() -> CloudConfig:
    cors_raw = os.getenv(
        "CLOUD_CORS_ALLOW_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    origins = [x.strip() for x in cors_raw.split(",") if x.strip()]

    cookie_samesite = os.getenv("AUTH_COOKIE_SAMESITE", "lax").strip().lower()
    if cookie_samesite not in {"lax", "strict", "none"}:
        cookie_samesite = "lax"

    auth_cookie_domain = os.getenv("AUTH_COOKIE_DOMAIN")
    if auth_cookie_domain:
        auth_cookie_domain = auth_cookie_domain.strip() or None

    aws_s3_bucket = os.getenv("AWS_S3_BUCKET")
    if aws_s3_bucket:
        aws_s3_bucket = aws_s3_bucket.strip() or None

    return CloudConfig(
        cors_allow_origins=origins or ["http://localhost:3000"],
        local_db_path=os.getenv("LOCAL_DB_PATH", "cloud/data/cloud.db"),
        signaling_offer_ttl_sec=int(os.getenv("SIGNALING_OFFER_TTL_SEC", "30")),
        signaling_answer_ttl_sec=int(os.getenv("SIGNALING_ANSWER_TTL_SEC", "30")),
        signaling_ice_ttl_sec=int(os.getenv("SIGNALING_ICE_TTL_SEC", "20")),
        edge_shared_secret=_require_env("EDGE_SHARED_SECRET"),
        edge_signature_ttl_sec=int(os.getenv("EDGE_SIGNATURE_TTL_SEC", "30")),
        auth_admin_email=os.getenv("AUTH_ADMIN_EMAIL"),
        auth_admin_password=os.getenv("AUTH_ADMIN_PASSWORD"),
        auth_jwt_secret=os.getenv("AUTH_JWT_SECRET", "dev-only-change-this-secret"),
        auth_access_ttl_sec=int(os.getenv("AUTH_ACCESS_TTL_SEC", "900")),
        auth_refresh_ttl_sec=int(os.getenv("AUTH_REFRESH_TTL_SEC", "604800")),
        auth_cookie_secure=_parse_bool(os.getenv("AUTH_COOKIE_SECURE", "false"), default=False),
        auth_cookie_samesite=cookie_samesite,
        auth_cookie_domain=auth_cookie_domain,
        clip_storage_dir=os.getenv("CLIP_STORAGE_DIR", "cloud/data/clips"),
        clip_retention_days=int(os.getenv("CLIP_RETENTION_DAYS", "7")),
        clip_cleanup_interval_sec=int(os.getenv("CLIP_CLEANUP_INTERVAL_SEC", "3600")),
        clip_presigned_url_ttl_sec=int(os.getenv("CLIP_PRESIGNED_URL_TTL_SEC", "300")),
        aws_s3_bucket=aws_s3_bucket,
        aws_region=os.getenv("AWS_REGION", "ap-northeast-2").strip() or "ap-northeast-2",
        kma_api_key=(os.getenv("KMA_API_KEY") or "").strip() or None,
        kma_asos_station_no=_parse_env_value(os.getenv("KMA_ASOS_STATION_NO"), "119"),  # 기본: 경기 수원
        openai_api_key=(os.getenv("OPENAI_API_KEY") or "").strip() or None,
    )
