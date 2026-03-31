from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Dict, List

import httpx
from loguru import logger
from shared.edge_hmac import sign_edge_request


class CloudClient:
    def __init__(
        self,
        base_url: str,
        edge_id: str,
        edge_shared_secret: str,
        command_poll_interval: float,
        zone_poll_interval: float,
        heartbeat_interval: float,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.edge_id = edge_id
        self.edge_shared_secret = edge_shared_secret
        if not self.edge_shared_secret:
            raise ValueError("edge_shared_secret is required")
        self.command_poll_interval = command_poll_interval
        self.zone_poll_interval = zone_poll_interval
        self.heartbeat_interval = heartbeat_interval

        self._http = httpx.AsyncClient(base_url=self.base_url, timeout=5.0)
        self._running = False
        self._tasks: List[asyncio.Task[Any]] = []

        self._command_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self._zones: List[Dict[str, Any]] = []
        self._last_heartbeat_at = 0.0

    async def _send_signed(
        self,
        method: str,
        path: str,
        *,
        params: Dict[str, Any] | None = None,
        json: Dict[str, Any] | None = None,
        data: Dict[str, Any] | None = None,
        files: Dict[str, Any] | None = None,
    ) -> httpx.Response:
        request = self._http.build_request(
            method=method,
            url=path,
            params=params,
            json=json,
            data=data,
            files=files,
        )

        body = await request.aread()
        timestamp = str(int(time.time()))
        signature = sign_edge_request(
            shared_secret=self.edge_shared_secret,
            edge_id=self.edge_id,
            timestamp=timestamp,
            method=request.method,
            path=request.url.path,
            query=request.url.query.decode("utf-8"),
            body=body,
        )
        request.headers["X-Edge-Id"] = self.edge_id
        request.headers["X-Edge-Timestamp"] = timestamp
        request.headers["X-Edge-Signature"] = signature
        request.stream = httpx.ByteStream(body)
        return await self._http.send(request)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._tasks = [
            asyncio.create_task(self._poll_commands_loop(), name="cloud_poll_commands"),
            asyncio.create_task(self._poll_zones_loop(), name="cloud_poll_zones"),
        ]

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        await self._http.aclose()

    async def _poll_commands_loop(self) -> None:
        backoff = 1.0
        while self._running:
            try:
                response = await self._send_signed(
                    "GET",
                    "/api/edge/commands",
                    params={"edge_id": self.edge_id},
                )
                response.raise_for_status()
                payload = response.json()
                commands = payload if isinstance(payload, list) else payload.get("commands", [])
                for command in commands:
                    await self._command_queue.put(command)
                backoff = 1.0
                await asyncio.sleep(self.command_poll_interval)
            except Exception as exc:
                logger.warning(f"명령 polling 실패: {exc}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 10.0)

    async def _poll_zones_loop(self) -> None:
        backoff = 1.0
        while self._running:
            try:
                response = await self._send_signed(
                    "GET",
                    "/api/edge/zones",
                    params={"edge_id": self.edge_id},
                )
                response.raise_for_status()
                payload = response.json()
                zones = payload if isinstance(payload, list) else payload.get("zones", [])
                if isinstance(zones, list):
                    self._zones = zones
                backoff = 1.0
                await asyncio.sleep(self.zone_poll_interval)
            except Exception as exc:
                logger.warning(f"구역 polling 실패: {exc}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 15.0)

    async def get_pending_commands(self) -> List[Dict[str, Any]]:
        commands: List[Dict[str, Any]] = []
        while not self._command_queue.empty():
            commands.append(self._command_queue.get_nowait())
        return commands

    def get_latest_zones(self) -> List[Dict[str, Any]]:
        return self._zones

    async def report_heartbeat(self, heartbeat: Dict[str, Any]) -> None:
        now = time.monotonic()
        if now - self._last_heartbeat_at < self.heartbeat_interval:
            return

        self._last_heartbeat_at = now
        payload = {"edge_id": self.edge_id, **heartbeat}
        try:
            await self._send_signed("POST", "/api/edge/heartbeat", json=payload)
        except Exception as exc:
            logger.warning(f"heartbeat 전송 실패(무시): {exc}")

    async def report_log(self, event: Dict[str, Any]) -> None:
        payload = {"edge_id": self.edge_id, **event}
        try:
            await self._send_signed("POST", "/api/edge/log", json=payload)
        except Exception as exc:
            logger.warning(f"로그 전송 실패(무시): {exc}")

    async def upload_clip(
        self,
        edge_id: str,
        event_uid: str,
        clip_started_at: str,
        clip_ended_at: str,
        duration_sec: float,
        file_path: str,
    ) -> None:
        with open(file_path, "rb") as fp:
            files = {
                "file": (
                    os.path.basename(file_path),
                    fp,
                    "video/mp4",
                )
            }
            data = {
                "edge_id": edge_id,
                "event_uid": event_uid,
                "clip_started_at": clip_started_at,
                "clip_ended_at": clip_ended_at,
                "duration_sec": str(duration_sec),
            }
            response = await self._send_signed("POST", "/api/edge/clips", data=data, files=files)
            response.raise_for_status()

    async def report_clip_failed(
        self,
        edge_id: str,
        event_uid: str,
        error_message: str,
    ) -> None:
        data = {
            "edge_id": edge_id,
            "event_uid": event_uid,
            "status": "FAILED",
            "error_message": error_message,
        }
        response = await self._send_signed("POST", "/api/edge/clips", data=data)
        response.raise_for_status()

    async def signaling_post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = await self._send_signed("POST", path, json=payload)
        response.raise_for_status()
        return response.json() if response.text else {}

    async def signaling_get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        response = await self._send_signed("GET", path, params=params)
        response.raise_for_status()
        return response.json() if response.text else {}
