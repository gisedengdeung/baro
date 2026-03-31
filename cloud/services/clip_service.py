from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

from fastapi import UploadFile
from loguru import logger

from cloud.services.db_service import DBService
from cloud.services.s3_uploader import upload_video_to_s3_from_memory

KST = ZoneInfo("Asia/Seoul")


class ClipService:
    def __init__(
        self,
        db_service: DBService,
    ) -> None:
        self.db_service = db_service

    async def save_uploaded_clip(
        self,
        edge_id: str,
        event_uid: str,
        clip_started_at: str,
        clip_ended_at: str,
        duration_sec: float,
        upload: UploadFile,
    ) -> Dict[str, Any]:
        existing = self.db_service.get_event_by_event_uid(event_uid)
        if not existing:
            raise ValueError(f"Unknown event_uid: {event_uid}")
        if existing.get("edge_id") != edge_id:
            raise ValueError(f"event_uid belongs to edge_id={existing.get('edge_id')}, not {edge_id}")

        # S3에 저장될 파일 경로 문자열 생성 (ex. clips/edge-default/20260319/클립고유ID.mp4)
        day_tag = datetime.now(KST).strftime("%Y%m%d")
        s3_file_name = f"clips/{edge_id}/{day_tag}/{event_uid}.mp4"

        s3_object_key = await asyncio.to_thread(
            upload_video_to_s3_from_memory, upload, s3_file_name
        )

        if not s3_object_key:
            raise ValueError(f"S3 업로드 실패: {event_uid}")

        # DB에 S3 object key 저장
        updated = self.db_service.set_clip_ready_by_event_uid(
            event_uid=event_uid,
            edge_id=edge_id,
            clip_path=s3_object_key,
            clip_started_at=clip_started_at,
            clip_ended_at=clip_ended_at,
            duration_sec=duration_sec,
        )
        if not updated:
            raise ValueError(f"Failed to map clip to event_uid: {event_uid}")

        await self.db_service.broadcast_log_update(updated)
        return updated

    async def mark_clip_failed(
        self,
        edge_id: str,
        event_uid: str,
        error_message: str | None = None,
    ) -> Dict[str, Any] | None:
        updated = self.db_service.set_clip_failed_by_event_uid(
            event_uid=event_uid,
            edge_id=edge_id,
            error_message=error_message,
        )
        if updated:
            await self.db_service.broadcast_log_update(updated)
        return updated
