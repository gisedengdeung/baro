# Conveyor Guard

컨베이어 안전 시스템을 `edge`, `cloud`, `frontend`로 분리한 저장소입니다.

- `edge/`: 카메라/시리얼 입력, 감지 파이프라인, 제어, WebRTC 송출
- `cloud/`: FastAPI API, 인증, 상태/로그/구역 관리, signaling relay, S3 클립 메타 관리
- `frontend/simple-video-viewer/`: 운영용 React UI
- `docker-compose.prod.yml`: EC2 단일 인스턴스 표준 배포

## 현재 배포 기준

- 단일 EC2
- `cloud + frontend + caddy + coturn`
- 브라우저와 Edge는 모두 Caddy `:80`으로 접근
- WebRTC는 signaling은 cloud, TURN은 coturn이 담당
- Edge 요청은 `EDGE_SHARED_SECRET` 기반 HMAC 헤더가 필수

## 로컬 실행

1. 예제 env를 복사하고 필수값을 채웁니다.

```bash
cp .env.cloud.example .env.cloud
cp .env.edge.example .env.edge
```

필수:
- `.env.cloud`: `EDGE_SHARED_SECRET`, `AUTH_ADMIN_EMAIL`, `AUTH_ADMIN_PASSWORD`, `AUTH_JWT_SECRET`, `AWS_S3_BUCKET`
- `.env.edge`: `EDGE_SHARED_SECRET`, `CLOUD_BASE_URL`

2. 의존성을 설치합니다.

```bash
./scripts/setup_cloud.sh
./scripts/setup_edge.sh
./scripts/setup_frontend.sh
```

3. 각 프로세스를 실행합니다.

```bash
source .venv-cloud/bin/activate
./scripts/run_cloud.sh
```

```bash
source .venv-edge/bin/activate
./scripts/run_edge.sh
```

```bash
cd frontend/simple-video-viewer
npm start
```

4. 브라우저에서 `http://localhost:3000`에 접속합니다.

프론트는 same-origin 기본값을 사용합니다. 개발 서버에서는 CRA proxy가 `/api`, `/ws`를 `http://localhost:8000`으로 전달합니다.

## EC2 Docker 배포

빠른 절차는 [docs/ec2-cloud-http-quickstart.md](/Users/Barcy/BarcyHub/Dev/workspace-barcy/team-project/stop/docs/ec2-cloud-http-quickstart.md)를 보면 됩니다.

핵심 명령은 아래 순서입니다.

```bash
bash scripts/setup_ec2_docker.sh
cp .env.prod.example .env.prod
nano .env.prod
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

보안그룹:
- `22/tcp`: 내 IP만
- `80/tcp`: 공개
- `3478/tcp`, `3478/udp`: 공개
- `49160-49200/udp`: 공개

임시 운영 기준:
- `CADDY_DOMAIN=:80`
- `TURN_PUBLIC_IP=<EC2_PUBLIC_IP>`
- `TURN_REALM=<EC2_PUBLIC_IP>`
- `REACT_APP_WEBRTC_ICE_SERVERS_JSON`에도 같은 공인 IP를 넣어야 함

## 꼭 알아둘 환경 변수

Cloud:
- `EDGE_SHARED_SECRET`
- `EDGE_SIGNATURE_TTL_SEC`
- `AUTH_ADMIN_EMAIL`
- `AUTH_ADMIN_PASSWORD`
- `AUTH_JWT_SECRET`
- `AWS_S3_BUCKET`
- `AWS_REGION`
- `CLIP_PRESIGNED_URL_TTL_SEC`

Edge:
- `EDGE_SHARED_SECRET`
- `CLOUD_BASE_URL`
- `EDGE_ID`

Frontend build:
- `REACT_APP_EDGE_ID`
- `REACT_APP_WEBRTC_ICE_SERVERS_JSON`

## WebRTC 확인 기준

- Edge가 `/api/signaling/offer`에 offer를 올린다.
- 브라우저가 로그인 후 offer를 받아 answer와 ICE를 보낸다.
- Edge가 `/api/signaling/answer`, `/api/signaling/ice`를 받아 peer connection을 완성한다.
- 운영망에서는 TURN candidate가 보이는지 확인해야 한다.

## 참고 문서

- [EC2 HTTP Quickstart](/Users/Barcy/BarcyHub/Dev/workspace-barcy/team-project/stop/docs/ec2-cloud-http-quickstart.md)
- [EC2 Deploy Guide](/Users/Barcy/BarcyHub/Dev/workspace-barcy/team-project/stop/docs/ec2-cloud-deploy.md)
