from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import cv2
import numpy as np
import torch
import torch.nn as nn
from loguru import logger
from PIL import Image
from torchvision import models, transforms


class FireDetector:
    def __init__(self, model_name: str = "fire_classifier.pt", conf_threshold: float = 0.6) -> None:
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.conf_threshold = conf_threshold
        
        self.base_dir = Path(__file__).resolve().parent.parent
        self.model_path = self.base_dir / "models" / model_name
        self.class_path = self.base_dir / "models" / "fire_classes.json"
        
        self.img_size = 224
        self.transform = transforms.Compose([
            transforms.Resize((self.img_size, self.img_size)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
        
        self.model = None
        self.class_names = []
        self._load_resources()

    def _load_resources(self) -> None:
        try:
            if self.class_path.exists():
                with open(self.class_path, "r", encoding="utf-8") as f:
                    self.class_names = json.load(f)
            else:
                logger.warning(f"화재 감지 클래스 파일 없음: {self.class_path}")
                self.class_names = ["normal", "fire", "smoke"] # fallback

            if self.model_path.exists():
                model = models.resnet18(weights=None)
                in_features = model.fc.in_features
                model.fc = nn.Linear(in_features, len(self.class_names))
                
                state_dict = torch.load(self.model_path, map_location=self.device)
                model.load_state_dict(state_dict)
                model.to(self.device)
                model.eval()
                self.model = model
                logger.info(f"FireDetector 모델 로드 완료: {self.model_path}")
            else:
                logger.warning(f"FireDetector 모델 파일 없음 (기능 비활성): {self.model_path}")

        except Exception as exc:
            logger.error(f"FireDetector 초기화 실패: {exc}")
            self.model = None

    def predict(self, frame: np.ndarray) -> Dict[str, Any]:
        if self.model is None or frame is None:
            return {"class": "unknown", "confidence": 0.0, "danger": False}

        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(frame_rgb)
            input_tensor = self.transform(image).unsqueeze(0).to(self.device)

            with torch.no_grad():
                outputs = self.model(input_tensor)
                probs = torch.softmax(outputs, dim=1)
                conf, pred = torch.max(probs, 1)

            idx = pred.item()
            predicted_class = self.class_names[idx] if idx < len(self.class_names) else "unknown"
            confidence = float(conf.item())

            # fire나 smoke일 때, 설정된 임계값 이상이면 위험으로 판단
            is_danger = (predicted_class in ["fire", "smoke"]) and (confidence >= self.conf_threshold)

            return {
                "class": predicted_class,
                "confidence": confidence,
                "danger": is_danger
            }
        except Exception as exc:
            logger.warning(f"화재 추론 중 오류: {exc}")
            return {"class": "error", "confidence": 0.0, "danger": False}

    def draw_overlay(self, frame: np.ndarray, result: Dict[str, Any]) -> np.ndarray:
        if not result or result.get("class") == "unknown":
            return frame
            
        cls = result["class"]
        conf = result["confidence"]
        danger = result["danger"]
        
        # 화면 좌측 가운데에 텍스트 표시
        color = (0, 0, 255) if danger else (0, 255, 0)
        text = f"FireCheck: {cls} ({conf:.2f})"
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        thickness = 2

        # 텍스트의 너비와 높이를 계산합니다.
        (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        
        # 텍스트를 프레임의 가로 중앙에 위치시키기 위한 x 좌표를 계산합니다.
        text_x = (frame.shape[1] - text_width) // 2
        
        cv2.putText(frame, text, (text_x, 30), font, font_scale, color, thickness, cv2.LINE_AA)
                    
        return frame