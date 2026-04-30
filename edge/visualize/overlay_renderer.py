from __future__ import annotations

from collections import defaultdict
from typing import Any

import cv2
import numpy as np
from loguru import logger


SKELETON_EDGES = [
    (0, 1), (0, 2), (1, 3), (2, 4),          # 얼굴
    (5, 6),                                    # 어깨
    (5, 7), (7, 9), (6, 8), (8, 10),          # 팔
    (5, 11), (6, 12), (11, 12),               # 몸통
    (11, 13), (13, 15), (12, 14), (14, 16),   # 다리
]


class OverlayRenderer:
    COLOR_GREEN = (0, 200, 0)
    COLOR_ORANGE = (0, 165, 255)
    COLOR_RED = (0, 0, 255)
    COLOR_WHITE = (255, 255, 255)
    COLOR_BLACK = (0, 0, 0)

    def __init__(
        self,
        enabled: bool = True,
        draw_zone_polygons: bool = True,
        draw_label_confidence: bool = False,
    ) -> None:
        self.enabled = enabled
        self.draw_zone_polygons = draw_zone_polygons
        self.draw_label_confidence = draw_label_confidence

    @staticmethod
    def _safe_int_bbox(raw_bbox: Any) -> tuple[int, int, int, int] | None:
        if not isinstance(raw_bbox, (list, tuple)) or len(raw_bbox) != 4:
            return None
        try:
            x1, y1, x2, y2 = [int(v) for v in raw_bbox]
            return x1, y1, x2, y2
        except Exception:
            return None

    @staticmethod
    def _build_zone_points(zone: dict[str, Any]) -> np.ndarray | None:
        raw_points = zone.get("points", [])
        if not isinstance(raw_points, list) or len(raw_points) < 3:
            return None
        points: list[list[int]] = []
        for point in raw_points:
            try:
                points.append([int(point["x"]), int(point["y"])])
            except Exception:
                return None
        return np.array(points, dtype=np.int32)

    def _draw_text_badge(
        self,
        frame: np.ndarray,
        text: str,
        origin: tuple[int, int],
        bg_color: tuple[int, int, int],
    ) -> None:
        x, y = origin
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1
        (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        x = max(0, x)
        y = max(th + 4, y)

        cv2.rectangle(
            frame,
            (x, y - th - 6),
            (x + tw + 8, y + baseline),
            bg_color,
            -1,
        )
        cv2.putText(
            frame,
            text,
            (x + 4, y - 3),
            font,
            font_scale,
            self.COLOR_WHITE,
            thickness,
            cv2.LINE_AA,
        )

    def _draw_zones(
        self,
        frame: np.ndarray,
        zones: list[dict[str, Any]],
        intrusion_zone_ids: set[str],
        intrusion_zone_names: set[str],
    ) -> None:
        if not self.draw_zone_polygons:
            return

        overlay = frame.copy()
        for zone in zones:
            points = self._build_zone_points(zone)
            if points is None:
                continue

            zone_id = str(zone.get("id", ""))
            zone_name = str(zone.get("name", ""))
            is_intrusion = zone_id in intrusion_zone_ids or zone_name in intrusion_zone_names
            stroke = self.COLOR_ORANGE if is_intrusion else self.COLOR_GREEN
            fill = (0, 80, 190) if is_intrusion else (0, 120, 0)

            cv2.fillPoly(overlay, [points], fill)
            cv2.polylines(frame, [points], isClosed=True, color=stroke, thickness=2)

            label = zone_name or zone_id or "ZONE"
            px, py = int(points[0][0]), int(points[0][1])
            self._draw_text_badge(frame, label, (px, py - 4), stroke)

        cv2.addWeighted(overlay, 0.18, frame, 0.82, 0, frame)

    def _draw_skeleton(
        self,
        frame: np.ndarray,
        keypoints: list[list[float]],
        color: tuple[int, int, int],
    ) -> None:
        for i, j in SKELETON_EDGES:
            if i >= len(keypoints) or j >= len(keypoints):
                continue
            x1, y1 = int(keypoints[i][0]), int(keypoints[i][1])
            x2, y2 = int(keypoints[j][0]), int(keypoints[j][1])
            if x1 == 0 and y1 == 0 or x2 == 0 and y2 == 0:
                continue
            cv2.line(frame, (x1, y1), (x2, y2), color, 2)
        for kp in keypoints:
            x, y = int(kp[0]), int(kp[1])
            if x == 0 and y == 0:
                continue
            cv2.circle(frame, (x, y), 3, self.COLOR_WHITE, -1)

    def _draw_persons(
        self,
        frame: np.ndarray,
        persons: list[dict[str, Any]],
        intrusion_indices: set[int],
        intrusion_map: dict[int, set[str]],
        action_result: dict[str, Any] | None = None,
    ) -> None:
        is_accident = bool(action_result and action_result.get("is_accident"))

        for idx, person in enumerate(persons):
            bbox = self._safe_int_bbox(person.get("bbox"))
            if bbox is None:
                continue
            x1, y1, x2, y2 = bbox
            is_intrusion = idx in intrusion_indices

            if is_accident:
                color = self.COLOR_RED
            elif is_intrusion:
                color = self.COLOR_ORANGE
            else:
                color = self.COLOR_GREEN

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            keypoints = person.get("keypoints", [])
            if keypoints:
                self._draw_skeleton(frame, keypoints, color)

            label_parts = ["Person"]
            if is_accident and action_result:
                label_parts.append(action_result.get("class_name", "ACCIDENT"))
            if is_intrusion:
                zone_names = sorted(intrusion_map.get(idx, set()))
                label_parts.append(f"INTRUSION:{'|'.join(zone_names) if zone_names else 'YES'}")

            if self.draw_label_confidence:
                conf = person.get("confidence")
                if isinstance(conf, (int, float)):
                    label_parts.append(f"{float(conf):.2f}")

            self._draw_text_badge(frame, " ".join(label_parts), (x1, y1 - 2), color)

    def _draw_violations(
        self,
        frame: np.ndarray,
        violations: list[dict[str, Any]],
    ) -> None:
        for v in violations:
            if not v.get("is_violation"):
                continue
            bbox = self._safe_int_bbox(v.get("bbox"))
            if bbox is None:
                continue
            x1, y1, x2, y2 = bbox
            cv2.rectangle(frame, (x1, y1), (x2, y2), self.COLOR_RED, 2)
            label = v.get("class_name", "VIOLATION")
            if self.draw_label_confidence:
                conf = v.get("confidence")
                if isinstance(conf, (int, float)):
                    label += f" {float(conf):.2f}"
            self._draw_text_badge(frame, label, (x1, y1 - 2), self.COLOR_RED)

    def _draw_risk_level(self, frame: np.ndarray, risk_level: str) -> None:
        if not risk_level:
            return

        risk = str(risk_level).upper()
        if risk in {"CRITICAL", "LOTO_RISK_DETECTED"}:
            color = self.COLOR_RED
        elif risk in {"WARNING", "NOTICE"}:
            color = self.COLOR_ORANGE
        else:
            color = self.COLOR_GREEN

        self._draw_text_badge(frame, f"RISK: {risk}", (8, 26), color)

    def render(
        self,
        frame: np.ndarray,
        persons: list[dict[str, Any]],
        zones: list[dict[str, Any]],
        zone_alerts: list[dict[str, Any]],
        risk_level: str,
        violations: list[dict[str, Any]] | None = None,
        action_result: dict[str, Any] | None = None,
    ) -> np.ndarray:
        if not self.enabled:
            return frame

        try:
            canvas = frame.copy()

            intrusion_indices: set[int] = set()
            intrusion_zone_ids: set[str] = set()
            intrusion_zone_names: set[str] = set()
            intrusion_map: dict[int, set[str]] = defaultdict(set)

            for alert in zone_alerts:
                zone_id = str(alert.get("zone_id", ""))
                zone_name = str(alert.get("zone_name", ""))
                if zone_id:
                    intrusion_zone_ids.add(zone_id)
                if zone_name:
                    intrusion_zone_names.add(zone_name)

                for person_info in alert.get("persons", []):
                    person_index = person_info.get("person_index")
                    if not isinstance(person_index, int):
                        continue
                    intrusion_indices.add(person_index)
                    if zone_name:
                        intrusion_map[person_index].add(zone_name)

            self._draw_zones(canvas, zones, intrusion_zone_ids, intrusion_zone_names)
            self._draw_persons(canvas, persons, intrusion_indices, intrusion_map, action_result)
            self._draw_violations(canvas, violations or [])
            self._draw_risk_level(canvas, risk_level)
            return canvas
        except Exception as exc:
            logger.warning(f"오버레이 렌더링 실패: {exc}")
            return frame
