from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from cloud.dependencies import get_signaling_store
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


@router.post("/offer")
def post_offer(payload: OfferPayload, store: SignalingStore = Depends(get_signaling_store)):
    message = store.upsert_offer(payload.edge_id, payload.receiver, payload.model_dump())
    return {
        "status": "ok",
        "message_id": message["message_id"],
        "expires_at": message["expires_at"],
    }


@router.get("/offer")
def get_offer(
    edge_id: str = Query("edge-default"),
    receiver: str = Query(...),
    store: SignalingStore = Depends(get_signaling_store),
):
    offer = store.get_offer(edge_id, receiver)
    return {"offer": offer}


@router.post("/offer/ack")
def ack_offer(payload: AckPayload, store: SignalingStore = Depends(get_signaling_store)):
    acked = store.ack_offer(payload.edge_id, payload.receiver, payload.message_id)
    return {"status": "ok", "acked": acked}


@router.post("/answer")
def post_answer(payload: AnswerPayload, store: SignalingStore = Depends(get_signaling_store)):
    message = store.upsert_answer(payload.edge_id, payload.receiver, payload.model_dump())
    return {
        "status": "ok",
        "message_id": message["message_id"],
        "expires_at": message["expires_at"],
    }


@router.get("/answer")
def get_answer(
    edge_id: str = Query("edge-default"),
    receiver: str = Query(...),
    store: SignalingStore = Depends(get_signaling_store),
):
    answer = store.get_answer(edge_id, receiver)
    return {"answer": answer}


@router.post("/answer/ack")
def ack_answer(payload: AckPayload, store: SignalingStore = Depends(get_signaling_store)):
    acked = store.ack_answer(payload.edge_id, payload.receiver, payload.message_id)
    return {"status": "ok", "acked": acked}


@router.post("/ice")
def post_ice(payload: IcePayload, store: SignalingStore = Depends(get_signaling_store)):
    message = store.push_ice(payload.edge_id, payload.receiver, payload.model_dump())
    return {
        "status": "ok",
        "message_id": message["message_id"],
        "expires_at": message["expires_at"],
    }


@router.get("/ice")
def get_ice(
    edge_id: str = Query("edge-default"),
    receiver: str = Query(...),
    store: SignalingStore = Depends(get_signaling_store),
):
    candidates = store.get_ice(edge_id, receiver)
    return {"candidates": candidates}


@router.post("/ice/ack")
def ack_ice(payload: IceAckPayload, store: SignalingStore = Depends(get_signaling_store)):
    acked_count = store.ack_ice(payload.edge_id, payload.receiver, payload.message_ids)
    return {"status": "ok", "acked_count": acked_count}
