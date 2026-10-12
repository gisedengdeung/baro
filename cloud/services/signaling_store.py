from __future__ import annotations

from datetime import datetime, timedelta, timezone
import threading
import time as _time_module
from collections import defaultdict
from typing import Any, Dict, List, Tuple
from uuid import uuid4


class SignalingStore:
    def __init__(
        self,
        offer_ttl_sec: int = 30,
        answer_ttl_sec: int = 30,
        ice_ttl_sec: int = 20,
    ) -> None:
        self.offer_ttl_sec = offer_ttl_sec
        self.answer_ttl_sec = answer_ttl_sec
        self.ice_ttl_sec = ice_ttl_sec

        self._offers: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._answers: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._ice: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
        self._lock = threading.Lock()

        self._viewer_sessions: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._viewer_ttl_sec: int = 60

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _to_iso(dt: datetime) -> str:
        return dt.isoformat()

    @staticmethod
    def _from_iso(value: str) -> datetime:
        return datetime.fromisoformat(value)

    def _new_message(self, payload: Dict[str, Any], ttl_sec: int) -> Dict[str, Any]:
        now = self._now()
        return {
            **payload,
            "message_id": str(uuid4()),
            "created_at": self._to_iso(now),
            "expires_at": self._to_iso(now + timedelta(seconds=ttl_sec)),
            "acked": False,
            "acked_at": None,
        }

    def _is_expired(self, message: Dict[str, Any], now: datetime) -> bool:
        expires_at = message.get("expires_at")
        if not expires_at:
            return True
        try:
            return self._from_iso(expires_at) <= now
        except Exception:
            return True

    def _purge_expired_locked(self) -> None:
        now = self._now()

        for key, message in list(self._offers.items()):
            if message.get("acked") or self._is_expired(message, now):
                self._offers.pop(key, None)

        for key, message in list(self._answers.items()):
            if message.get("acked") or self._is_expired(message, now):
                self._answers.pop(key, None)

        for key, messages in list(self._ice.items()):
            kept = [m for m in messages if not m.get("acked") and not self._is_expired(m, now)]
            if kept:
                self._ice[key] = kept
            else:
                self._ice.pop(key, None)

    def get_offer_for_browser_session(self, edge_id: str, session_receiver: str) -> Dict[str, Any] | None:
        """브라우저 세션별 offer 조회. 세션 슬롯에 없으면 edge가 저장한 'browser' 슬롯에서 복사."""
        with self._lock:
            self._purge_expired_locked()
            message = self._offers.get((edge_id, session_receiver))
            if message and not message.get("acked"):
                return dict(message)
            base = self._offers.get((edge_id, "browser"))
            if base and not base.get("acked"):
                copy = {**base, "message_id": str(uuid4()), "acked": False, "acked_at": None}
                self._offers[(edge_id, session_receiver)] = copy
                return dict(copy)
            return None

    def get_ice_for_browser_session(self, edge_id: str, session_receiver: str) -> List[Dict[str, Any]]:
        """브라우저 세션별 ICE 조회. edge가 저장한 'browser' 슬롯의 후보를 세션 슬롯으로 fan-out."""
        with self._lock:
            self._purge_expired_locked()
            base_candidates = self._ice.get((edge_id, "browser"), [])
            session_key = (edge_id, session_receiver)
            existing_source_ids = {m.get("_source_id") for m in self._ice.get(session_key, [])}
            for candidate in base_candidates:
                if not candidate.get("acked") and candidate["message_id"] not in existing_source_ids:
                    copy = {
                        **candidate,
                        "message_id": str(uuid4()),
                        "_source_id": candidate["message_id"],
                        "acked": False,
                        "acked_at": None,
                    }
                    self._ice[session_key].append(copy)
            return [dict(m) for m in self._ice.get(session_key, []) if not m.get("acked")]

    def record_viewer(self, edge_id: str, session_id: str) -> None:
        """브라우저 세션이 활성 상태임을 기록."""
        with self._lock:
            self._viewer_sessions[edge_id][session_id] = _time_module.time()

    def get_active_viewers(self, edge_id: str) -> List[str]:
        """TTL 내에 폴링한 브라우저 세션 목록 반환."""
        with self._lock:
            now = _time_module.time()
            sessions = self._viewer_sessions.get(edge_id, {})
            active = {sid: ts for sid, ts in sessions.items() if now - ts < self._viewer_ttl_sec}
            self._viewer_sessions[edge_id] = active
            return list(active.keys())

    def upsert_offer(self, edge_id: str, receiver: str, offer: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._purge_expired_locked()
            message = self._new_message(offer, self.offer_ttl_sec)
            self._offers[(edge_id, receiver)] = message
            return dict(message)

    def get_offer(self, edge_id: str, receiver: str) -> Dict[str, Any] | None:
        with self._lock:
            self._purge_expired_locked()
            message = self._offers.get((edge_id, receiver))
            if not message or message.get("acked"):
                return None
            return dict(message)

    def ack_offer(self, edge_id: str, receiver: str, message_id: str) -> bool:
        with self._lock:
            self._purge_expired_locked()
            message = self._offers.get((edge_id, receiver))
            if not message:
                return False
            if message.get("message_id") != message_id:
                return False
            message["acked"] = True
            message["acked_at"] = self._to_iso(self._now())
            return True

    def upsert_answer(self, edge_id: str, receiver: str, answer: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._purge_expired_locked()
            message = self._new_message(answer, self.answer_ttl_sec)
            self._answers[(edge_id, receiver)] = message
            return dict(message)

    def get_answer(self, edge_id: str, receiver: str) -> Dict[str, Any] | None:
        with self._lock:
            self._purge_expired_locked()
            message = self._answers.get((edge_id, receiver))
            if not message or message.get("acked"):
                return None
            return dict(message)

    def ack_answer(self, edge_id: str, receiver: str, message_id: str) -> bool:
        with self._lock:
            self._purge_expired_locked()
            message = self._answers.get((edge_id, receiver))
            if not message:
                return False
            if message.get("message_id") != message_id:
                return False
            message["acked"] = True
            message["acked_at"] = self._to_iso(self._now())
            return True

    def push_ice(self, edge_id: str, receiver: str, candidate: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._purge_expired_locked()
            message = self._new_message(candidate, self.ice_ttl_sec)
            self._ice[(edge_id, receiver)].append(message)
            return dict(message)

    def get_ice(self, edge_id: str, receiver: str) -> List[Dict[str, Any]]:
        with self._lock:
            self._purge_expired_locked()
            return [
                dict(message)
                for message in self._ice.get((edge_id, receiver), [])
                if not message.get("acked")
            ]

    def ack_ice(self, edge_id: str, receiver: str, message_ids: List[str]) -> int:
        with self._lock:
            self._purge_expired_locked()
            if not message_ids:
                return 0

            id_set = set(message_ids)
            acked_count = 0
            messages = self._ice.get((edge_id, receiver), [])
            now_iso = self._to_iso(self._now())

            for message in messages:
                if message.get("message_id") in id_set and not message.get("acked"):
                    message["acked"] = True
                    message["acked_at"] = now_iso
                    acked_count += 1

            self._ice[(edge_id, receiver)] = [m for m in messages if not m.get("acked")]
            if not self._ice[(edge_id, receiver)]:
                self._ice.pop((edge_id, receiver), None)

            return acked_count
