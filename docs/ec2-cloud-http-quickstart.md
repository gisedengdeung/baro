# EC2 HTTP Quickstart

도메인 없이 EC2 public IP + HTTP로 먼저 띄우는 가장 짧은 절차입니다.

## 1. AWS에서 할 일

- Ubuntu 24.04 EC2 1대 생성
- 보안그룹 오픈:
  - `22/tcp`: 내 IP
  - `80/tcp`: 공개
  - `3478/tcp`, `3478/udp`: 공개
  - `49160-49200/udp`: 공개
- S3 버킷 생성
- EC2 IAM Role에 S3 접근 권한 연결

## 2. EC2 접속 후

```bash
mkdir -p ~/app
cd ~/app
git clone <YOUR_REPO_URL> stop
cd stop
bash scripts/setup_ec2_docker.sh
```

## 3. `.env.prod` 작성

```bash
cp .env.prod.example .env.prod
nano .env.prod
```

반드시 채울 값:
- `EDGE_SHARED_SECRET`
- `AUTH_ADMIN_EMAIL`
- `AUTH_ADMIN_PASSWORD`
- `AUTH_JWT_SECRET`
- `AWS_S3_BUCKET`
- `TURN_PUBLIC_IP`
- `TURN_REALM`
- `TURN_USER`
- `TURN_PASSWORD`

임시 HTTP 운영이면 아래처럼 둡니다.

```env
CADDY_DOMAIN=:80
TURN_PUBLIC_IP=<EC2_PUBLIC_IP>
TURN_REALM=<EC2_PUBLIC_IP>
REACT_APP_WEBRTC_ICE_SERVERS_JSON=[{"urls":["stun:<EC2_PUBLIC_IP>:3478","turn:<EC2_PUBLIC_IP>:3478?transport=udp","turn:<EC2_PUBLIC_IP>:3478?transport=tcp"],"username":"turnuser","credential":"turnpassword"}]
```

## 4. 실행

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

## 5. 확인

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
docker compose --env-file .env.prod -f docker-compose.prod.yml logs --tail=200 cloud caddy coturn
```

브라우저:
- `http://<EC2_PUBLIC_IP>/`

Edge:
- `CLOUD_BASE_URL=http://<EC2_PUBLIC_IP>`
- `EDGE_SHARED_SECRET=<same value as cloud>`

## 6. 통과 기준

- 로그인 가능
- `/api/control/status` 응답 정상
- `/ws/logs` 연결 정상
- Edge heartbeat가 `200`
- WebRTC offer/answer/ice가 교환됨
- 필요 시 relay candidate가 보임
