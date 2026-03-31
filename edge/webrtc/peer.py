from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import numpy as np
from loguru import logger

from edge.cloud_client import CloudClient

try:
    from aiortc import (
        RTCPeerConnection,
        RTCConfiguration,
        RTCIceServer,
        RTCSessionDescription,
        VideoStreamTrack,
    )
    from aiortc.sdp import candidate_from_sdp
    from av import VideoFrame

    AIORTC_AVAILABLE = True
except Exception:  # pragma: no cover
    RTCPeerConnection = object  # type: ignore
    RTCConfiguration = object  # type: ignore
    RTCIceServer = object  # type: ignore
    RTCSessionDescription = object  # type: ignore
    VideoStreamTrack = object  # type: ignore
    VideoFrame = object  # type: ignore
    candidate_from_sdp = None  # type: ignore
    AIORTC_AVAILABLE = False


class _CameraTrack(VideoStreamTrack):  # type: ignore[misc]
    def __init__(self) -> None:
        super().__init__()
        self._frame_queue: asyncio.Queue[np.ndarray] = asyncio.Queue(maxsize=1)

    def push_frame(self, frame: np.ndarray) -> None:
        if self._frame_queue.full():
            try:
                self._frame_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        self._frame_queue.put_nowait(frame)

    async def recv(self) -> VideoFrame:
        frame = await self._frame_queue.get()
        video_frame = VideoFrame.from_ndarray(frame, format="bgr24")
        pts, time_base = await self.next_timestamp()
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame


