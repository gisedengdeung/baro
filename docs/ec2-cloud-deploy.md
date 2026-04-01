# AWS EC2 첫 배포 가이드 (Cloud 백엔드)

## 0) EC2가 무엇인가
- EC2(Elastic Compute Cloud)는 AWS에서 빌려 쓰는 가상 서버다.
- 이 프로젝트 기준 역할:
  - `EC2`: FastAPI Cloud 서버 실행
  - `S3`: 클립 영상 파일 저장소
- 즉, 앱 서버는 EC2에서 돌고, 영상 파일은 S3에 저장된다.

## 1) AWS 콘솔에서 EC2 생성
1. AWS Console -> EC2 -> `Launch instance`
2. AMI: `Ubuntu Server 24.04 LTS`
3. Instance type: `t3.micro` (학습용)
4. Key pair: 새로 생성해서 `.pem` 다운로드
5. Network:
   - Public IPv4 활성화
   - Security Group 인바운드:
     - `22` (SSH, 내 IP만)
     - `80` (HTTP)
     - `443` (HTTPS, 나중에 사용)
     - `8000` (초기 확인용, 최종에는 닫기 권장)
6. Launch 후 Public IPv4 확인

## 2) EC2 접속
로컬 터미널에서:

```bash
chmod 400 <key>.pem
ssh -i <key>.pem ubuntu@<EC2_PUBLIC_IP>
```

## 3) 코드 배치 및 기본 패키지
EC2 내부에서:

```bash
mkdir -p ~/app
cd ~/app
git clone <YOUR_REPO_URL> stop
cd stop
```

자동 설치 스크립트 실행:

```bash
bash scripts/setup_ec2_cloud.sh
```

이 스크립트가 하는 일:
- `git/nginx/python-venv` 설치
- `.venv-cloud` 생성 + `requirements-cloud.txt` 설치
- `systemd` 서비스(`conveyor-guard-cloud`) 등록/시작
- nginx 리버스 프록시 설정

## 4) 환경변수 설정
`.env` 파일 편집:

```bash
cd ~/app/stop
nano .env
```

최소 필수:
- `AWS_ACCESS_KEY`
- `AWS_SECRET_KEY`
- `AUTH_ADMIN_EMAIL`
- `AUTH_ADMIN_PASSWORD`
- `AUTH_JWT_SECRET`
- `LOCAL_DB_PATH=/home/ubuntu/app/stop/cloud/data/cloud.db`

예시는 `.env.cloud.example` 참고.

변경 후 서비스 재시작:

```bash
sudo systemctl restart conveyor-guard-cloud
```

## 5) 동작 확인
EC2 내부:

```bash
curl http://127.0.0.1:8000/
curl -i -X POST http://127.0.0.1:8000/api/edge/clips
```

- `/`는 200 JSON
- `/api/edge/clips`는 폼값 없으므로 422가 정상(라우트 존재 확인)

외부 PC:
- `http://<EC2_PUBLIC_IP>/docs` 접속 확인

로그 확인:

```bash
sudo journalctl -u conveyor-guard-cloud -f
```

## 6) Edge 연동 전환
로컬 `./.env.edge` 수정:

```env
CLOUD_BASE_URL=http://<EC2_PUBLIC_IP>
```

Edge 재시작 후 테스트:
- 이벤트 발생
- EC2 로그에서 `/api/edge/log`, `/api/edge/clips` 요청 확인
- S3 버킷에서 `clips/{edge_id}/{YYYYMMDD}/...` 파일 생성 확인

## 7) 최종 보안 정리(권장)
초기 점검이 끝나면:
1. EC2 보안그룹에서 `8000` 인바운드 제거
2. FastAPI는 `127.0.0.1:8000` 유지 + nginx(80/443)만 외부 노출
3. 도메인 연결 후 certbot으로 HTTPS 적용

## 8) 자주 막히는 포인트
- `ModuleNotFoundError`:
  - `pip install -r requirements-cloud.txt` 다시 실행
- `/api/edge/clips` 404:
  - 다른 서버 프로세스 떠 있는지 확인, 서비스 재시작
- S3 업로드 실패:
  - `.env`의 AWS 키 확인
  - IAM 권한(`s3:PutObject`) 확인
