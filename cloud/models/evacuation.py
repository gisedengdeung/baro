from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

NodeKind = Literal["WAYPOINT", "EXIT", "STAIR", "DOOR"]


class RoutePoint(BaseModel):
    x: float
    y: float


class EvacuationExitBase(BaseModel):
    edge_id: str = Field(default="edge-default")
    name: str
    x: float
    y: float
    description: Optional[str] = None


class EvacuationExit(EvacuationExitBase):
    id: str


class EvacuationNodeBase(BaseModel):
    edge_id: str = Field(default="edge-default")
    name: str
    x: float
    y: float
    kind: NodeKind = "WAYPOINT"
    meta: Dict[str, Any] = Field(default_factory=dict)


class EvacuationNode(EvacuationNodeBase):
    id: str


class EvacuationEdgeBase(BaseModel):
    edge_id: str = Field(default="edge-default")
    from_node_id: str
    to_node_id: str
    distance: float = Field(gt=0)
    is_blocked: bool = False


class EvacuationEdge(EvacuationEdgeBase):
    id: str


class EvacuationRouteResponse(BaseModel):
    edge_id: str
    zone_id: Optional[str] = None
    incident_type: Optional[str] = None
    start_node_id: str
    end_node_id: str
    total_distance: float
    estimated_seconds: float
    polyline: List[RoutePoint] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    node_ids: List[str] = Field(default_factory=list)