class WebRTCPeer:
    def __init__(
        self,
        cloud_client: CloudClient,
        edge_id: str,
        ice_servers: List[Dict[str, Any]] | None = None,
    ) -> None:
        self.cloud_client = cloud_client
        self.edge_id = edge_id
        self.ice_servers = ice_servers or [{"urls": "stun:stun.l.google.com:19302"}]

        self._pc: Optional[RTCPeerConnection] = None
        self._track: Optional[_CameraTrack] = None
        self._seen_answer_id: Optional[str] = None
        self._seen_remote_ice_ids: set[str] = set()

        self._answer_task: Optional[asyncio.Task[Any]] = None
        self._ice_task: Optional[asyncio.Task[Any]] = None
        self._restart_task: Optional[asyncio.Task[Any]] = None
        self._disconnected_restart_task: Optional[asyncio.Task[Any]] = None
        self._is_stopping = False

    def _build_rtc_configuration(self) -> Any:
        servers: list[Any] = []
        for server in self.ice_servers:
            urls = server.get("urls")
            if not urls:
                continue
            username = server.get("username")
            credential = server.get("credential")
            try:
                servers.append(
                    RTCIceServer(
                        urls=urls,
                        username=username,
                        credential=credential,
                    )
                )
            except Exception as exc:
                logger.warning(f"유효하지 않은 ICE 서버 항목 무시: {exc}")
        if not servers:
            return None
        return RTCConfiguration(iceServers=servers)

    async def start(self) -> None:
        if not AIORTC_AVAILABLE:
            logger.warning("aiortc 미설치: WebRTC 비활성")
            return

        self._pc = RTCPeerConnection(configuration=self._build_rtc_configuration())
        self._track = _CameraTrack()
        self._pc.addTrack(self._track)
        self._seen_answer_id = None
        self._seen_remote_ice_ids = set()

        @self._pc.on("icecandidate")
        async def on_icecandidate(candidate: Any) -> None:
            if candidate is None:
                return
            cand_sdp = candidate.to_sdp()
            # Browser RTCIceCandidate expects "candidate:..." format.
            if not cand_sdp.startswith("candidate:"):
                cand_sdp = f"candidate:{cand_sdp}"
            payload = {
                "edge_id": self.edge_id,
                "sender": "edge",
                "receiver": "browser",
                "candidate": {
                    "candidate": cand_sdp,
                    "sdpMid": candidate.sdpMid,
                    "sdpMLineIndex": candidate.sdpMLineIndex,
                },
            }
            try:
                await self.cloud_client.signaling_post("/api/signaling/ice", payload)
            except Exception as exc:
                logger.warning(f"ICE 업로드 실패: {exc}")

        @self._pc.on("connectionstatechange")
        async def on_connectionstatechange() -> None:
            logger.info(f"WebRTC 상태: {self._pc.connectionState}")
            if self._pc.connectionState == "connected":
                if self._disconnected_restart_task is not None:
                    self._disconnected_restart_task.cancel()
                    self._disconnected_restart_task = None
                return

            if self._pc.connectionState == "disconnected":
                if (
                    not self._is_stopping
                    and self._restart_task is None
                    and self._disconnected_restart_task is None
                ):
                    self._disconnected_restart_task = asyncio.create_task(
                        self._restart_after_disconnected_grace(),
                        name="webrtc_restart_after_disconnected",
                    )
                return

            if self._pc.connectionState in {"failed", "closed"} and not self._is_stopping and self._restart_task is None:
                if self._disconnected_restart_task is not None:
                    self._disconnected_restart_task.cancel()
                    self._disconnected_restart_task = None
                self._restart_task = asyncio.create_task(self._restart_peer(), name="webrtc_restart_peer")

        offer = await self._pc.createOffer()
        await self._pc.setLocalDescription(offer)

        await self.cloud_client.signaling_post(
            "/api/signaling/offer",
            {
                "edge_id": self.edge_id,
                "sender": "edge",
                "receiver": "browser",
                "type": self._pc.localDescription.type,
                "sdp": self._pc.localDescription.sdp,
            },
        )

        self._answer_task = asyncio.create_task(self._poll_answer_loop(), name="webrtc_poll_answer")
        self._ice_task = asyncio.create_task(self._poll_remote_ice_loop(), name="webrtc_poll_ice")

    async def stop(self) -> None:
        self._is_stopping = True
        if self._answer_task:
            self._answer_task.cancel()
        if self._ice_task:
            self._ice_task.cancel()
        if self._disconnected_restart_task:
            self._disconnected_restart_task.cancel()
        if self._answer_task or self._ice_task:
            await asyncio.gather(*(t for t in [self._answer_task, self._ice_task] if t), return_exceptions=True)
        if self._disconnected_restart_task:
            await asyncio.gather(self._disconnected_restart_task, return_exceptions=True)
        if self._pc:
            await self._pc.close()
        self._answer_task = None
        self._ice_task = None
        self._disconnected_restart_task = None
        self._pc = None
        self._track = None
        self._is_stopping = False

    async def _restart_after_disconnected_grace(self) -> None:
        try:
            await asyncio.sleep(3.0)
            if self._is_stopping or self._pc is None or self._restart_task is not None:
                return
            if self._pc.connectionState == "disconnected":
                self._restart_task = asyncio.create_task(self._restart_peer(), name="webrtc_restart_peer")
        except asyncio.CancelledError:
            return
        finally:
            self._disconnected_restart_task = None

    async def _restart_peer(self) -> None:
        try:
            logger.warning("WebRTC 연결 실패 감지: peer 재시작")
            await self.stop()
            await asyncio.sleep(1.0)
            await self.start()
        except Exception as exc:
            logger.warning(f"WebRTC peer 재시작 실패: {exc}")
        finally:
            self._restart_task = None

    async def _poll_answer_loop(self) -> None:
        if not self._pc:
            return
        while True:
            try:
                payload = await self.cloud_client.signaling_get(
                    "/api/signaling/answer",
                    {"edge_id": self.edge_id, "receiver": "edge"},
                )
                answer = payload.get("answer")
                if answer:
                    answer_id = answer.get("message_id")
                    if answer_id and answer_id == self._seen_answer_id:
                        return

                    await self._pc.setRemoteDescription(
                        RTCSessionDescription(sdp=answer["sdp"], type=answer["type"])
                    )
                    self._seen_answer_id = answer_id
                    if answer_id:
                        try:
                            await self.cloud_client.signaling_post(
                                "/api/signaling/answer/ack",
                                {
                                    "edge_id": self.edge_id,
                                    "receiver": "edge",
                                    "message_id": answer_id,
                                },
                            )
                        except Exception as exc:
                            logger.warning(f"Answer ACK 실패(무시): {exc}")
                    return
            except Exception as exc:
                logger.warning(f"Answer polling 오류: {exc}")
            await asyncio.sleep(1.0)

    async def _poll_remote_ice_loop(self) -> None:
        if not self._pc or not candidate_from_sdp:
            return
        while True:
            try:
                payload = await self.cloud_client.signaling_get(
                    "/api/signaling/ice",
                    {"edge_id": self.edge_id, "receiver": "edge"},
                )
                candidates = payload.get("candidates", [])
                ack_ids: list[str] = []
                for raw in candidates:
                    message_id = raw.get("message_id")
                    if message_id:
                        ack_ids.append(message_id)
                    if message_id and message_id in self._seen_remote_ice_ids:
                        continue

                    data = raw.get("candidate", {})
                    if not data:
                        continue
                    cand_sdp = data.get("candidate", "")
                    if not cand_sdp:
                        continue
                    # aiortc parser expects candidate body without "candidate:" prefix.
                    if cand_sdp.startswith("candidate:"):
                        cand_sdp = cand_sdp[len("candidate:") :]
                    cand = candidate_from_sdp(cand_sdp)
                    cand.sdpMid = data.get("sdpMid")
                    cand.sdpMLineIndex = data.get("sdpMLineIndex")
                    await self._pc.addIceCandidate(cand)

                    if message_id:
                        self._seen_remote_ice_ids.add(message_id)

                if ack_ids:
                    await self.cloud_client.signaling_post(
                        "/api/signaling/ice/ack",
                        {
                            "edge_id": self.edge_id,
                            "receiver": "edge",
                            "message_ids": list(set(ack_ids)),
                        },
                    )
            except Exception as exc:
                logger.warning(f"ICE polling 오류: {exc}")
            await asyncio.sleep(1.0)

    def send_frame(self, frame: np.ndarray) -> None:
        if self._track is None:
            return
        self._track.push_frame(frame)
