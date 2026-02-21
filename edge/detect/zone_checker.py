from __future__ import annotations

from typing import Any, Dict, List, Tuple

import cv2
import numpy as np
from loguru import logger


class ZoneChecker:
    @staticmethod
    def _build_zone(zone_data: Dict[str, Any]) -> Dict[str, Any] | None:
        try:
            points_list = [[p["x"], p["y"]] for p in zone_data.get("points", [])]
            points = np.array(points_list, dtype=np.int32)
            if points.size == 0:
                return None
            return {
                "id": zone_data.get("id", "N/A"),
                "name": zone_data.get("name", "Unknown Zone"),
                "points": points,
                "iou_threshold": float(zone_data.get("iou_threshold", 0.2)),
                "bounding_rect": cv2.boundingRect(points),
            }
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning(f"위험 구역 파싱 실패: {exc}")
            return None

    @staticmethod
    def _check_person_in_zone(person_bbox: List[int], zone: Dict[str, Any]) -> Tuple[bool, float]:
        px1, py1, px2, py2 = person_bbox
        zx, zy, zw, zh = zone["bounding_rect"]

        if px2 < zx or px1 > zx + zw or py2 < zy or py1 > zy + zh:
            return False, 0.0

        person_rect_points = np.array([[px1, py1], [px2, py1], [px2, py2], [px1, py2]], dtype=np.int32)
        key_points = [
            (px1, py1),
            (px2, py1),
            (px1, py2),
            (px2, py2),
            ((px1 + px2) // 2, py2),
        ]
        for point in key_points:
            if cv2.pointPolygonTest(zone["points"], point, False) >= 0:
                return True, 1.0

        try:
            person_area = max(1, (px2 - px1) * (py2 - py1))
            height = max(py2, zone["bounding_rect"][1] + zone["bounding_rect"][3])
            width = max(px2, zone["bounding_rect"][0] + zone["bounding_rect"][2])
            mask = np.zeros((height, width), dtype=np.uint8)

            cv2.fillPoly(mask, [person_rect_points], 255)
            person_mask = mask.copy()
            mask.fill(0)
            cv2.fillPoly(mask, [zone["points"]], 255)
            zone_mask = mask

            intersection = cv2.bitwise_and(person_mask, zone_mask)
            iou = cv2.countNonZero(intersection) / person_area
            return iou >= zone["iou_threshold"], round(iou, 2)
        except Exception as exc:
            logger.warning(f"침입 계산 실패: {exc}")
            return False, 0.0

    def check(self, persons: List[Dict[str, Any]], zones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        built_zones = [z for z in (self._build_zone(raw) for raw in zones) if z is not None]
        alerts: List[Dict[str, Any]] = []
        for zone in built_zones:
            persons_in_zone = []
            for idx, person in enumerate(persons):
                is_in, iou = self._check_person_in_zone(person["bbox"], zone)
                if not is_in:
                    continue
                persons_in_zone.append(
                    {
                        "person_index": idx,
                        "bbox": person["bbox"],
                        "confidence": person.get("confidence", 0.0),
                        "intrusion_iou": round(iou, 2),
                    }
                )

            if persons_in_zone:
                alerts.append(
                    {
                        "zone_id": zone["id"],
                        "zone_name": zone["name"],
                        "person_count": len(persons_in_zone),
                        "persons": persons_in_zone,
                    }
                )
        return alerts
