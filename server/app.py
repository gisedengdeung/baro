"""레거시 호환 엔트리포인트.

기존 실행 경로(`server.app:app`)를 유지하기 위해 Cloud 앱을 재노출합니다.
"""

from cloud.main import app
