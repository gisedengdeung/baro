from __future__ import annotations

import asyncio
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from fastapi import UploadFile
from loguru import logger

from cloud.services.db_service import DBService


class ClipService:
    def __init__(
        self,
        db_service: DBService,
        storage_dir: str,
        retention_days: int = 7,
        cleanup_interval_sec: int = 3600,
    ) -> None:
        self.db_service = db_service
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.retention_days = max(1, retention_days)
        self.cleanup_interval_sec = max(60, cleanup_interval_sec)

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
            raise ValueError(
                f"event_uid belongs to edge_id={existing.get('edge_id')}, not {edge_id}"
            )

        day_tag = datetime.utcnow().strftime("%Y%m%d")
        target_dir = self.storage_dir / edge_id / day_tag
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{event_uid}.mp4"

        await self._copy_upload_file(upload, target_path)

        updated = self.db_service.set_clip_ready_by_event_uid(
            event_uid=event_uid,
            edge_id=edge_id,
            clip_path=str(target_path.resolve()),
            clip_started_at=clip_started_at,
            clip_ended_at=clip_ended_at,
            duration_sec=duration_sec,
        )
        if not updated:
            target_path.unlink(missing_ok=True)
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

    async def cleanup_once(self) -> Dict[str, int]:
        cutoff = datetime.utcnow() - timedelta(days=self.retention_days)
        candidates = self.db_service.list_expired_clip_candidates(cutoff.isoformat())
        if not candidates:
            return {"found": 0, "expired": 0, "deleted": 0}

        deleted = 0
        expire_ids: List[int] = []
        for item in candidates:
            clip_path = item.get("clip_path")
            log_id = item.get("id")
            if not clip_path or not log_id:
                continue

            try:
                Path(clip_path).unlink(missing_ok=True)
                deleted += 1
            except Exception as exc:
                logger.warning(f"만료 클립 파일 삭제 실패(path={clip_path}): {exc}")
            finally:
                expire_ids.append(int(log_id))

        expired_count = self.db_service.mark_clips_expired(expire_ids)
        for log_id in expire_ids:
            event = self.db_service.get_event_by_id(log_id)
            if event:
                await self.db_service.broadcast_log_update(event)

        return {"found": len(candidates), "expired": expired_count, "deleted": deleted}

    async def cleanup_loop(self) -> None:
        while True:
            try:
                result = await self.cleanup_once()
                if result["expired"] > 0:
                    logger.info(
                        f"클립 만료 정리 완료: found={result['found']} "
                        f"expired={result['expired']} deleted={result['deleted']}"
                    )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning(f"클립 만료 정리 루프 오류: {exc}")
            await asyncio.sleep(self.cleanup_interval_sec)

    @staticmethod
    async def _copy_upload_file(upload: UploadFile, target_path: Path) -> None:
        def _copy() -> None:
            upload.file.seek(0)
            with open(target_path, "wb") as out:
                shutil.copyfileobj(upload.file, out)

        await asyncio.to_thread(_copy)
