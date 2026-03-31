from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import UploadFile
from loguru import logger


@dataclass(frozen=True)
class S3RuntimeConfig:
    bucket: str
    region: str
    presigned_url_ttl_sec: int
    aws_access_key: str | None
    aws_secret_key: str | None


@lru_cache(maxsize=1)
def _load_config() -> S3RuntimeConfig:
    bucket = os.getenv("AWS_S3_BUCKET", "").strip()
    if not bucket:
        # Legacy fallback for older deployments.
        bucket = os.getenv("S3_BUCKET_NAME", "").strip()
    if not bucket:
        raise RuntimeError("AWS_S3_BUCKET is required.")

    region = os.getenv("AWS_REGION", "ap-northeast-2").strip() or "ap-northeast-2"
    ttl = int(os.getenv("PRESIGNED_URL_TTL_SEC", "300"))

    aws_access_key = os.getenv("AWS_ACCESS_KEY", "").strip() or None
    aws_secret_key = os.getenv("AWS_SECRET_KEY", "").strip() or None

    return S3RuntimeConfig(
        bucket=bucket,
        region=region,
        presigned_url_ttl_sec=ttl,
        aws_access_key=aws_access_key,
        aws_secret_key=aws_secret_key,
    )


def _create_s3_client() -> tuple[Any, S3RuntimeConfig]:
    cfg = _load_config()
    kwargs: dict[str, str] = {"region_name": cfg.region}
    if cfg.aws_access_key and cfg.aws_secret_key:
        kwargs["aws_access_key_id"] = cfg.aws_access_key
        kwargs["aws_secret_access_key"] = cfg.aws_secret_key
    return boto3.client("s3", **kwargs), cfg


def upload_video_to_s3_from_memory(upload_file: UploadFile, s3_object_key: str) -> str:
    try:
        s3_client, cfg = _create_s3_client()
        logger.info(f"S3 업로드 시작: s3://{cfg.bucket}/{s3_object_key}")
        upload_file.file.seek(0)
        s3_client.upload_fileobj(
            upload_file.file,
            cfg.bucket,
            s3_object_key,
            ExtraArgs={"ContentType": "video/mp4"},
        )
        logger.info(f"S3 업로드 완료: s3://{cfg.bucket}/{s3_object_key}")
        return s3_object_key
    except (ClientError, BotoCoreError, RuntimeError, ValueError) as exc:
        logger.error(f"S3 업로드 실패: {exc}")
        return ""


def generate_presigned_download_url(s3_object_key: str, expires_in: int | None = None) -> str:
    try:
        s3_client, cfg = _create_s3_client()
        ttl = expires_in if expires_in is not None else cfg.presigned_url_ttl_sec
        return s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": cfg.bucket, "Key": s3_object_key},
            ExpiresIn=ttl,
        )
    except (ClientError, BotoCoreError, RuntimeError, ValueError) as exc:
        logger.error(f"Presigned URL 생성 실패: {exc}")
        return ""
