"""
WebSocket edge 필터링 테스트 스크립트

테스트 항목:
  1. edge-default 채널 구독 시 edge-default heartbeat만 수신
  2. edge-other heartbeat 전송 시 edge-default 구독자에게 미도달
  3. edge_id 없이 구독 시 모든 edge 메시지 수신

실행 방법:
  1. cloud 서버 실행
  2. python tests/test_ws_edge_filter.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
import websockets

from shared.edge_auth import build_edge_auth_headers

# ─── 설정 ─────────────────────────────────────────
CLOUD_URL   = "http://localhost:8000"
WS_URL      = "ws://localhost:8000"
EMAIL       = "test@test.com"
PASSWORD    = "test1234"
EDGE_SECRET = "여기에 .env.cloud의 EDGE_SHARED_SECRET 값 입력"  # .env.cloud의 EDGE_SHARED_SECRET
# ──────────────────────────────────────────────────


def login() -> str:
    """로그인 후 쿠키 헤더 문자열 반환."""
    resp = httpx.post(
        f"{CLOUD_URL}/api/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
    )
    resp.raise_for_status()
    return "; ".join(f"{k}={v}" for k, v in resp.cookies.items())


def send_heartbeat(edge_id: str) -> bool:
    """edge heartbeat POST 전송. 성공 시 True."""
    path = "/api/edge/heartbeat"
    headers = build_edge_auth_headers(
        shared_secret=EDGE_SECRET,
        method="POST",
        request_target="/api/edge/heartbeat",
        edge_id=edge_id,
    )
    payload = {
        "edge_id": edge_id,
        "operation_mode": "AUTOMATIC",
        "conveyor_is_on": True,
        "conveyor_speed": 120,
        "risk_level": "LOW",
        "is_locked": False,
        "test_is_active": False,
        "test_speed": 0,
    }
    try:
        resp = httpx.post(f"{CLOUD_URL}{path}", json=payload, headers=headers)
        resp.raise_for_status()
        return True
    except httpx.HTTPStatusError as e:
        print(f"  [heartbeat 실패] edge={edge_id} status={e.response.status_code} body={e.response.text}")
        return False


async def collect_messages(
    cookie: str,
    edge_id: str | None,
    duration_sec: float,
) -> List[dict]:
    """WebSocket 구독 후 duration_sec 동안 수신한 메시지 목록 반환."""
    url = f"{WS_URL}/ws/logs"
    if edge_id:
        url += f"?edge_id={edge_id}"

    received = []
    try:
        async with websockets.connect(url, additional_headers={"Cookie": cookie}) as ws:
            async def _receive():
                async for msg in ws:
                    received.append(json.loads(msg))

            recv_task = asyncio.create_task(_receive())
            await asyncio.sleep(duration_sec)
            recv_task.cancel()
    except Exception as e:
        print(f"  [WS 오류] {e}")
    return received


async def run_test(cookie: str, name: str, subscribe_edge: str | None, heartbeat_edge: str) -> None:
    print(f"\n{'='*55}")
    print(f"테스트: {name}")
    print(f"  구독 채널: {'logs:' + subscribe_edge if subscribe_edge else 'logs (전체)'}")
    print(f"  heartbeat 전송 edge: {heartbeat_edge}")
    print(f"{'='*55}")

    async def send_loop():
        await asyncio.sleep(0.5)
        for i in range(3):
            ok = send_heartbeat(heartbeat_edge)
            if ok:
                print(f"  → heartbeat #{i+1} 전송 완료 (edge={heartbeat_edge})")
            await asyncio.sleep(1)

    messages_task = asyncio.create_task(
        collect_messages(cookie, subscribe_edge, duration_sec=4)
    )
    await send_loop()
    messages = await messages_task

    status_updates = [m for m in messages if m.get("type") == "STATUS_UPDATE"]
    print(f"\n  수신된 STATUS_UPDATE 수: {len(status_updates)}")

    for msg in status_updates:
        print(f"    - {msg}")

    if subscribe_edge and subscribe_edge != heartbeat_edge:
        if len(status_updates) == 0:
            print(f"\n  ✅ PASS: {heartbeat_edge} 메시지가 {subscribe_edge} 구독자에게 도달하지 않음")
        else:
            print(f"\n  ❌ FAIL: 다른 edge의 메시지가 섞여 들어옴")
    elif subscribe_edge == heartbeat_edge:
        if len(status_updates) > 0:
            print(f"\n  ✅ PASS: {heartbeat_edge} 메시지 정상 수신")
        else:
            print(f"\n  ❌ FAIL: 메시지를 수신하지 못함")
    else:
        print(f"\n  ℹ️  전체 구독 — 수신 메시지 수: {len(status_updates)}")


async def main():
    print("로그인 중...")
    cookie = login()
    print("로그인 완료\n")

    # 테스트 1: edge-default 구독 → edge-default heartbeat → 수신 돼야 함
    await run_test(
        cookie,
        name="[1] 같은 edge 구독 → 수신 확인",
        subscribe_edge="edge-default",
        heartbeat_edge="edge-default",
    )

    # 테스트 2: edge-default 구독 → edge-other heartbeat → 수신 안 돼야 함
    await run_test(
        cookie,
        name="[2] 다른 edge 구독 → 격리 확인",
        subscribe_edge="edge-default",
        heartbeat_edge="edge-other",
    )

    # 테스트 3: edge_id 없이 전체 구독 → 모든 edge 수신
    await run_test(
        cookie,
        name="[3] 전체 구독 → 모든 edge 수신 확인",
        subscribe_edge=None,
        heartbeat_edge="edge-default",
    )


if __name__ == "__main__":
    asyncio.run(main())
