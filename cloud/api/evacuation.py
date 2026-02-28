from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from cloud.dependencies import get_current_user, get_evacuation_service, get_zone_service
from cloud.models.auth import UserPublic
from cloud.models.evacuation import (
    EvacuationEdge,
    EvacuationEdgeBase,
    EvacuationExit,
    EvacuationExitBase,
    EvacuationNode,
    EvacuationNodeBase,
    EvacuationRouteResponse,
)
from cloud.services.evacuation_service import EvacuationService
from cloud.services.zone_service import ZoneService

router = APIRouter()


@router.get("/route", response_model=EvacuationRouteResponse)
def get_evacuation_route(
    edge_id: str = Query(...),
    zone_id: Optional[str] = Query(default=None),
    incident_type: Optional[str] = Query(default=None),
    _user: UserPublic = Depends(get_current_user),
    evacuation_service: EvacuationService = Depends(get_evacuation_service),
    zone_service: ZoneService = Depends(get_zone_service),
) -> EvacuationRouteResponse:
    try:
        route = evacuation_service.get_route(
            edge_id=edge_id,
            zone_id=zone_id,
            incident_type=incident_type,
            zone_service=zone_service,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return EvacuationRouteResponse(**route)


@router.get("/exits", response_model=List[EvacuationExit])
def list_exits(
    edge_id: Optional[str] = Query(default=None),
    _user: UserPublic = Depends(get_current_user),
    evacuation_service: EvacuationService = Depends(get_evacuation_service),
) -> List[EvacuationExit]:
    return [EvacuationExit(**x) for x in evacuation_service.list_exits(edge_id=edge_id)]


@router.post("/exits", response_model=EvacuationExit, status_code=status.HTTP_201_CREATED)
def create_exit(
    payload: EvacuationExitBase,
    _user: UserPublic = Depends(get_current_user),
    evacuation_service: EvacuationService = Depends(get_evacuation_service),
) -> EvacuationExit:
    return EvacuationExit(**evacuation_service.upsert_exit(payload.model_dump()))


@router.put("/exits/{exit_id}", response_model=EvacuationExit)
def update_exit(
    exit_id: str,
    payload: EvacuationExitBase,
    _user: UserPublic = Depends(get_current_user),
    evacuation_service: EvacuationService = Depends(get_evacuation_service),
) -> EvacuationExit:
    updated = evacuation_service.upsert_exit(payload.model_dump(), exit_id=exit_id)
    return EvacuationExit(**updated)


@router.delete("/exits/{exit_id}")
def delete_exit(
    exit_id: str,
    _user: UserPublic = Depends(get_current_user),
    evacuation_service: EvacuationService = Depends(get_evacuation_service),
):
    deleted = evacuation_service.delete_exit(exit_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exit not found")
    return {"status": "ok", "deleted": True}


@router.get("/nodes", response_model=List[EvacuationNode])
def list_nodes(
    edge_id: Optional[str] = Query(default=None),
    _user: UserPublic = Depends(get_current_user),
    evacuation_service: EvacuationService = Depends(get_evacuation_service),
) -> List[EvacuationNode]:
    return [EvacuationNode(**x) for x in evacuation_service.list_nodes(edge_id=edge_id)]


@router.post("/nodes", response_model=EvacuationNode, status_code=status.HTTP_201_CREATED)
def create_node(
    payload: EvacuationNodeBase,
    _user: UserPublic = Depends(get_current_user),
    evacuation_service: EvacuationService = Depends(get_evacuation_service),
) -> EvacuationNode:
    return EvacuationNode(**evacuation_service.upsert_node(payload.model_dump()))


@router.put("/nodes/{node_id}", response_model=EvacuationNode)
def update_node(
    node_id: str,
    payload: EvacuationNodeBase,
    _user: UserPublic = Depends(get_current_user),
    evacuation_service: EvacuationService = Depends(get_evacuation_service),
) -> EvacuationNode:
    updated = evacuation_service.upsert_node(payload.model_dump(), node_id=node_id)
    return EvacuationNode(**updated)


@router.delete("/nodes/{node_id}")
def delete_node(
    node_id: str,
    _user: UserPublic = Depends(get_current_user),
    evacuation_service: EvacuationService = Depends(get_evacuation_service),
):
    deleted = evacuation_service.delete_node(node_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    return {"status": "ok", "deleted": True}


@router.get("/edges", response_model=List[EvacuationEdge])
def list_edges(
    edge_id: Optional[str] = Query(default=None),
    _user: UserPublic = Depends(get_current_user),
    evacuation_service: EvacuationService = Depends(get_evacuation_service),
) -> List[EvacuationEdge]:
    return [EvacuationEdge(**x) for x in evacuation_service.list_edges(edge_id=edge_id)]


@router.post("/edges", response_model=EvacuationEdge, status_code=status.HTTP_201_CREATED)
def create_edge(
    payload: EvacuationEdgeBase,
    _user: UserPublic = Depends(get_current_user),
    evacuation_service: EvacuationService = Depends(get_evacuation_service),
) -> EvacuationEdge:
    return EvacuationEdge(**evacuation_service.upsert_edge(payload.model_dump()))


@router.put("/edges/{edge_id}", response_model=EvacuationEdge)
def update_edge(
    edge_id: str,
    payload: EvacuationEdgeBase,
    _user: UserPublic = Depends(get_current_user),
    evacuation_service: EvacuationService = Depends(get_evacuation_service),
) -> EvacuationEdge:
    updated = evacuation_service.upsert_edge(payload.model_dump(), edge_id=edge_id)
    return EvacuationEdge(**updated)


@router.delete("/edges/{edge_id}")
def delete_edge(
    edge_id: str,
    _user: UserPublic = Depends(get_current_user),
    evacuation_service: EvacuationService = Depends(get_evacuation_service),
):
    deleted = evacuation_service.delete_edge(edge_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edge not found")
    return {"status": "ok", "deleted": True}
