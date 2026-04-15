from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import numpy as np
from loguru import logger

from edge.cloud_client import CloudClient

try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
    from aiortc.sdp import candidate_from_sdp
    from av import VideoFrame

    AIORTC_AVAILABLE = True
except Exception:  # pragma: no cover
    RTCPeerConnection = object  # type: ignore
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


class WebRTCSession:
    """단일 브라우저 세션(browser-{session_id})과의 WebRTC 연결."""

    def __init__(self, cloud_client: CloudClient, edge_id: str, session_id: str) -> None:
        self.cloud_client = cloud_client
        self.edge_id = edge_id
        self.session_id = session_id  # e.g. 'browser-xyz'

        self._pc: Optional[RTCPeerConnection] = None
        self._track: Optional[_CameraTrack] = None
        self._seen_answer_id: Optional[str] = None
        self._seen_remote_ice_ids: set[str] = set()

        self._answer_task: Optional[asyncio.Task[Any]] = None
        self._ice_task: Optional[asyncio.Task[Any]] = None
        self._restart_task: Optional[asyncio.Task[Any]] = None
        self._disconnected_restart_task: Optional[asyncio.Task[Any]] = None
        self._is_stopping = False

    @property
    def _edge_receiver(self) -> str:
        """브라우저가 edge에 보낼 때 사용하는 receiver 값 (edge-{session_id})."""
        return f"edge-{self.session_id}"

    async def start(self) -> None:
        if not AIORTC_AVAILABLE:
            logger.warning("aiortc 미설치: WebRTC 비활성")
            return

        self._pc = RTCPeerConnection()
        self._track = _CameraTrack()
        self._pc.addTrack(self._track)
        self._seen_answer_id = None
        self._seen_remote_ice_ids = set()

        @self._pc.on("icecandidate")
        async def on_icecandidate(candidate: Any) -> None:
            if candidate is None:
                return
            cand_sdp = candidate.to_sdp()
            if not cand_sdp.startswith("candidate:"):
                cand_sdp = f"candidate:{cand_sdp}"
            payload = {
                "edge_id": self.edge_id,
                "sender": "edge",
                "receiver": self.session_id,
                "candidate": {
                    "candidate": cand_sdp,
                    "sdpMid": candidate.sdpMid,
                    "sdpMLineIndex": candidate.sdpMLineIndex,
                },
            }
            try:
                await self.cloud_client.signaling_post("/api/signaling/ice", payload)
            except Exception as exc:
                logger.warning(f"[{self.session_id}] ICE 업로드 실패: {exc}")

        @self._pc.on("connectionstatechange")
        async def on_connectionstatechange() -> None:
            state = self._pc.connectionState
            logger.info(f"[{self.session_id}] WebRTC 상태: {state}")

            if state == "connected":
                if self._disconnected_restart_task is not None:
                    self._disconnected_restart_task.cancel()
                    self._disconnected_restart_task = None
                return

            if state == "disconnected":
                if (
                    not self._is_stopping
                    and self._restart_task is None
                    and self._disconnected_restart_task is None
                ):
                    self._disconnected_restart_task = asyncio.create_task(
                        self._restart_after_disconnected_grace(),
                        name=f"webrtc_restart_disconnected_{self.session_id}",
                    )
                return

            if state in {"failed", "closed"} and not self._is_stopping and self._restart_task is None:
                if self._disconnected_restart_task is not None:
                    self._disconnected_restart_task.cancel()
                    self._disconnected_restart_task = None
                self._restart_task = asyncio.create_task(
                    self._restart_peer(),
                    name=f"webrtc_restart_peer_{self.session_id}",
                )

        offer = await self._pc.createOffer()
        await self._pc.setLocalDescription(offer)

        await self.cloud_client.signaling_post(
            "/api/signaling/offer",
            {
                "edge_id": self.edge_id,
                "sender": "edge",
                "receiver": self.session_id,
                "type": self._pc.localDescription.type,
                "sdp": self._pc.localDescription.sdp,
            },
        )
        logger.info(f"[{self.session_id}] offer 전송 완료")

        self._answer_task = asyncio.create_task(
            self._poll_answer_loop(),
            name=f"webrtc_poll_answer_{self.session_id}",
        )
        self._ice_task = asyncio.create_task(
            self._poll_remote_ice_loop(),
            name=f"webrtc_poll_ice_{self.session_id}",
        )

    async def stop(self) -> None:
        self._is_stopping = True
        tasks = [t for t in [self._answer_task, self._ice_task, self._disconnected_restart_task] if t]
        for t in tasks:
            t.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        if self._restart_task:
            self._restart_task.cancel()
            await asyncio.gather(self._restart_task, return_exceptions=True)
        if self._pc:
            await self._pc.close()
        self._answer_task = None
        self._ice_task = None
        self._restart_task = None
        self._disconnected_restart_task = None
        self._pc = None
        self._track = None
        self._is_stopping = False

    def send_frame(self, frame: np.ndarray) -> None:
        if self._track is not None:
            self._track.push_frame(frame)

    async def _restart_after_disconnected_grace(self) -> None:
        try:
            await asyncio.sleep(3.0)
            if self._is_stopping or self._pc is None or self._restart_task is not None:
                return
            if self._pc.connectionState == "disconnected":
                self._restart_task = asyncio.create_task(
                    self._restart_peer(),
                    name=f"webrtc_restart_peer_{self.session_id}",
                )
        except asyncio.CancelledError:
            return
        finally:
            self._disconnected_restart_task = None

    async def _restart_peer(self) -> None:
        try:
            logger.warning(f"[{self.session_id}] WebRTC 연결 실패: peer 재시작")
            await self.stop()
            await asyncio.sleep(1.0)
            await self.start()
        except Exception as exc:
            logger.warning(f"[{self.session_id}] WebRTC peer 재시작 실패: {exc}")
        finally:
            self._restart_task = None

    async def _poll_answer_loop(self) -> None:
        if not self._pc:
            return
        while True:
            try:
                payload = await self.cloud_client.signaling_get(
                    "/api/signaling/answer",
                    {"edge_id": self.edge_id, "receiver": self._edge_receiver},
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
                                    "receiver": self._edge_receiver,
                                    "message_id": answer_id,
                                },
                            )
                        except Exception as exc:
                            logger.warning(f"[{self.session_id}] Answer ACK 실패(무시): {exc}")
                    return
            except Exception as exc:
                logger.warning(f"[{self.session_id}] Answer polling 오류: {exc}")
            await asyncio.sleep(1.0)

    async def _poll_remote_ice_loop(self) -> None:
        if not self._pc or not candidate_from_sdp:
            return
        while True:
            try:
                payload = await self.cloud_client.signaling_get(
                    "/api/signaling/ice",
                    {"edge_id": self.edge_id, "receiver": self._edge_receiver},
                )
                candidates = payload.get("candidates", [])
                ack_ids: List[str] = []
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
                    if cand_sdp.startswith("candidate:"):
                        cand_sdp = cand_sdp[len("candidate:"):]
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
                            "receiver": self._edge_receiver,
                            "message_ids": list(set(ack_ids)),
                        },
                    )
            except Exception as exc:
                logger.warning(f"[{self.session_id}] ICE polling 오류: {exc}")
            await asyncio.sleep(1.0)


