# EC2 Cloud 연결 표준 가이드 (팀원용)

이 문서는 **팀원이 이미 로컬 Edge/Frontend 기본 세팅을 끝낸 상태**를 기준으로, EC2 Cloud 서버에 연결해 사용하는 절차를 정리합니다.

## 1. 전제 조건

- Cloud 서버 주소(예시): `http://43.201.98.95`
- 팀 레포 최신 코드 pull 가능
- 로컬에서 Frontend(`localhost:3000`)와 Edge 실행 가능

참고:
- `setup_ec2_cloud.sh`, `deploy/ec2/cloud.service`, `deploy/ec2/nginx-cloud.conf`는 **EC2 서버 배포용 파일**입니다.
- 팀원이 로컬에서 Front/Edge만 쓰는 경우, 위 3개를 실행할 필요는 없습니다.

## 2. 팀원 공통 최소 절차

### 2.1 최신 코드 반영

```bash
git pull
```

### 2.2 Edge 대상 Cloud 주소 설정

프로젝트 루트의 `.env.edge` 파일에서 아래 값 확인/수정:

```env
CLOUD_BASE_URL=http://43.201.98.95
EDGE_ID=edge-default
```

### 2.3 Front API 주소 설정

파일: `frontend/simple-video-viewer/.env`

로그인/세션 안정성을 위해 아래 값 사용 권장:

```env
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_WS_BASE_URL=ws://localhost:8000
REACT_APP_EDGE_ID=edge-default
```

## 3. SSH 터널 실행 (중요)

`localhost:8000` 방식이면 터널이 반드시 필요합니다.

Windows PowerShell에서 실행:

```powershell
ssh -i "$env:USERPROFILE\.ssh\stop-ec2-key.pem" -L 8000:127.0.0.1:80 ubuntu@43.201.98.95
```

주의:
- 터널 창을 닫으면 연결이 끊깁니다.
- 끊을 때는 `Ctrl + C` 또는 `exit`.

## 4. Frontend/Edge 실행

### 4.1 Frontend

```bash
cd frontend/simple-video-viewer
npm start
```

브라우저는 `http://localhost:3000`으로 열리는 것이 정상입니다.

### 4.2 Edge

예시:

```bash
python -m edge.main --camera 0 --serial COM3 --cloud-url http://43.201.98.95 --edge-id edge-default
```

하드웨어 없이 테스트 시:

```bash
python -m edge.main --camera 0 --serial COM3 --cloud-url http://43.201.98.95 --edge-id edge-default --serial-mock
```

## 5. 정상 동작 체크리스트

- `http://43.201.98.95/docs` 접속 가능
- Front 로그인 후 Dashboard 이동 가능
- Edge 실행 시 heartbeat 전송
- EC2 서버 로그에서 아래 요청이 `200` 확인:
  - `/api/edge/heartbeat`
  - `/api/edge/commands`
  - `/api/edge/zones`

## 6. 자주 발생하는 문제

### 6.1 로그인 후 메인(`/`)으로 튕김

원인:
- 터널 미실행 또는 터널 끊김

조치:
- SSH 터널 다시 실행 후 Front 재시도

### 6.2 회원가입 실패 문구

먼저 DevTools Network에서 `POST /api/auth/signup` 상태코드를 확인:
- `200`: 가입 성공(후속 요청 실패로 UI 문구만 실패일 수 있음)
- `409`: 이미 존재하는 이메일
- `422`: 입력 형식 오류(이메일/비밀번호)

### 6.3 클립 업로드 실패 (`/api/edge/clips`)

대부분 EC2 `.env`의 AWS 키 누락/오류:
- `AWS_ACCESS_KEY`
- `AWS_SECRET_KEY`

## 7. 보안 권장사항

- `.env`, `.env.edge`는 Git에 커밋 금지
- SSH 22포트는 `0.0.0.0/0` 대신 팀원 IP로 제한
- AWS 키 노출 의심 시 즉시 rotate
- 장기적으로 IAM Role(EC2 Instance Profile) 전환 권장
