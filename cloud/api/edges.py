from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from cloud.dependencies import get_db_service
from cloud.services.db_service import DBService

router = APIRouter()


@router.get("", response_model=List[Dict[str, Any]])
def get_edges(
    db_service: DBService = Depends(get_db_service),
) -> List[Dict[str, Any]]:
    return db_service.get_edges()
