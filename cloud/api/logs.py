from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query

from cloud.dependencies import get_db_service
from cloud.services.db_service import DBService

router = APIRouter()


@router.get("", response_model=List[Dict[str, Any]])
def get_logs(
    limit: int = Query(50, ge=1, le=200),
    db_service: DBService = Depends(get_db_service),
) -> List[Dict[str, Any]]:
    return db_service.get_events(limit=limit)
