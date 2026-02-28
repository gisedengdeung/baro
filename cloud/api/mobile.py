from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from cloud.dependencies import get_current_user, get_mobile_push_service
from cloud.models.auth import UserPublic
from cloud.models.mobile import (
    MobileDeviceDeleteResponse,
    MobileDeviceRecord,
    MobileDeviceRegisterRequest,
    MobileDeviceRegisterResponse,
)
from cloud.services.mobile_push_service import MobilePushService

router = APIRouter()


@router.post("/devices/register", response_model=MobileDeviceRegisterResponse)
def register_device(
    payload: MobileDeviceRegisterRequest,
    current_user: UserPublic = Depends(get_current_user),
    mobile_push_service: MobilePushService = Depends(get_mobile_push_service),
) -> MobileDeviceRegisterResponse:
    if payload.user_id and payload.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot register token for another user")

    device = mobile_push_service.register_device(
        user_id=current_user.id,
        platform=payload.platform,
        fcm_token=payload.fcm_token,
        edge_scope=payload.edge_scope,
    )
    return MobileDeviceRegisterResponse(status="ok", device=MobileDeviceRecord(**device))


@router.delete("/devices/{device_id}", response_model=MobileDeviceDeleteResponse)
def unregister_device(
    device_id: str,
    current_user: UserPublic = Depends(get_current_user),
    mobile_push_service: MobilePushService = Depends(get_mobile_push_service),
) -> MobileDeviceDeleteResponse:
    deleted = mobile_push_service.delete_device(device_id=device_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return MobileDeviceDeleteResponse(status="ok", deleted=True)
