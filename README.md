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

## Setup (1회/필요시)

실행 전에 환경 준비가 필요할 때 아래 스크립트를 사용하세요.

```bash
./scripts/setup_cloud.sh
./scripts/setup_edge.sh
./scripts/setup_frontend.sh
```

각 스크립트가 하는 일:
- `setup_cloud.sh`: `.venv-cloud` 가상환경 생성/재사용 + `requirements-cloud.txt` 설치
- `setup_edge.sh`: `.venv-edge` 가상환경 생성/재사용 + `requirements-edge.txt` 설치 + `.env.edge` 자동 생성(없을 때만)
- `setup_frontend.sh`: `frontend/simple-video-viewer`에서 `npm install` + `.env` 자동 생성(없을 때만)

원칙:
- setup 스크립트: 최초 1회 또는 의존성 변경 시 실행
- run 스크립트: 서버/앱을 실행할 때마다 사용

## 실행

터미널 3개를 동시에 띄워서 실행하는 기준입니다.

```bash
./scripts/setup_cloud.sh
./scripts/setup_edge.sh
./scripts/setup_frontend.sh
```

참고: `setup_edge.sh`에서 Python 버전 문제가 나면 아래처럼 실행하세요.

```bash
./scripts/setup_edge.sh --python python3.11
```

### 1) 터미널 A: Cloud 실행

초기 실행(사용자 테이블이 비어 있을 때)은 관리자 계정 환경 변수가 필요합니다.

```bash
export AUTH_ADMIN_EMAIL=admin@example.com
export AUTH_ADMIN_PASSWORD='ChangeMe123!'
```

```bash
cd <repo-root>   # 예: /Users/Barcy/BarcyHub/Dev/workspace-barcy/team-project/stop
source .venv-cloud/bin/activate
./scripts/run_cloud.sh
```

정상이면 `http://localhost:8000`에서 서버가 뜹니다.

WebSocket 관련 의존성(`websockets`, `wsproto`)이 추가되었으므로,
기존 가상환경을 쓰는 경우 반드시 위 `pip install -r requirements-cloud.txt`를 다시 실행한 뒤 서버를 재기동하세요.

### 2) 터미널 B: Edge 실행

```bash
cd <repo-root>
source .venv-edge/bin/activate
./scripts/run_edge.sh
```

Edge에서 자주 나는 오류 대응:

```bash
EDGE_FALL_MODEL_PATH=edge/models/yolov8n.pt ./scripts/run_edge.sh
```

```bash
EDGE_SERIAL_MOCK=true ./scripts/run_edge.sh
```

```bash
EDGE_SERIAL_MOCK=true EDGE_FALL_MODEL_PATH=edge/models/yolov8n.pt ./scripts/run_edge.sh
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

### 3) 터미널 C: Frontend 실행

```bash
cd frontend/simple-video-viewer
npm start
```

중요: `npm start`는 반드시 `frontend/simple-video-viewer` 폴더 안에서 실행해야 합니다.

기본 개발 서버: `http://localhost:3000`

### 4) 접속 확인

- 브라우저: `http://localhost:3000`
- Frontend가 Cloud API(`http://localhost:8000`)를 호출하면 연결이 정상입니다.

## 환경 변수

### Cloud

- `CLOUD_CORS_ALLOW_ORIGINS` (기본: `http://localhost:3000`)
- `LOCAL_DB_PATH` (기본: `cloud/data/cloud.db`)
- `SIGNALING_OFFER_TTL_SEC` (기본: `30`)
- `SIGNALING_ANSWER_TTL_SEC` (기본: `30`)
- `SIGNALING_ICE_TTL_SEC` (기본: `20`)
- `AUTH_ADMIN_EMAIL` (초기 관리자 이메일, 최초 부팅 필수)
- `AUTH_ADMIN_PASSWORD` (초기 관리자 비밀번호, 최초 부팅 필수)
- `AUTH_JWT_SECRET` (기본: `dev-only-change-this-secret`)
- `AUTH_ACCESS_TTL_SEC` (기본: `900`)
- `AUTH_REFRESH_TTL_SEC` (기본: `604800`)
- `AUTH_COOKIE_SECURE` (기본: `false`)
- `AUTH_COOKIE_SAMESITE` (기본: `lax`)
- `AUTH_COOKIE_DOMAIN` (선택)
- `CLIP_STORAGE_DIR` (기본: `cloud/data/clips`)
- `CLIP_RETENTION_DAYS` (기본: `7`)
- `CLIP_CLEANUP_INTERVAL_SEC` (기본: `3600`)

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
- `EDGE_PERSON_MODEL_PATH` (기본: `edge/models/yolov8n.pt`)
- `EDGE_FALL_MODEL_PATH` (기본: `edge/models/fall_det_1.pt`)
- 하위 호환: 값이 파일명만(`yolov8n.pt`)일 경우 `edge/models/<파일명>`을 먼저 찾고, 없으면 `<repo-root>/<파일명>`을 fallback으로 확인
- `EDGE_VISUAL_OVERLAY_ENABLED` (기본: `true`)
- `EDGE_DRAW_ZONE_POLYGONS` (기본: `true`)
- `EDGE_DRAW_LABEL_CONFIDENCE` (기본: `false`)
- `EDGE_CLIP_PRE_SECONDS` (기본: `10`)
- `EDGE_CLIP_POST_SECONDS` (기본: `10`)
- `EDGE_CLIP_TARGET_FPS` (기본: `10`)
- `EDGE_CLIP_WIDTH` (기본: `1280`)
- `EDGE_CLIP_HEIGHT` (기본: `720`)
- `EDGE_CLIP_OUTPUT_DIR` (기본: `edge/data/clips`)

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

로그인 정책:
- 회원가입(`signup`)은 비활성화되어 `/login`으로 리다이렉트됩니다.
- 최초 관리자 계정은 Cloud 서버 시작 시 `AUTH_ADMIN_EMAIL`, `AUTH_ADMIN_PASSWORD`로 생성됩니다.

## API 요약

### Cloud -> Edge (Edge polling)

- `GET /api/edge/commands?edge_id=...`
- `GET /api/edge/zones?edge_id=...`

### Edge -> Cloud (push)

- `POST /api/edge/heartbeat`
- `POST /api/edge/log`
- `POST /api/edge/clips`

### 제어/조회(호환 경로)

- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `POST /api/control/start_automatic`
- `POST /api/control/start_maintenance`
- `POST /api/control/stop`
- `POST /api/control/reset`
- `GET /api/control/status`
- `GET /api/logs`
- `GET /api/logs/{id}/clip`
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
