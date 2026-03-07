// src/pages/Dashboard/Dashboard.jsx
import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Webcam from "react-webcam";
import useAuthStore from "../../store/useAuthStore";
import "./Dashboard.css";

// 로그 타입에 따라 아이콘을 바꿔 로그 메시지와 시간을 함께 화면에 표시
const LogItem = ({ type = "info", message, time }) => {
  const iconMap = {
    info: "ℹ️",
    warning: "⚠️",
    danger: "🚨",
  };
  return (
    <div className={`log-item log-${type}`}>
      <span className="log-icon">{iconMap[type]}</span>
      <span className="log-message">{`[${time}] ${message}`}</span>
    </div>
  );
};

function Dashboard() {
  // 상태 선언
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();

  const [currentTime, setCurrentTime] = useState(new Date()); // 수정됨
  const [webcamError, setWebcamError] = useState(null); // 웹캠 접근 실패 시 에러 메시지 저장
  const [hour12, setHour12] = useState(true);

  const handleLogout = async () => {
    if (window.confirm("로그아웃 하시겠습니까?")) {
      await logout();
      navigate("/");
    }
  };

  useEffect(() => {
    document.body.classList.add("dashboard-body-no-scroll"); // 전체화면 스크롤 방지

    // 수정된 시간 가져오기
    const timer = setInterval(() => {
      const now = new Date();

      setCurrentTime(
        /* 
        now.toLocaleString("ko-KR", {
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }),*/
        now,
      );
    }, 1000);

    return () => {
      document.body.classList.remove("dashboard-body-no-scroll");
      clearInterval(timer);
    };
  }, []);

  const systemStatus = "ok"; // 'ok', 'warning', 'danger'

  // 웹캠 설정
  const videoConstraints = {
    facingMode: "user",
  };

  // 웹캠 연결 오류 메시지
  const handleUserMediaError = (error) => {
    console.error("Webcam access error:", error);
    setWebcamError(
      "웹캠에 접근할 수 없습니다. 권한을 확인하거나 다른 프로그램에서 사용 중인지 확인해주세요.",
    );
  };

  return (
    <div className="dashboard">
      <header className="header-bar">
        <div className="header-left">
          <div className="logo">STOP</div>
          <div className="factory-label">Subtitle</div>
        </div>
        <div className="right-info">
          <div className="date-time">
            {currentTime.toLocaleDateString("ko-Kr", {
              year: "numeric",
              month: "2-digit",
              day: "2-digit",
            })}
          </div>
          <div className="user-label">
            🧑‍💻 {user?.role || "user"} ({user?.email})
          </div>
          <button className="logout-btn" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

      <main className="main-layout">
        {/* 웹캠? CCTV 칸 */}
        <section className="stream-panel">
          {webcamError ? (
            <div className="webcam-error">
              <p>⚠️ {webcamError}</p>
            </div>
          ) : (
            <Webcam
              audio={false}
              videoConstraints={videoConstraints}
              onUserMediaError={handleUserMediaError}
              className="webcam-feed"
            /> // --> react-webcam으로 카메라 연결(임시)
          )}
        </section>
        <aside className="control-panel">
          {/*시스템 제어*/}
          <div className="system-infos">
            <h3>시스템 정보</h3>
            {/*시계*/}
            <div className="time-card">
              <div className="string-time">
                {currentTime.toLocaleTimeString("ko-KR", {
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                  hour12: hour12,
                })}
                <button
                  onClick={() => {
                    setHour12((prev) => !prev);
                  }}
                >
                  {hour12 ? "24H" : "12H"}
                </button>
              </div>
            </div>

            {/* 시스템 상태 */}
            <div className={`panel-card system-status status-${systemStatus}`}>
              <div className="status-indicator">
                <span className="status-light"></span>
                <span>
                  {systemStatus === "ok" && "All Systems Operational"}
                  {systemStatus === "warning" && "System Warning"}
                  {systemStatus === "danger" && "System Critical"}
                </span>
              </div>
            </div>

            {/* 제어칸 */}
            <div className="panel-card">
              <h3>컨베이어 제어</h3>
              <div className="control-buttons">
                <button>자동 모드 시작</button>
                <button>수동 모드 시작</button>
                <button>정지</button>
                <button>위험구역 설정</button>
              </div>
            </div>

            {/* 긴급 정지칸 */}
            <div className="panel-card">
              <button className="emergency-stop-btn">긴급 정지</button>
            </div>
          </div>

          {/* 로그박스, 현재 더미데이터로 설정해놓음 */}
          <div className="panel-card log-board">
            <h3>이벤트 로그</h3>
            <div className="log-content">
              <LogItem
                type="danger"
                time="14:45:12"
                message="위험 구역 #1에서 작업자 감지"
              />
              <LogItem
                type="warning"
                time="14:46:01"
                message="컨베이어 벨트 속도 저하"
              />
              <LogItem type="info" time="14:48:30" message="시스템 재가동" />
              <LogItem
                type="danger"
                time="14:49:12"
                message="비상 정지 버튼 눌림"
              />
              <LogItem type="info" time="14:50:30" message="관리자 로그인" />
            </div>
          </div>
        </aside>
      </main>
    </div>
  );
}

export default Dashboard;
