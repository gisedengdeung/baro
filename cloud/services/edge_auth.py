from __future__ import annotations

import time

from fastapi import HTTPException, Request, status

from shared.edge_auth import (
    EDGE_ID_HEADER,
    EDGE_SIGNATURE_HEADER,
    EDGE_TIMESTAMP_HEADER,
    build_request_target,
    normalize_edge_id,
    verify_edge_request_signature,
)


class EdgeAuthService:
    def __init__(self, shared_secret: str, max_age_sec: int = 30) -> None:
        self.shared_secret = shared_secret
        self.max_age_sec = max_age_sec

    def authenticate(self, request: Request) -> str:
        edge_id = normalize_edge_id(request.headers.get(EDGE_ID_HEADER, ""))
        timestamp_raw = request.headers.get(EDGE_TIMESTAMP_HEADER, "").strip()
        signature = request.headers.get(EDGE_SIGNATURE_HEADER, "").strip()

        if not edge_id or not timestamp_raw or not signature:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing edge authentication headers.",
            )

        try:
            timestamp = int(timestamp_raw)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid edge request timestamp.",
            ) from exc

        now = int(time.time())
        if abs(now - timestamp) > self.max_age_sec:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Expired edge request signature.",
            )

        request_target = build_request_target(request.url.path, request.url.query)
        if not verify_edge_request_signature(
            shared_secret=self.shared_secret,
            method=request.method,
            request_target=request_target,
            edge_id=edge_id,
            timestamp=timestamp,
            signature=signature,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid edge request signature.",
            )

        return edge_id


def ensure_authenticated_edge_id(
    authenticated_edge_id: str,
    declared_edge_id: str | None,
) -> str:
    normalized_authenticated = normalize_edge_id(authenticated_edge_id)
    normalized_declared = normalize_edge_id(declared_edge_id or normalized_authenticated)
    if normalized_authenticated != normalized_declared:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated edge does not match request edge_id.",
        )
    return normalized_authenticated
