import cv2
import torch
import numpy as np
from collections import deque
from ultralytics import YOLO

# 우리가 만든 DD-Net 모델 구조 불러오기

def run_demo(video_path, output_path="demo_result.mp4"):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[안내] 구동 환경: {device}")

    # 1. 모델 로드 (YOLO & DD-Net)
    print("AI 모델을 불러오는 중입니다...")
    yolo_model = YOLO('yolov8n-pose.pt') # 가벼운 YOLO 나노 모델
    
    ddnet_model = torch.jit.load("ddnet_deploy_jetson.pt").to(device)
    ddnet_model.eval()

    # 2. 비디오 설정
    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    
    # 결과 저장용 비디오 라이터
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # 3. 20프레임 메모리 버퍼 (큐 방식: 꽉 차면 과거 데이터부터 버림)
    frame_buffer = deque(maxlen=20)
    
    print("\n🎬 실시간 추론을 시작합니다. (종료하려면 'q' 키를 누르세요)")
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        # [A] YOLOv8로 뼈대 추출
        results = yolo_model(frame, verbose=False)
        annotated_frame = results[0].plot() # 뼈대가 그려진 이미지
        
        # 현재 프레임의 17개 관절 좌표를 담을 배열 (17, 2)
        current_kpts = np.full((17, 2), np.nan)
        
        if results[0].keypoints is not None and len(results[0].keypoints.xy) > 0:
            # 첫 번째 사람의 좌표만 가져옴 (다중 객체는 생략)
            kpts = results[0].keypoints.xyn[0].cpu().numpy()

            # ---------------------------------------------------------
            # 💡 [추가된 로그 출력 코드] 
            # ---------------------------------------------------------
            # kpts[0]은 0번 관절(코, Nose)의 [x, y] 좌표입니다.
            nose_x, nose_y = kpts[0]
            max_val = np.nanmax(kpts) # 현재 프레임 좌표 중 가장 큰 값
            
            print(f"프레임 로그 ➔ 코 좌표: ({nose_x:.3f}, {nose_y:.3f}) | 최대 스케일값: {max_val:.3f}")
            # ---------------------------------------------------------
            
            for i in range(min(17, len(kpts))):
                x, y = kpts[i]
                if x > 0 and y > 0:
                    current_kpts[i] = [x, y]
                    
        # 결측치(0,0 탐지 실패) 실시간 보정: 이전 프레임의 좌표를 그대로 끌고 옴
        if len(frame_buffer) > 0:
            prev_kpts = frame_buffer[-1]
            mask = np.isnan(current_kpts)
            current_kpts[mask] = prev_kpts[mask]
            
        # 만약 첫 프레임부터 결측치면 0으로 채움
        current_kpts[np.isnan(current_kpts)] = 0.0
        
        frame_buffer.append(current_kpts)
        
        # [B] 버퍼에 20프레임이 꽉 차면 DD-Net 판단 시작!
        status_text = "Gathering Frames..."
        box_color = (128, 128, 128) # 회색 (대기 중)
        
        if len(frame_buffer) == 20:
            # 버퍼 데이터를 (1, 20, 17, 2) 텐서로 변환
            seq_array = np.array(frame_buffer)
            seq_tensor = torch.FloatTensor(seq_array).unsqueeze(0).to(device)
            
            # DD-Net 추론
            with torch.no_grad():
                outputs = ddnet_model(seq_tensor)
                probabilities = torch.nn.functional.softmax(outputs, dim=1)[0]
                
                prob_normal = probabilities[0].item() * 100
                prob_fall = probabilities[1].item() * 100
                
                # 예측 결과에 따른 시각화 설정
                if prob_fall > 80.0: # 낙상 확률이 80% 이상일 때만 경고
                    status_text = f"WARNING: Fall-Down! ({prob_fall:.1f}%)"
                    box_color = (0, 0, 255) # 빨간색 (OpenCV는 BGR 순서)
                    # ------------------------------------------------------
                    # 🚨 [추가] 이중 안전장치: YOLO 바운딩 박스 비율 (가로/세로) 확인
                    # ------------------------------------------------------
                    w = 0
                    h = 1 # 0 나누기 방지
                    if results[0].boxes is not None and len(results[0].boxes) > 0:
                        # 첫 번째 사람의 바운딩 박스 [x_center, y_center, width, height]
                        box = results[0].boxes.xywh[0] 
                        w = box[2].item()
                        h = box[3].item()
                    
                    # 쓰러지면 보통 가로(w)가 세로(h)보다 길어집니다.
                    # 허리만 숙인 상태(세로가 훨씬 긺)를 걸러내기 위해 w > h * 0.8 정도의 조건을 줍니다.
                    if w > h * 1.2:
                        status_text = f"WARNING: Fall-Down! ({prob_fall:.1f}%)"
                        box_color = (0, 0, 255) # 빨간색
                    else:
                        # DD-Net은 낙상이라 했지만, 박스 비율상 서 있는 상태
                        status_text = f"Bending / Working ({prob_fall:.1f}%)"
                        box_color = (0, 255, 255) # 노란색 (주의/작업중)
                else:
                    status_text = f"Normal ({prob_normal:.1f}%)"
                    box_color = (0, 255, 0) # 초록색
        
        # [C] 화면에 상태 알림 UI 그리기
        cv2.rectangle(annotated_frame, (10, 10), (600, 60), box_color, -1)
        cv2.putText(annotated_frame, status_text, (20, 45), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
                    
        # 결과 화면 출력 및 저장
        cv2.imshow("DD-Net Fall Detection Demo", annotated_frame)
        out.write(annotated_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print("\n✅ 데모 영상 처리가 완료되었습니다! ('demo_result.mp4' 확인)")

if __name__ == '__main__':
    # 테스트할 CCTV 원본 영상의 경로를 적어주세요!
    TEST_VIDEO_PATH = "sample.mp4" 
    run_demo(TEST_VIDEO_PATH)