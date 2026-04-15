from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from cloud.dependencies import get_clip_service, get_db_service
from cloud.services.clip_service import ClipService
from cloud.services.db_service import DBService

router = APIRouter()


@router.get("", response_model=List[Dict[str, Any]])
def get_logs(
    limit: int = Query(50, ge=1, le=200),
    edge_id: str | None = Query(None),
    db_service: DBService = Depends(get_db_service),
) -> List[Dict[str, Any]]:
    return db_service.get_events(limit=limit, edge_id=edge_id)


@router.get("/{log_id}/clip")
def get_log_clip(
    log_id: int,
    db_service: DBService = Depends(get_db_service),
    clip_service: ClipService = Depends(get_clip_service),
):
    event = db_service.get_event_by_id(log_id, include_internal=True)
    if not event:
        raise HTTPException(status_code=404, detail="Log not found.")

    if event.get("clip_status") != "READY" or not event.get("clip_path"):
        raise HTTPException(status_code=404, detail="Clip not ready.")

    clip_path_str = event["clip_path"]

    try:
        clip_url = clip_service.build_clip_download_url(clip_path_str)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return RedirectResponse(url=clip_url)
