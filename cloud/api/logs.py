from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from cloud.dependencies import get_db_service
from cloud.services.db_service import DBService

router = APIRouter()


@router.get("", response_model=List[Dict[str, Any]])
def get_logs(
    limit: int = Query(50, ge=1, le=200),
    db_service: DBService = Depends(get_db_service),
) -> List[Dict[str, Any]]:
    return db_service.get_events(limit=limit)


@router.get("/{log_id}/clip")
def get_log_clip(log_id: int, db_service: DBService = Depends(get_db_service)):
    event = db_service.get_event_by_id(log_id, include_internal=True)
    if not event:
        raise HTTPException(status_code=404, detail="Log not found.")

    if event.get("clip_status") != "READY" or not event.get("clip_path"):
        raise HTTPException(status_code=404, detail="Clip not ready.")

    clip_path = Path(event["clip_path"])
    if not clip_path.exists():
        raise HTTPException(status_code=404, detail="Clip file missing.")

    return FileResponse(
        path=clip_path,
        media_type="video/mp4",
        filename=clip_path.name,
    )
