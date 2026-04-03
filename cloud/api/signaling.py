from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from cloud.dependencies import (
    get_auth_service,
    require_edge_request_auth,
    require_signaling_browser_auth,
)
from cloud.services.auth_service import AuthService
from cloud.dependencies import get_signaling_store
from cloud.services.edge_auth import ensure_authenticated_edge_id
from cloud.services.signaling_store import SignalingStore

router = APIRouter()


class OfferPayload(BaseModel):
    edge_id: str = "edge-default"
    sender: str
    receiver: str
    type: str
    sdp: str


class AnswerPayload(BaseModel):
    edge_id: str = "edge-default"
    sender: str
    receiver: str
    type: str
    sdp: str


class IcePayload(BaseModel):
    edge_id: str = "edge-default"
    sender: str
    receiver: str
    candidate: Dict[str, Any]


class AckPayload(BaseModel):
    edge_id: str = "edge-default"
    receiver: str
    message_id: str


class IceAckPayload(BaseModel):
    edge_id: str = "edge-default"
    receiver: str
    message_ids: List[str]


def _normalize_sender_receiver(sender: str | None, receiver: str | None) -> tuple[str | None, str | None]:
    sender_v = sender.strip().lower() if isinstance(sender, str) else None
    receiver_v = receiver.strip().lower() if isinstance(receiver, str) else None
    return sender_v, receiver_v


def _require_signaling_auth_if_needed(
    request: Request,
    sender: str | None,
    receiver: str | None,
) -> str | None:
    sender_v, receiver_v = _normalize_sender_receiver(sender, receiver)

    # Auth policy:
    # - Browser-originated signaling must be authenticated.
    # - browser receiver without sender context (GET/ACK from browser) must be authenticated.
    # - Edge-originated offer (sender=edge, receiver=browser) remains allowed.
    if sender_v == "browser" or (sender_v is None and receiver_v == "browser"):
        require_signaling_browser_auth(request, sender=sender_v, receiver=receiver_v)
        return None

    if sender_v == "edge" or (sender_v is None and receiver_v == "edge"):
        return require_edge_request_auth(request)

    if sender_v != "edge" and receiver_v == "browser":
        require_signaling_browser_auth(request, sender=sender_v, receiver=receiver_v)
    return None


def _resolve_signaling_edge_id(
    request: Request,
    sender: str | None,
    receiver: str | None,
    declared_edge_id: str,
) -> str:
    authenticated_edge_id = _require_signaling_auth_if_needed(request, sender, receiver)
    if authenticated_edge_id:
        return ensure_authenticated_edge_id(authenticated_edge_id, declared_edge_id)
    return declared_edge_id


@router.post("/offer")
def post_offer(
    payload: OfferPayload,
    request: Request,
    store: SignalingStore = Depends(get_signaling_store),
    _auth_service: AuthService = Depends(get_auth_service),
):
    edge_id = _resolve_signaling_edge_id(request, payload.sender, payload.receiver, payload.edge_id)
    message = store.upsert_offer(
        edge_id,
        payload.receiver,
        {**payload.model_dump(), "edge_id": edge_id},
    )
    return {
        "status": "ok",
        "message_id": message["message_id"],
        "expires_at": message["expires_at"],
    }


@router.get("/offer")
def get_offer(
    request: Request,
    edge_id: str = Query("edge-default"),
    receiver: str = Query(...),
    store: SignalingStore = Depends(get_signaling_store),
    _auth_service: AuthService = Depends(get_auth_service),
):
    edge_id = _resolve_signaling_edge_id(request, None, receiver, edge_id)
    offer = store.get_offer(edge_id, receiver)
    return {"offer": offer}


@router.post("/offer/ack")
def ack_offer(
    payload: AckPayload,
    request: Request,
    store: SignalingStore = Depends(get_signaling_store),
    _auth_service: AuthService = Depends(get_auth_service),
):
    edge_id = _resolve_signaling_edge_id(request, None, payload.receiver, payload.edge_id)
    acked = store.ack_offer(edge_id, payload.receiver, payload.message_id)
    return {"status": "ok", "acked": acked}


@router.post("/answer")
def post_answer(
    payload: AnswerPayload,
    request: Request,
    store: SignalingStore = Depends(get_signaling_store),
    _auth_service: AuthService = Depends(get_auth_service),
):
    edge_id = _resolve_signaling_edge_id(request, payload.sender, payload.receiver, payload.edge_id)
    message = store.upsert_answer(
        edge_id,
        payload.receiver,
        {**payload.model_dump(), "edge_id": edge_id},
    )
    return {
        "status": "ok",
        "message_id": message["message_id"],
        "expires_at": message["expires_at"],
    }


@router.get("/answer")
def get_answer(
    request: Request,
    edge_id: str = Query("edge-default"),
    receiver: str = Query(...),
    store: SignalingStore = Depends(get_signaling_store),
    _auth_service: AuthService = Depends(get_auth_service),
):
    edge_id = _resolve_signaling_edge_id(request, None, receiver, edge_id)
    answer = store.get_answer(edge_id, receiver)
    return {"answer": answer}


@router.post("/answer/ack")
def ack_answer(
    payload: AckPayload,
    request: Request,
    store: SignalingStore = Depends(get_signaling_store),
    _auth_service: AuthService = Depends(get_auth_service),
):
    edge_id = _resolve_signaling_edge_id(request, None, payload.receiver, payload.edge_id)
    acked = store.ack_answer(edge_id, payload.receiver, payload.message_id)
    return {"status": "ok", "acked": acked}


@router.post("/ice")
def post_ice(
    payload: IcePayload,
    request: Request,
    store: SignalingStore = Depends(get_signaling_store),
    _auth_service: AuthService = Depends(get_auth_service),
):
    edge_id = _resolve_signaling_edge_id(request, payload.sender, payload.receiver, payload.edge_id)
    message = store.push_ice(
        edge_id,
        payload.receiver,
        {**payload.model_dump(), "edge_id": edge_id},
    )
    return {
        "status": "ok",
        "message_id": message["message_id"],
        "expires_at": message["expires_at"],
    }


@router.get("/ice")
def get_ice(
    request: Request,
    edge_id: str = Query("edge-default"),
    receiver: str = Query(...),
    store: SignalingStore = Depends(get_signaling_store),
    _auth_service: AuthService = Depends(get_auth_service),
):
    edge_id = _resolve_signaling_edge_id(request, None, receiver, edge_id)
    candidates = store.get_ice(edge_id, receiver)
    return {"candidates": candidates}


@router.post("/ice/ack")
def ack_ice(
    payload: IceAckPayload,
    request: Request,
    store: SignalingStore = Depends(get_signaling_store),
    _auth_service: AuthService = Depends(get_auth_service),
):
    edge_id = _resolve_signaling_edge_id(request, None, payload.receiver, payload.edge_id)
    acked_count = store.ack_ice(edge_id, payload.receiver, payload.message_ids)
    return {"status": "ok", "acked_count": acked_count}
