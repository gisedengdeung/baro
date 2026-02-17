from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class Point(BaseModel):
    x: int
    y: int


class DangerZoneBase(BaseModel):
    name: str
    points: List[Point]


class DangerZoneCreate(DangerZoneBase):
    id: str


class DangerZone(DangerZoneBase):
    id: str


class ZoneResponse(BaseModel):
    status: str = "success"
    message: str
    zone_id: str
