from __future__ import annotations

import hashlib
import hmac
import time

EDGE_ID_HEADER = "X-Edge-Id"
EDGE_TIMESTAMP_HEADER = "X-Edge-Timestamp"
EDGE_SIGNATURE_HEADER = "X-Edge-Signature"


def normalize_edge_id(edge_id: str) -> str:
    return edge_id.strip()


def build_request_target(path: str, query_string: str | None = None) -> str:
    normalized_path = path if path.startswith("/") else f"/{path}"
    normalized_query = (query_string or "").lstrip("?")
    if not normalized_query:
        return normalized_path
    return f"{normalized_path}?{normalized_query}"


def build_signature_payload(
    method: str,
    request_target: str,
    edge_id: str,
    timestamp: int,
) -> bytes:
    return "\n".join(
        [
            method.upper(),
            build_request_target(request_target),
            normalize_edge_id(edge_id),
            str(int(timestamp)),
        ]
    ).encode("utf-8")


def sign_edge_request(
    shared_secret: str,
    method: str,
    request_target: str,
    edge_id: str,
    timestamp: int,
) -> str:
    payload = build_signature_payload(method, request_target, edge_id, timestamp)
    return hmac.new(
        shared_secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()


def build_edge_auth_headers(
    shared_secret: str,
    method: str,
    request_target: str,
    edge_id: str,
    timestamp: int | None = None,
) -> dict[str, str]:
    issued_at = int(time.time()) if timestamp is None else int(timestamp)
    normalized_edge_id = normalize_edge_id(edge_id)
    return {
        EDGE_ID_HEADER: normalized_edge_id,
        EDGE_TIMESTAMP_HEADER: str(issued_at),
        EDGE_SIGNATURE_HEADER: sign_edge_request(
            shared_secret=shared_secret,
            method=method,
            request_target=request_target,
            edge_id=normalized_edge_id,
            timestamp=issued_at,
        ),
    }


def verify_edge_request_signature(
    shared_secret: str,
    method: str,
    request_target: str,
    edge_id: str,
    timestamp: int,
    signature: str,
) -> bool:
    expected = sign_edge_request(
        shared_secret=shared_secret,
        method=method,
        request_target=request_target,
        edge_id=edge_id,
        timestamp=timestamp,
    )
    return hmac.compare_digest(signature, expected)
