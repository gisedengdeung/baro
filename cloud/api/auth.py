from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from cloud.dependencies import get_auth_service, get_current_user
from cloud.models.auth import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RefreshResponse,
    SignupRequest,
    SignupResponse,
    UserPublic,
)
from cloud.services.auth_service import AuthService, REFRESH_COOKIE_NAME

router = APIRouter()


@router.post("/signup", response_model=SignupResponse)
def signup(
    payload: SignupRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> SignupResponse:
    user = auth_service.register_user(payload.email, payload.password, payload.role)
    access_token, refresh_token = auth_service.issue_tokens(user)
    auth_service.set_auth_cookies(response, access_token, refresh_token)
    return SignupResponse(status="ok", user=user)


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    user = auth_service.authenticate(payload.email, payload.password)
    access_token, refresh_token = auth_service.issue_tokens(user)
    auth_service.set_auth_cookies(response, access_token, refresh_token)
    return LoginResponse(status="ok", user=user)


@router.post("/refresh", response_model=RefreshResponse)
def refresh(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> RefreshResponse:
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        auth_service.clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

    try:
        _user, access_token, new_refresh_token = auth_service.refresh(refresh_token)
    except HTTPException:
        auth_service.clear_auth_cookies(response)
        raise

    auth_service.set_auth_cookies(response, access_token, new_refresh_token)
    return RefreshResponse(status="ok")


@router.post("/logout", response_model=LogoutResponse)
def logout(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> LogoutResponse:
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if refresh_token:
        auth_service.revoke_by_refresh_token(refresh_token)
    auth_service.clear_auth_cookies(response)
    return LogoutResponse(status="ok")


@router.get("/me", response_model=UserPublic)
def me(current_user: UserPublic = Depends(get_current_user)) -> UserPublic:
    return current_user
