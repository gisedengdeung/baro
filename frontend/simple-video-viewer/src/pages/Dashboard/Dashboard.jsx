// src/pages/Dashboard/Dashboard.jsx
import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import useAuthStore from "../../store/useAuthStore";
import { useWebRTC } from "../../hooks/useWebRTC";
import VideoLogTable from "../../components/dashboard/VideoLogTable";
import "./Dashboard.css";

// 더미 로그 데이터
const DUMMY_LOGS = [
  {
    id: 1,
    timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    operation_mode: "AUTOMATIC",
    event_type: "LOG_NORMAL_OPERATION",
  },
  {
    id: 2,
    timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
    operation_mode: "AUTOMATIC",
    event_type: "LOG_INTRUSION_SLOWDOWN",
    details: { description: "위험 구역 침입 감지" },
  },
  {
    id: 3,
    timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    operation_mode: "MAINTENANCE",
    event_type: "LOG_MAINTENANCE_SAFE",
  },
  {
    id: 4,
    timestamp: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
    operation_mode: "AUTOMATIC",
    event_type: "LOG_CRITICAL_FALLING",
    details: { description: "작업자 쓰러짐 발생!" },
  },
  {
    id: 5,
    timestamp: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
    operation_mode: "STOPPED",
    event_type: "LOG_CRITICAL_SENSOR",
  },
  {
    id: 6,
    timestamp: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
    operation_mode: "AUTOMATIC",
    event_type: "LOG_CROUCHING_WARN",
  },
  {
    id: 7,
    timestamp: new Date(Date.now() - 1000 * 60 * 180).toISOString(),
    operation_mode: "MANUAL",
    event_type: "LOG_LOTO_ACTIVE",
  },
];

function Dashboard() {
  // 상태 선언
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();

  const { videoRef, connected, error: streamError } = useWebRTC();

  const [currentTime, setCurrentTime] = useState(new Date());
  const [hour12, setHour12] = useState(true);
  const [showLogs, setShowLogs] = useState(false);

  const handleLogout = async () => {
    if (window.confirm("로그아웃 하시겠습니까?")) {
      await logout();
      navigate("/");
    }
  };

  useEffect(() => {
    document.body.classList.add("dashboard-body-no-scroll"); // 전체화면 스크롤 방지

    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => {
      document.body.classList.remove("dashboard-body-no-scroll");
      clearInterval(timer);
    };
  }, []);

  const systemStatus = "ok"; // 'ok', 'warning', 'danger'

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
        {/* CCTV WebRTC 스트림 */}
        <section className="stream-panel">
          {streamError ? (
            <div className="webcam-error">
              <p>⚠️ {streamError}</p>
            </div>
          ) : (
            <>
              {!connected && (
                <div className="webcam-error">
                  <p>📡 Edge 연결 중...</p>
                </div>
              )}
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="webcam-feed"
                style={{ display: connected ? "block" : "none" }}
              />
            </>
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
                <button onClick={() => setHour12((prev) => !prev)}>
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

          {/* 로그박스 - 로그 확인하기 버튼만 표시 */}
          <div className="log-board">
            <button className="log-check-btn" onClick={() => setShowLogs(true)}>
              로그 확인하기
            </button>
          </div>
        </aside>
      </main>

      {/* 로그 확인 모달 */}
      {showLogs && (
        <div className="modal-overlay" onClick={() => setShowLogs(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>🎞️ 시스템 이벤트 로그</h2>
              <button
                className="modal-close-btn"
                onClick={() => setShowLogs(false)}
              >
                &times;
              </button>
            </div>
            <div className="modal-body" style={{ height: "500px" }}>
              <VideoLogTable logs={DUMMY_LOGS} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;
