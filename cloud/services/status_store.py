from __future__ import annotations

import threading
from datetime import datetime
from typing import Dict, Optional
from zoneinfo import ZoneInfo

from cloud.models.status import EdgeHeartbeat

KST = ZoneInfo("Asia/Seoul")


class StatusStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest: Dict[str, EdgeHeartbeat] = {}

    def update(self, heartbeat: EdgeHeartbeat) -> None:
        hb = heartbeat.model_copy(update={"updated_at": datetime.now(KST)})
        with self._lock:
            self._latest[hb.edge_id] = hb

    def get(self, edge_id: str) -> Optional[EdgeHeartbeat]:
        with self._lock:
            return self._latest.get(edge_id)

    def get_any(self) -> Optional[EdgeHeartbeat]:
        with self._lock:
            if not self._latest:
                return None
            return next(iter(self._latest.values()))
