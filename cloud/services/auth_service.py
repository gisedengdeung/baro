from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Dict
from uuid import uuid4

from fastapi import HTTPException, Request, Response, status

from cloud.db import get_connection
from cloud.models.auth import UserPublic, UserRole

ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"


@dataclass(slots=True)
class AuthConfig:
    jwt_secret: str
    access_ttl_sec: int
    refresh_ttl_sec: int
    cookie_secure: bool
    cookie_samesite: str
    cookie_domain: str | None


class AuthService:
    def __init__(self, db_path: str, config: AuthConfig) -> None:
        self.db_path = db_path
        self.config = config

    @staticmethod
    def _now_utc() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _b64url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    @staticmethod
    def _b64url_decode(data: str) -> bytes:
        padding = "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode((data + padding).encode("ascii"))

    @staticmethod
    def _json_dumps(value: Dict[str, Any]) -> bytes:
        return json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")

    def _sign(self, data: bytes) -> str:
        digest = hmac.new(self.config.jwt_secret.encode("utf-8"), data, hashlib.sha256).digest()
        return self._b64url_encode(digest)

    def _encode_jwt(self, payload: Dict[str, Any]) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        header_part = self._b64url_encode(self._json_dumps(header))
        payload_part = self._b64url_encode(self._json_dumps(payload))
        message = f"{header_part}.{payload_part}".encode("ascii")
        signature = self._sign(message)
        return f"{header_part}.{payload_part}.{signature}"

    def _decode_jwt(self, token: str) -> Dict[str, Any]:
        try:
            header_part, payload_part, signature_part = token.split(".", 2)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

        expected_sig = self._sign(f"{header_part}.{payload_part}".encode("ascii"))
        if not hmac.compare_digest(signature_part, expected_sig):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature")

        try:
            payload_raw = self._b64url_decode(payload_part)
            payload = json.loads(payload_raw.decode("utf-8"))
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload") from exc

        exp = payload.get("exp")
        if not isinstance(exp, int) or exp <= int(self._now_utc().timestamp()):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

        return payload

    @staticmethod
    def _hash_password(password: str, salt: bytes | None = None) -> str:
        salt_bytes = salt or os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 120_000)
        return f"pbkdf2_sha256$120000${base64.b64encode(salt_bytes).decode('ascii')}${base64.b64encode(digest).decode('ascii')}"

    @staticmethod
    def _verify_password(password: str, encoded_hash: str) -> bool:
        try:
            algorithm, rounds, salt_b64, hash_b64 = encoded_hash.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            rounds_i = int(rounds)
            salt = base64.b64decode(salt_b64.encode("ascii"))
            expected = base64.b64decode(hash_b64.encode("ascii"))
        except Exception:
            return False

        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds_i)
        return hmac.compare_digest(actual, expected)

    def _build_user_public(self, row: Any) -> UserPublic:
        return UserPublic(id=row["id"], email=row["email"], role=row["role"])

    def _create_access_token(self, user: UserPublic) -> str:
        now_ts = int(self._now_utc().timestamp())
        payload = {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "typ": "access",
            "iat": now_ts,
            "exp": now_ts + self.config.access_ttl_sec,
        }
        return self._encode_jwt(payload)

    def _create_refresh_token(self, user: UserPublic, token_jti: str) -> str:
        now_ts = int(self._now_utc().timestamp())
        payload = {
            "sub": user.id,
            "typ": "refresh",
            "jti": token_jti,
            "iat": now_ts,
            "exp": now_ts + self.config.refresh_ttl_sec,
        }
        return self._encode_jwt(payload)

    def _set_cookie(self, response: Response, key: str, value: str, max_age: int) -> None:
        response.set_cookie(
            key=key,
            value=value,
            httponly=True,
            secure=self.config.cookie_secure,
            samesite=self.config.cookie_samesite,
            domain=self.config.cookie_domain,
            path="/",
            max_age=max_age,
        )

    def set_auth_cookies(self, response: Response, access_token: str, refresh_token: str) -> None:
        self._set_cookie(response, ACCESS_COOKIE_NAME, access_token, self.config.access_ttl_sec)
        self._set_cookie(response, REFRESH_COOKIE_NAME, refresh_token, self.config.refresh_ttl_sec)

    def clear_auth_cookies(self, response: Response) -> None:
        response.delete_cookie(
            ACCESS_COOKIE_NAME,
            path="/",
            domain=self.config.cookie_domain,
        )
        response.delete_cookie(
            REFRESH_COOKIE_NAME,
            path="/",
            domain=self.config.cookie_domain,
        )

    def bootstrap_admin(self, admin_email: str | None, admin_password: str | None) -> None:
        with get_connection(self.db_path) as conn:
            count_row = conn.execute("SELECT COUNT(*) AS cnt FROM users").fetchone()
            user_count = int(count_row["cnt"]) if count_row else 0

            if user_count > 0:
                return

            if not admin_email and not admin_password:
                return

            if not admin_email or not admin_password:
                raise RuntimeError(
                    "No users found. Set AUTH_ADMIN_EMAIL and AUTH_ADMIN_PASSWORD before starting cloud server."
                )

            conn.execute(
                """
                INSERT INTO users (id, email, password_hash, role, created_at, updated_at)
                VALUES (?, ?, ?, 'admin', ?, ?)
                """,
                (
                    str(uuid4()),
                    admin_email.strip().lower(),
                    self._hash_password(admin_password),
                    self._now_utc().isoformat(),
                    self._now_utc().isoformat(),
                ),
            )
            conn.commit()

    def authenticate(self, email: str, password: str) -> UserPublic:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT id, email, password_hash, role FROM users WHERE email = ?",
                (email.strip().lower(),),
            ).fetchone()

        if row is None or not self._verify_password(password, row["password_hash"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

        return self._build_user_public(row)

    def register_user(self, email: str, password: str, role: UserRole) -> UserPublic:
        normalized_email = email.strip().lower()
        if not normalized_email:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Email is required")
        if len(password) < 8:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password must be at least 8 characters",
            )
        if role not in {"admin", "operator"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid role",
            )

        user_id = str(uuid4())
        now = self._now_utc().isoformat()

        with get_connection(self.db_path) as conn:
            existing_user = conn.execute(
                "SELECT id FROM users WHERE email = ?",
                (normalized_email,),
            ).fetchone()
            if existing_user is not None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

            try:
                conn.execute(
                    """
                    INSERT INTO users (id, email, password_hash, role, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        normalized_email,
                        self._hash_password(password),
                        role,
                        now,
                        now,
                    ),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists") from exc

        return UserPublic(id=user_id, email=normalized_email, role=role)

    def issue_tokens(self, user: UserPublic) -> tuple[str, str]:
        token_jti = str(uuid4())
        access_token = self._create_access_token(user)
        refresh_token = self._create_refresh_token(user, token_jti)
        now = self._now_utc()
        expires_at = now + timedelta(seconds=self.config.refresh_ttl_sec)

        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO auth_refresh_sessions (id, user_id, token_jti, expires_at, revoked_at, created_at, last_used_at)
                VALUES (?, ?, ?, ?, NULL, ?, ?)
                """,
                (
                    str(uuid4()),
                    user.id,
                    token_jti,
                    expires_at.isoformat(),
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            conn.commit()

        return access_token, refresh_token

    def _load_user_by_id(self, user_id: str) -> UserPublic:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT id, email, role FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()

        if row is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        return self._build_user_public(row)

    def get_user_from_access_token(self, token: str) -> UserPublic:
        payload = self._decode_jwt(token)
        if payload.get("typ") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = payload.get("sub")
        if not isinstance(user_id, str):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
        return self._load_user_by_id(user_id)

    def refresh(self, refresh_token: str) -> tuple[UserPublic, str, str]:
        payload = self._decode_jwt(refresh_token)
        if payload.get("typ") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        token_jti = payload.get("jti")
        user_id = payload.get("sub")
        if not isinstance(token_jti, str) or not isinstance(user_id, str):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh payload")

        now = self._now_utc()

        with get_connection(self.db_path) as conn:
            session = conn.execute(
                """
                SELECT id, user_id, expires_at, revoked_at
                FROM auth_refresh_sessions
                WHERE token_jti = ?
                """,
                (token_jti,),
            ).fetchone()

            if session is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session not found")

            if session["revoked_at"] is not None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session revoked")

            try:
                expires_at = datetime.fromisoformat(session["expires_at"])
            except Exception as exc:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh expiry") from exc

            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)

            if expires_at <= now:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

            conn.execute(
                "UPDATE auth_refresh_sessions SET revoked_at = ?, last_used_at = ? WHERE id = ?",
                (now.isoformat(), now.isoformat(), session["id"]),
            )
            conn.commit()

        user = self._load_user_by_id(user_id)
        new_access, new_refresh = self.issue_tokens(user)
        return user, new_access, new_refresh

    def revoke_by_refresh_token(self, refresh_token: str) -> None:
        try:
            payload = self._decode_jwt(refresh_token)
        except HTTPException:
            return

        token_jti = payload.get("jti")
        if not isinstance(token_jti, str):
            return

        now = self._now_utc().isoformat()
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                UPDATE auth_refresh_sessions
                SET revoked_at = COALESCE(revoked_at, ?), last_used_at = ?
                WHERE token_jti = ?
                """,
                (now, now, token_jti),
            )
            conn.commit()

    def get_current_user_from_request(self, request: Request) -> UserPublic:
        token: str | None = None

        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip() or None

        if token is None:
            token = request.cookies.get(ACCESS_COOKIE_NAME)

        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        return self.get_user_from_access_token(token)
