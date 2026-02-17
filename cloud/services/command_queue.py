from __future__ import annotations

import threading
from collections import defaultdict, deque
from typing import Any, Deque, Dict, List


class CommandQueueService:
    def __init__(self) -> None:
        self._queues: Dict[str, Deque[Dict[str, Any]]] = defaultdict(deque)
        self._lock = threading.Lock()

    def push(self, edge_id: str, command: Dict[str, Any]) -> None:
        with self._lock:
            self._queues[edge_id].append(command)

    def pop_all(self, edge_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            queue = self._queues[edge_id]
            items = list(queue)
            queue.clear()
            return items
