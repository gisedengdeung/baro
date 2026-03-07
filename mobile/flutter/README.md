# STOP Mobile Flutter App

모노레포 기준 Flutter 앱 구현 위치는 `mobile/flutter/app` 입니다.

## 현재 상태
- MVP 앱 코드(로그인/사건 목록/상세/대피 경로/설정)가 `mobile/flutter/app/lib`에 구현되어 있습니다.
- 이 개발환경에는 Flutter SDK가 없어 `flutter create`/`flutter run`은 아직 실행 검증하지 못했습니다.

## 디렉터리
- `mobile/flutter/app/pubspec.yaml`
- `mobile/flutter/app/lib/features/auth`
- `mobile/flutter/app/lib/features/incidents`
- `mobile/flutter/app/lib/features/evacuation`
- `mobile/flutter/app/lib/features/settings`
- `scripts/setup_mobile.sh`
- `scripts/run_mobile.sh`
- `scripts/configure_mobile_local_http.sh`

## 선행 설치
1. Flutter SDK 설치
2. Android Studio/Xcode 설정

확인:
```bash
flutter --version
```

## 첫 실행 절차
1. Cloud API 실행
```bash
./scripts/run_cloud.sh
```

2. Flutter 의존성 설치 + 플랫폼 생성 + 로컬 HTTP 허용 설정
```bash
./scripts/setup_mobile.sh
```

3. 앱 실행
```bash
# Android emulator
./scripts/run_mobile.sh --platform android --api-base-url http://10.0.2.2:8000

# iOS simulator
./scripts/run_mobile.sh --platform ios --api-base-url http://127.0.0.1:8000
```

## API_BASE_URL 규칙
- Android emulator에서 host 머신 `localhost`는 `10.0.2.2`
- iOS simulator는 `127.0.0.1` 사용
- 앱은 `--dart-define API_BASE_URL=...` 값으로 Cloud API를 호출합니다.

## 구현된 화면
1. LoginScreen
- `POST /api/auth/login`
- access token 저장 후 incidents로 이동

2. IncidentListScreen
- `GET /api/incidents`

3. IncidentDetailScreen
- `GET /api/incidents/{incident_id}`
- 스냅샷: `GET /api/incidents/{incident_id}/snapshot`

4. EvacuationRouteScreen
- `GET /api/evacuation/route?edge_id=&zone_id=&incident_type=`
- Canvas(CustomPainter) 경로 렌더링

5. SettingsScreen
- 수동 `fcm_token` 입력
- `POST /api/mobile/devices/register`

## 인증 동작
- 보호 API는 `Authorization: Bearer <access_token>` 사용
- 서버가 `401` 응답하면 세션을 정리하고 다시 로그인하도록 유도합니다.
- refresh-token 자동 갱신은 현재 범위에서 제외되어 있습니다.

## 다음 단계
1. Firebase Messaging 실제 토큰 연동
2. push 수신/딥링크 연결
3. refresh-token 모바일 전용 갱신 API 도입
