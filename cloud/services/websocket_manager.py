from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from loguru import logger


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: Dict[str, List[Any]] = defaultdict(list)

    async def connect(self, websocket: Any, channel: str) -> None:
        await websocket.accept()
        self._connections[channel].append(websocket)

    def disconnect(self, websocket: Any, channel: str) -> None:
        if websocket in self._connections[channel]:
            self._connections[channel].remove(websocket)

    async def broadcast(self, channel: str, message: Dict[str, Any]) -> None:
        for ws in list(self._connections[channel]):
            try:
                await ws.send_json(message)
            except Exception as exc:
                logger.warning(f"WS 전송 실패({channel}): {exc}")
                self.disconnect(ws, channel)

    async def broadcast_to_edge(self, channel: str, edge_id: str, message: Dict[str, Any]) -> None:
        """edge_id 구독자와 전체 구독자(edge_id 없이 연결된 브라우저) 모두에게 전송."""
        await self.broadcast(f"{channel}:{edge_id}", message)
        await self.broadcast(channel, message)

    async def broadcast_to_channel_tree(self, channel: str, message: Dict[str, Any]) -> None:
        """전체 채널과 edge별 하위 채널을 모두 포함해 전송."""
        prefix = f"{channel}:"
        target_channels = [
            name
            for name in list(self._connections.keys())
            if name == channel or name.startswith(prefix)
        ]
        for target in target_channels:
            await self.broadcast(target, message)

    def status(self) -> Dict[str, int]:
        return {channel: len(connections) for channel, connections in self._connections.items()}
