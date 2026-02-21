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

    def status(self) -> Dict[str, int]:
        return {channel: len(connections) for channel, connections in self._connections.items()}
