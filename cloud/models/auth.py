from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

UserRole = Literal["admin", "operator"]


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)


class SignupRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    role: UserRole


class UserPublic(BaseModel):
    id: str
    email: str
    role: UserRole


class LoginResponse(BaseModel):
    status: str = "ok"
    user: UserPublic
    access_token: str | None = None
    refresh_token: str | None = None


class SignupResponse(BaseModel):
    status: str = "ok"
    user: UserPublic
    access_token: str | None = None
    refresh_token: str | None = None


class RefreshResponse(BaseModel):
    status: str = "ok"
    access_token: str | None = None
    refresh_token: str | None = None


class LogoutResponse(BaseModel):
    status: str = "ok"
