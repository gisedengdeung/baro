from __future__ import annotations

from functools import lru_cache
from urllib.parse import urlparse

import boto3
from botocore.client import BaseClient
from fastapi import UploadFile
from loguru import logger


def build_s3_uri(bucket: str, key: str) -> str:
    return f"s3://{bucket}/{key.lstrip('/')}"


def parse_s3_uri(value: str) -> tuple[str, str] | None:
    if not value.startswith("s3://"):
        return None
    parsed = urlparse(value)
    bucket = parsed.netloc.strip()
    key = parsed.path.lstrip("/")
    if not bucket or not key:
        return None
    return bucket, key


@lru_cache(maxsize=4)
def get_s3_client(region_name: str) -> BaseClient:
    return boto3.client("s3", region_name=region_name)


def upload_video_to_s3_from_memory(
    upload_file: UploadFile,
    *,
    bucket_name: str,
    region_name: str,
    s3_file_name: str,
) -> str:
    logger.info(f"S3 업로드 시작: bucket={bucket_name}, key={s3_file_name}")
    upload_file.file.seek(0)

    get_s3_client(region_name).upload_fileobj(
        upload_file.file,
        bucket_name,
        s3_file_name,
        ExtraArgs={"ContentType": "video/mp4"},
    )

    uri = build_s3_uri(bucket_name, s3_file_name)
    logger.info(f"S3 업로드 완료: {uri}")
    return uri


def generate_presigned_get_url(
    *,
    bucket_name: str,
    region_name: str,
    s3_file_name: str,
    expires_in: int,
) -> str:
    return get_s3_client(region_name).generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_name, "Key": s3_file_name},
        ExpiresIn=expires_in,
    )
