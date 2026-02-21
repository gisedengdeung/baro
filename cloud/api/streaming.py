from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/video_feed")
def deprecated_video_feed():
    raise HTTPException(
        status_code=410,
        detail="MJPEG 스트리밍은 제거되었습니다. WebRTC(/api/signaling) 경로를 사용하세요.",
    )