class WebRTCPeerManager:
    """여러 브라우저 세션의 WebRTC 연결을 관리."""

    VIEWER_POLL_INTERVAL = 3.0

    def __init__(self, cloud_client: CloudClient, edge_id: str) -> None:
        self.cloud_client = cloud_client
        self.edge_id = edge_id
        self._sessions: Dict[str, WebRTCSession] = {}
        self._lock = asyncio.Lock()
        self._poll_task: Optional[asyncio.Task[Any]] = None
        self._is_stopping = False

    async def start(self) -> None:
        if not AIORTC_AVAILABLE:
            logger.warning("aiortc 미설치: WebRTC 비활성")
            return
        self._poll_task = asyncio.create_task(
            self._poll_viewers_loop(),
            name="webrtc_poll_viewers",
        )
        logger.info("WebRTCPeerManager 시작")

    async def stop(self) -> None:
        self._is_stopping = True
        if self._poll_task:
            self._poll_task.cancel()
            await asyncio.gather(self._poll_task, return_exceptions=True)
        async with self._lock:
            for session in self._sessions.values():
                await session.stop()
            self._sessions.clear()
        logger.info("WebRTCPeerManager 종료")

    def send_frame(self, frame: np.ndarray) -> None:
        for session in self._sessions.values():
            session.send_frame(frame)

    async def _poll_viewers_loop(self) -> None:
        while not self._is_stopping:
            try:
                viewers = await self.cloud_client.get_viewers()
                viewer_set = set(viewers)

                async with self._lock:
                    # 새 세션 생성
                    for session_id in viewer_set:
                        if session_id not in self._sessions:
                            session = WebRTCSession(self.cloud_client, self.edge_id, session_id)
                            self._sessions[session_id] = session
                            asyncio.create_task(
                                session.start(),
                                name=f"webrtc_session_start_{session_id}",
                            )
                            logger.info(f"새 WebRTC 세션 생성: {session_id}")

                    # 사라진 세션 종료
                    for session_id in list(self._sessions.keys()):
                        if session_id not in viewer_set:
                            session = self._sessions.pop(session_id)
                            asyncio.create_task(
                                session.stop(),
                                name=f"webrtc_session_stop_{session_id}",
                            )
                            logger.info(f"WebRTC 세션 종료: {session_id}")

            except Exception as exc:
                logger.warning(f"viewer 폴링 오류: {exc}")

            await asyncio.sleep(self.VIEWER_POLL_INTERVAL)


# 하위 호환: 기존 코드에서 WebRTCPeer를 import하는 경우를 위한 alias
WebRTCPeer = WebRTCPeerManager
