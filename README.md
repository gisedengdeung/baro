# Conveyor Guard (Edge/Cloud 분리 아키텍처)

컨베이어 안전 시스템을 **Edge 서버**(현장)와 **Cloud 서버**(AWS/FastAPI)로 분리한 구조입니다.

## 아키텍처

- `edge/`
  - 카메라/시리얼 입력, 사람/넘어짐/위험구역 감지
  - 위험 평가 + 룰 엔진 + 컨베이어/부저 제어
  - Cloud로 heartbeat/log 전송, 명령/구역 polling
  - WebRTC 송출(영상 전용)
- `cloud/`
  - FastAPI REST + WebSocket + Firestore
  - 제어 명령 큐(Cloud -> Edge)
  - 로그/구역 API, 상태 API, WebRTC signaling relay

## 폴더 구조

```text
edge/
cloud/
shared/
scripts/
requirements-edge.txt
requirements-cloud.txt
Dockerfile.cloud
```

## 실행

### 1) Cloud 서버

```bash
pip install -r requirements-cloud.txt
./scripts/run_cloud.sh
```

기본 포트: `8000`

WebSocket 관련 의존성(`websockets`, `wsproto`)이 추가되었으므로,
기존 가상환경을 쓰는 경우 반드시 위 `pip install -r requirements-cloud.txt`를 다시 실행한 뒤 서버를 재기동하세요.

### 2) Edge 서버

```bash
pip install -r requirements-edge.txt
./scripts/run_edge.sh --camera 0 --serial /dev/ttyUSB0 --cloud-url http://localhost:8000 --edge-id edge-default
```

팀원별 PC 설정(권장):

```bash
cp .env.edge.example .env.edge
```

`.env.edge`에서 아래 2개 값을 각자 PC에 맞게 수정:
- `EDGE_CAMERA_SOURCE`
- `EDGE_SERIAL_PORT`

그리고 실행:

```bash
./scripts/run_edge.sh
```

참고:
- `scripts/run_edge.sh`는 `.env.edge`를 자동으로 로드합니다.
- 필요하면 실행 시 인자로 덮어쓸 수 있습니다. (인자가 우선)
- Windows(PowerShell)는 아래처럼 직접 실행:

```powershell
$env:EDGE_CAMERA_SOURCE="0"
$env:EDGE_SERIAL_PORT="COM3"
$env:CLOUD_BASE_URL="http://localhost:8000"
$env:EDGE_ID="edge-default"
python -m edge.main
```

### 3) Frontend (`simple-video-viewer`)

```bash
cd frontend/simple-video-viewer
npm install
npm start
```

기본 개발 서버: `http://localhost:3000`

## 환경 변수

### Cloud

- `CLOUD_CORS_ALLOW_ORIGINS` (기본: `*`)
- `LOCAL_DB_PATH` (기본: `cloud/data/cloud.db`)
- `SIGNALING_OFFER_TTL_SEC` (기본: `30`)
- `SIGNALING_ANSWER_TTL_SEC` (기본: `30`)
- `SIGNALING_ICE_TTL_SEC` (기본: `20`)

### Edge

- `EDGE_ID` (기본: `edge-default`)
- `CLOUD_BASE_URL` (기본: `http://localhost:8000`)
- `EDGE_CAMERA_SOURCE` (기본: `0`)
- `EDGE_SERIAL_PORT` (기본: `/dev/ttyUSB0`)
- `EDGE_SERIAL_BAUD` (기본: `9600`)
- `EDGE_SERIAL_MOCK` (기본: `false`)
- `EDGE_COMMAND_POLL_INTERVAL` (기본: `0.3`)
- `EDGE_ZONE_POLL_INTERVAL` (기본: `5.0`)
- `EDGE_HEARTBEAT_INTERVAL` (기본: `1.0`)
- `EDGE_PERSON_MODEL_PATH` (기본: `yolov8n.pt`)
- `EDGE_FALL_MODEL_PATH` (기본: `fall_det_1.pt`)
- `EDGE_VISUAL_OVERLAY_ENABLED` (기본: `true`)
- `EDGE_DRAW_ZONE_POLYGONS` (기본: `true`)
- `EDGE_DRAW_LABEL_CONFIDENCE` (기본: `false`)

장치 확인 팁:
- macOS 시리얼 포트: `ls /dev/cu.*`
- Linux 시리얼 포트: `ls /dev/ttyUSB* /dev/ttyACM*`
- 카메라 인덱스 확인(OpenCV):

```bash
python - <<'PY'
import cv2
for i in range(10):
    cap = cv2.VideoCapture(i)
    ok, _ = cap.read()
    print(i, ok)
    cap.release()
PY
```

### Frontend (`frontend/simple-video-viewer/.env`)

- `REACT_APP_API_BASE_URL` (기본: `http://localhost:8000`)
- `REACT_APP_WS_BASE_URL` (기본: `ws://localhost:8000`)
- `REACT_APP_EDGE_ID` (기본: `edge-default`)

예시:

```env
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_WS_BASE_URL=ws://localhost:8000
REACT_APP_EDGE_ID=edge-default
```

## API 요약

### Cloud -> Edge (Edge polling)

- `GET /api/edge/commands?edge_id=...`
- `GET /api/edge/zones?edge_id=...`

### Edge -> Cloud (push)

- `POST /api/edge/heartbeat`
- `POST /api/edge/log`

### 제어/조회(호환 경로)

- `POST /api/control/start_automatic`
- `POST /api/control/start_maintenance`
- `POST /api/control/stop`
- `POST /api/control/reset`
- `GET /api/control/status`
- `GET /api/logs`
- `CRUD /api/zones`
- `GET /api/status`
- `WS /ws/logs`
- `WS /ws/alerts`

### WebRTC signaling

- `POST/GET /api/signaling/offer`
- `POST/GET /api/signaling/answer`
- `POST/GET /api/signaling/ice`

### 영상 경로 변경

- `GET /api/streaming/video_feed`는 **410 Gone** 반환
- 영상은 WebRTC 사용

## 안전 로직 보장 사항

- `risk_evaluator`, `rule_engine`의 핵심 분기 유지
- LOCK 전환 시 전원 차단, RESET 시 잠금 해제 + 전원 차단 유지
- 아두이노 시리얼 명령 유지
  - 전원: `p0`, `p1`
  - 속도: `s0`~`s255`
  - 부저: `b_medium`, `b_high`, `b_critical`, `b_stop`

## Docker (Cloud 전용)

```bash
docker build -f Dockerfile.cloud -t conveyor-guard-cloud .
docker run --rm -p 8000:8000 conveyor-guard-cloud
```

Edge는 하드웨어 접근(카메라/시리얼) 때문에 네이티브 실행을 권장합니다.

## Local DB 운영

- Cloud 서버는 SQLite 파일 DB를 사용합니다.
- 기본 DB 파일: `cloud/data/cloud.db`
- 앱 시작 시 스키마를 자동 초기화합니다.

백업:

```bash
cp cloud/data/cloud.db cloud/data/cloud.db.bak
```

초기화(데이터 삭제 후 재생성):

```bash
rm -f cloud/data/cloud.db
./scripts/run_cloud.sh
```
