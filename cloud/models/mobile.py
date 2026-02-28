from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

MobilePlatform = Literal["ios", "android"]


class MobileDeviceRegisterRequest(BaseModel):
    platform: MobilePlatform
    fcm_token: str = Field(min_length=10)
    user_id: Optional[str] = None
    edge_scope: List[str] = Field(default_factory=list)


class MobileDeviceRecord(BaseModel):
    id: str
    user_id: str
    platform: MobilePlatform
    fcm_token: str
    edge_scope: List[str] = Field(default_factory=list)
    last_notified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class MobileDeviceRegisterResponse(BaseModel):
    status: str = "ok"
    device: MobileDeviceRecord


class MobileDeviceDeleteResponse(BaseModel):
    status: str = "ok"
    deleted: bool = True
