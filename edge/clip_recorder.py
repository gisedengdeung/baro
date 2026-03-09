from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Deque, Dict, List
from uuid import uuid4

import cv2
import numpy as np
from loguru import logger

from edge.cloud_client import CloudClient


@dataclass(slots=True)
class FramePacket:
    timestamp: datetime
    frame: np.ndarray


@dataclass(slots=True)
class PendingClip:
    event_uid: str
    edge_id: str
    event_time: datetime
    started_at: datetime
    ends_at: datetime
    frames: List[FramePacket] = field(default_factory=list)
    finalized: bool = False


class EdgeClipRecorder:
    def __init__(
        self,
        cloud_client: CloudClient,
        edge_id: str,
        output_dir: str,
        pre_seconds: int = 10,
        post_seconds: int = 10,
        target_fps: int = 10,
        width: int = 1280,
        height: int = 720,
    ) -> None:
        self.cloud_client = cloud_client
        self.edge_id = edge_id

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.pre_seconds = pre_seconds
        self.post_seconds = post_seconds
        self.target_fps = target_fps
        self.width = width
        self.height = height

        self.buffer_duration = timedelta(seconds=max(1, pre_seconds + 2))
        self.frame_interval_sec = 1.0 / max(1, target_fps)

        self._buffer: Deque[FramePacket] = deque()
        self._pending: Dict[str, PendingClip] = {}
        self._tasks: set[asyncio.Task[Any]] = set()
        self._last_append_monotonic: float = 0.0

    @staticmethod
    def _severity_rank(level: str) -> int:
        normalized = (level or "").strip().upper()
        ranking = {
            "INFO": 1,
            "NOTICE": 2,
            "WARNING": 3,
            "HIGH": 3,
            "ERROR": 4,
            "CRITICAL": 5,
        }
        return ranking.get(normalized, 0)

    def should_trigger(self, log_risk_level: str) -> bool:
        return self._severity_rank(log_risk_level) >= self._severity_rank("NOTICE")

    def _resize_frame(self, frame: np.ndarray) -> np.ndarray:
        return cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_AREA)

    def ingest_frame(self, frame: np.ndarray, now: datetime | None = None) -> None:
        ts = now or datetime.utcnow()
        loop = asyncio.get_running_loop()
        now_mono = loop.time()
        if self._last_append_monotonic and (now_mono - self._last_append_monotonic) < self.frame_interval_sec:
            return
        self._last_append_monotonic = now_mono

        packed = FramePacket(timestamp=ts, frame=self._resize_frame(frame))
        self._buffer.append(packed)

        cutoff = ts - self.buffer_duration
        while self._buffer and self._buffer[0].timestamp < cutoff:
            self._buffer.popleft()

        self._collect_post_frames(packed)

    def trigger(self, event_uid: str | None = None, event_time: datetime | None = None) -> str:
        uid = event_uid or str(uuid4())
        at = event_time or datetime.utcnow()
        started_at = at - timedelta(seconds=self.pre_seconds)
        ends_at = at + timedelta(seconds=self.post_seconds)

        pre_frames = [
            FramePacket(timestamp=packet.timestamp, frame=packet.frame.copy())
            for packet in self._buffer
            if packet.timestamp >= started_at
        ]

        pending = PendingClip(
            event_uid=uid,
            edge_id=self.edge_id,
            event_time=at,
            started_at=started_at,
            ends_at=ends_at,
            frames=pre_frames,
        )
        self._pending[uid] = pending
        logger.info(f"클립 녹화 트리거: event_uid={uid} pre_frames={len(pre_frames)}")
        return uid

    def _collect_post_frames(self, packet: FramePacket) -> None:
        completed: List[PendingClip] = []
        for pending in self._pending.values():
            if pending.finalized:
                continue
            if packet.timestamp <= pending.ends_at:
                pending.frames.append(
                    FramePacket(timestamp=packet.timestamp, frame=packet.frame.copy())
                )
            if packet.timestamp >= pending.ends_at:
                pending.finalized = True
                completed.append(pending)

        for pending in completed:
            self._pending.pop(pending.event_uid, None)
            task = asyncio.create_task(
                self._encode_and_upload_clip(pending),
                name=f"clip_finalize_{pending.event_uid}",
            )
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def _encode_and_upload_clip(self, clip: PendingClip) -> None:
        if not clip.frames:
            await self.cloud_client.report_clip_failed(
                edge_id=self.edge_id,
                event_uid=clip.event_uid,
                error_message="No frames collected for clip.",
            )
            return

        local_path = self.output_dir / f"{clip.event_uid}.mp4"
        try:
            await asyncio.to_thread(self._write_mp4, local_path, clip.frames)
            ended_at = clip.frames[-1].timestamp
            duration_sec = max(
                0.0,
                (ended_at - clip.started_at).total_seconds(),
            )

            await self.cloud_client.upload_clip(
                edge_id=self.edge_id,
                event_uid=clip.event_uid,
                clip_started_at=clip.started_at.isoformat(),
                clip_ended_at=ended_at.isoformat(),
                duration_sec=duration_sec,
                file_path=str(local_path),
            )
            logger.info(f"클립 업로드 성공: event_uid={clip.event_uid}")
        except Exception as exc:
            logger.warning(f"클립 처리 실패(event_uid={clip.event_uid}): {exc}")
            try:
                await self.cloud_client.report_clip_failed(
                    edge_id=self.edge_id,
                    event_uid=clip.event_uid,
                    error_message=str(exc),
                )
            except Exception as report_exc:
                logger.warning(f"클립 실패 상태 보고 실패(event_uid={clip.event_uid}): {report_exc}")
        finally:
            try:
                local_path.unlink(missing_ok=True)
            except Exception as cleanup_exc:
                logger.warning(f"로컬 클립 파일 삭제 실패({local_path}): {cleanup_exc}")

    def _write_mp4(self, path: Path, frames: List[FramePacket]) -> None:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(path), fourcc, float(self.target_fps), (self.width, self.height))
        if not writer.isOpened():
            raise RuntimeError("Failed to open mp4 writer.")

        try:
            for packet in frames:
                writer.write(packet.frame)
        finally:
            writer.release()

    async def shutdown(self) -> None:
        if not self._tasks:
            return
        await asyncio.gather(*self._tasks, return_exceptions=True)
