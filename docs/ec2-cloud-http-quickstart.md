# EC2 + Docker + Caddy + Tailscale Quickstart

이 문서는 `Cloud + Frontend`를 EC2 1대에 Docker로 배포하고, `Edge -> Cloud`를 Tailscale로 연결하는 가장 짧은 경로를 설명합니다.

## 0) 먼저 이것만 준비

- AWS 계정 + EC2 생성 권한
- 도메인 1개 (`example.com`)와 DNS 수정 권한
- Git 저장소 접근 권한
- Edge 장비에서 Tailscale 사용 가능

## 1) 최소 배포(필수 단계)

### 1-1. EC2 생성

권장 스펙:
- Region: `ap-northeast-2` (Seoul)
- AMI: `Ubuntu Server 24.04 LTS`
- Type: `t3.medium`
- Storage: 루트 `30GiB gp3`

Security Group inbound:
- `22/tcp`: 관리자 공인 IP `/32`
- `80/tcp`: `0.0.0.0/0`
- `443/tcp`: `0.0.0.0/0`
- `8000`은 열지 않음

### 1-2. EC2 접속

```bash
ssh -i <key>.pem ubuntu@<EC2_PUBLIC_IP>
```

### 1-3. 코드 배포 위치 준비

```bash
mkdir -p ~/app && cd ~/app
git clone <YOUR_REPO_URL> stop
cd stop
cp .env.prod.example .env.prod
```

### 1-4. `.env.prod` 필수값 입력

```bash
nano .env.prod
```

최소 필수:
- `CADDY_DOMAIN=<도메인>`
- `ACME_EMAIL=<이메일>`
- `AUTH_ADMIN_EMAIL=<관리자 이메일>`
- `AUTH_ADMIN_PASSWORD=<관리자 비밀번호>`
- `AUTH_JWT_SECRET=<랜덤 긴 문자열>`
- `EDGE_SHARED_SECRET=<랜덤 긴 문자열>`
- `AWS_S3_BUCKET=<private 버킷명>`
- `AWS_REGION=ap-northeast-2`
- `CONVEYOR_DATA_DIR=/srv/conveyor/data`
- `LOCAL_DB_PATH=/app/cloud/data/cloud.db`

랜덤 시크릿 생성 예시:

```bash
openssl rand -hex 32
```

### 1-5. Docker 설치 + 컨테이너 기동

가장 쉬운 방법(프로젝트 스크립트 사용):

```bash
./scripts/setup_ec2_cloud.sh
```

수동 실행이 필요하면:

```bash
sudo docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
sudo docker compose -f docker-compose.prod.yml --env-file .env.prod ps
```

### 1-6. 외부 접속 확인

```bash
curl -I https://<YOUR_DOMAIN>/
curl -I https://<YOUR_DOMAIN>/docs
sudo docker compose -f docker-compose.prod.yml --env-file .env.prod logs --tail=200 cloud
```

정상이면:
- `https://<YOUR_DOMAIN>/` -> Frontend
- `https://<YOUR_DOMAIN>/docs` -> FastAPI 문서

### 1-7. Tailscale 연결 (Edge 경로용)

EC2에서:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
tailscale ip -4
```

출력된 Tailscale IP를 Edge `.env.edge`에 사용:

```env
CLOUD_BASE_URL=http://<TAILSCALE_IP>:8000
EDGE_SHARED_SECRET=<cloud와 동일값>
```

## 2) 선택 단계(운영 강화)

### 2-1. 데이터 전용 EBS 추가 (권장)

권장:
- 데이터 EBS `100GiB gp3` (암호화)
- 마운트: `/srv/conveyor`

예시:

```bash
sudo mkfs -t ext4 /dev/nvme1n1
sudo mkdir -p /srv/conveyor
sudo mount /dev/nvme1n1 /srv/conveyor
sudo chown -R ubuntu:ubuntu /srv/conveyor
UUID=$(sudo blkid -s UUID -o value /dev/nvme1n1)
echo "UUID=$UUID /srv/conveyor ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab
```

### 2-2. UFW 방화벽 (권장)

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow in on tailscale0 to any port 8000 proto tcp
sudo ufw enable
sudo ufw status verbose
```

주의:
- `8000`은 public 인터페이스에서 열지 않음

### 2-3. coturn 직접 운영 시 포트 개방

`docker-compose.prod.yml`의 coturn을 사용할 경우 추가:
- `3478/tcp`, `3478/udp`
- `49160-49200/udp`

### 2-4. S3 권한은 IAM Role 권장

- EC2 인스턴스 프로파일(Role)에 S3 접근 권한 부여
- `.env.prod`의 `AWS_ACCESS_KEY`, `AWS_SECRET_KEY`는 비워두는 방식 권장

## 3) 구조 요약

요청 흐름:
1. 브라우저 -> `443(caddy)` -> `frontend` 또는 `cloud`
2. Edge -> `tailscale0:8000(cloud)`
3. clip 파일 -> `S3 private bucket`
4. clip 조회 -> `presigned URL` redirect

컨테이너 구성:
- `cloud`: FastAPI API + WebSocket + SQLite
- `frontend`: React build 정적 서빙
- `caddy`: TLS 자동발급/갱신 + reverse proxy
- `coturn`: WebRTC relay (옵션)

## 4) 트러블슈팅

### 4-1. `docker compose ps`가 비어 있음

배포 실패 상태입니다. 아래 먼저 확인:

```bash
sudo docker compose -f docker-compose.prod.yml --env-file .env.prod ps -a
sudo docker compose -f docker-compose.prod.yml --env-file .env.prod logs --tail=300
```

### 4-2. Frontend 빌드에서 `npm ci` 실패

증상:
- `package.json and package-lock.json are in sync` 오류

원인:
- 프론트 lockfile 불일치

정석 해결(로컬에서):
1. `frontend/simple-video-viewer`에서 `npm install`
2. 변경된 `package-lock.json` 커밋/푸시
3. EC2에서 `git pull` 후 재배포

### 4-3. 인증서 발급 실패

점검:
- 도메인 A 레코드가 EC2 공인 IP를 가리키는지
- SG에서 `80/443` 허용됐는지
- `CADDY_DOMAIN`, `ACME_EMAIL` 값 오타 없는지
