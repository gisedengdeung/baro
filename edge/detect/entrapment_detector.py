from __future__ import annotations

from typing import Any, Dict, List

from loguru import logger


class EntrapmentDetector:
    """
    위험구역 침입 상태가 컨베이어 동작 중 일정 프레임 이상 지속될 때 끼임 위험으로 판단.
    """

    def __init__(self, frame_threshold: int = 8) -> None:
        self.frame_threshold = max(1, frame_threshold)
        self._counts: Dict[str, int] = {}
        logger.info(f"EntrapmentDetector 초기화 완료: frame_threshold={self.frame_threshold}")

    def analyze(
        self,
        persons: List[Dict[str, Any]],
        zone_alerts: List[Dict[str, Any]],
        conveyor_is_on: bool,
    ) -> Dict[str, Any]:
        if not conveyor_is_on:
            self._counts.clear()
            return {"is_entrapment": False}

        active_keys: set[str] = set()
        for zone in zone_alerts:
            zone_id = zone.get("zone_id", "unknown-zone")
            for p in zone.get("persons", []):
                person_index = p.get("person_index")
                if person_index is None:
                    continue

                key = f"{zone_id}:{person_index}"
                active_keys.add(key)
                self._counts[key] = self._counts.get(key, 0) + 1
                if self._counts[key] >= self.frame_threshold:
                    return {
                        "is_entrapment": True,
                        "zone_id": zone_id,
                        "person_index": person_index,
                        "score": self._counts[key],
                    }

                # 낙상 + 위험구역 동시 관측 시 즉시 승격
                if 0 <= person_index < len(persons):
                    analysis = persons[person_index].get("pose_analysis", {})
                    if analysis.get("is_falling"):
                        return {
                            "is_entrapment": True,
                            "zone_id": zone_id,
                            "person_index": person_index,
                            "score": self.frame_threshold,
                        }

        stale = [k for k in self._counts.keys() if k not in active_keys]
        for key in stale:
            self._counts.pop(key, None)

        return {"is_entrapment": False}
