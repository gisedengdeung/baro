from __future__ import annotations

import hashlib
import hmac


def sha256_hexdigest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def build_signing_payload(
    edge_id: str,
    timestamp: str,
    method: str,
    path: str,
    query: str,
    body_hash: str,
) -> bytes:
    normalized_method = method.upper().strip()
    normalized_path = path or "/"
    normalized_query = query or ""
    return "\n".join(
        [
            edge_id.strip(),
            timestamp.strip(),
            normalized_method,
            normalized_path,
            normalized_query,
            body_hash.strip(),
        ]
    ).encode("utf-8")


def sign_edge_request(
    *,
    shared_secret: str,
    edge_id: str,
    timestamp: str,
    method: str,
    path: str,
    query: str,
    body: bytes,
) -> str:
    body_hash = sha256_hexdigest(body)
    payload = build_signing_payload(
        edge_id=edge_id,
        timestamp=timestamp,
        method=method,
        path=path,
        query=query,
        body_hash=body_hash,
    )
    return hmac.new(shared_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def verify_edge_signature(
    *,
    provided_signature: str,
    shared_secret: str,
    edge_id: str,
    timestamp: str,
    method: str,
    path: str,
    query: str,
    body: bytes,
) -> bool:
    expected = sign_edge_request(
        shared_secret=shared_secret,
        edge_id=edge_id,
        timestamp=timestamp,
        method=method,
        path=path,
        query=query,
        body=body,
    )
    return hmac.compare_digest(provided_signature, expected)
