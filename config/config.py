from pathlib import Path
from typing import Dict, Any

# 프로젝트 루트 디렉토리
# 이 파일의 위치를 기준으로 상위 디렉토리를 프로젝트 루트로 가정합니다.
# config/config.py -> smart-safety-system/
ROOT_DIR = Path(__file__).parent.parent

def get_config() -> Dict[str, Any]:
    """
    시스템 전체에서 사용할 중앙 설정 객체를 반환합니다.
    모든 경로는 프로젝트 루트를 기준으로 설정됩니다.
    """
    config = {
        "input": {
            "camera_index": 3,  # 실제 사용할 카메라 인덱스
            "mock_mode": False # True일 경우, 실제 카메라 대신 비디오 파일을 사용
        },
        "detection": {
            "person_detector": {
                "model_path": ROOT_DIR / "models" / "yolov8n.pt"
            },
            "pose_detector": {
                "pose_model_path": ROOT_DIR / "models" / "yolov8n-pose.pt"
            }
        },
        "control": {
            "mock_mode": False # True일 경우, 실제 시리얼 통신 대신 로그만 출력
        },
        "services": {
            "firebase_credential_path": ROOT_DIR / "config" / "firebase_credential.json"
        },
        "serial":{
            "port": "/dev/tty.usbserial-A5069RR4",
            "mock_mode": False,
            "baud_rate": 9600
        }
    }
    return config
