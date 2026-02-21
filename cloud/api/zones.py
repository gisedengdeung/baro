from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from cloud.dependencies import get_command_queue, get_zone_service
from cloud.models.zones import DangerZone, DangerZoneBase, DangerZoneCreate, Point, ZoneResponse
from cloud.services.command_queue import CommandQueueService
from cloud.services.zone_service import ZoneService

router = APIRouter()


@router.get("", response_model=List[DangerZone])
def get_all_zones(zone_service: ZoneService = Depends(get_zone_service)) -> List[DangerZone]:
    zones = zone_service.get_all_zones()
    return [DangerZone(id=z["id"], name=z["name"], points=[Point(**p) for p in z.get("points", [])]) for z in zones]


@router.get("/{zone_id}", response_model=DangerZone)
def get_zone(zone_id: str, zone_service: ZoneService = Depends(get_zone_service)) -> DangerZone:
    zone = zone_service.get_zone(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone not found: {zone_id}")
    return DangerZone(id=zone["id"], name=zone["name"], points=[Point(**p) for p in zone.get("points", [])])


@router.post("", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
def create_zone(
    zone: DangerZoneCreate,
    edge_id: str = Query("edge-default"),
    zone_service: ZoneService = Depends(get_zone_service),
    command_queue: CommandQueueService = Depends(get_command_queue),
) -> ZoneResponse:
    if zone_service.get_zone(zone.id):
        raise HTTPException(status_code=409, detail=f"Zone already exists: {zone.id}")
    zone_service.add_or_update_zone(zone.id, zone.model_dump())
    command_queue.push(edge_id, {"command": "UPDATE_ZONES", "data": zone_service.get_all_zones()})
    return ZoneResponse(message="zone created", zone_id=zone.id)


@router.put("/{zone_id}", response_model=ZoneResponse)
def update_zone(
    zone_id: str,
    zone_data: DangerZoneBase,
    edge_id: str = Query("edge-default"),
    zone_service: ZoneService = Depends(get_zone_service),
    command_queue: CommandQueueService = Depends(get_command_queue),
) -> ZoneResponse:
    if not zone_service.get_zone(zone_id):
        raise HTTPException(status_code=404, detail=f"Zone not found: {zone_id}")
    zone_service.add_or_update_zone(zone_id, zone_data.model_dump())
    command_queue.push(edge_id, {"command": "UPDATE_ZONES", "data": zone_service.get_all_zones()})
    return ZoneResponse(message="zone updated", zone_id=zone_id)


@router.delete("/{zone_id}", response_model=ZoneResponse)
def delete_zone(
    zone_id: str,
    edge_id: str = Query("edge-default"),
    zone_service: ZoneService = Depends(get_zone_service),
    command_queue: CommandQueueService = Depends(get_command_queue),
) -> ZoneResponse:
    if not zone_service.get_zone(zone_id):
        raise HTTPException(status_code=404, detail=f"Zone not found: {zone_id}")
    zone_service.delete_zone(zone_id)
    command_queue.push(edge_id, {"command": "UPDATE_ZONES", "data": zone_service.get_all_zones()})
    return ZoneResponse(message="zone deleted", zone_id=zone_id)
