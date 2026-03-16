// src/pages/Dashboard/Dashboard.jsx
import React, { useState, useEffect, useRef } from "react";
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
  const [modalTab, setModalTab] = useState("logs"); // 'logs' | 'stats'
  const [tabDirection, setTabDirection] = useState(null); // 'left' | 'right'
  const [isAnimating, setIsAnimating] = useState(false);

  const switchTab = (tab) => {
    // 탭 화면 전환시 애니메이션 방향 결정 로직
    if (tab === modalTab || isAnimating) return;
    const dir = tab === "stats" ? "left" : "right";
    setTabDirection(dir);
    setIsAnimating(true);
    setModalTab(tab);
    setTimeout(() => setIsAnimating(false), 350);
  };

  // 월별 위험도 더미 데이터
  const MONTHLY_STATS = [
    { month: "1월", danger: 3 },
    { month: "2월", danger: 7 },
    { month: "3월", danger: 2 },
    { month: "4월", danger: 4 },
    { month: "5월", danger: 1 },
    { month: "6월", danger: 5 },
    { month: "7월", danger: 3 },
    { month: "8월", danger: 2 },
    { month: "9월", danger: 4 },
    { month: "10월", danger: 9 },
    { month: "11월", danger: 2 },
    { month: "12월", danger: 2 },
  ];
  const maxDanger = Math.max(...MONTHLY_STATS.map((d) => d.danger)); // 막대 높이 비율 계산용 코드
  const barChartRef = useRef(null);
  const [chartHeight, setChartHeight] = useState(193);

  useEffect(() => {
    if (!barChartRef.current) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        // 전체 높이 - 상단 패딩(20px) - 수치 레이블(22px) - 월 레이블(25px)
        const usable = entry.contentRect.height - 20 - 22 - 25;
        setChartHeight(Math.max(usable, 40));
      }
    });
    ro.observe(barChartRef.current);
    return () => ro.disconnect();
  }, []);

  const handleLogout = async () => {
    if (window.confirm("로그아웃 하시겠습니까?")) {
      await logout();
      navigate("/");
    }
  };

  useEffect(() => {
    // 대시보드 진입 시 body 전체 스크롤을 막아 고정 레이아웃 유지
    document.body.classList.add("dashboard-body-no-scroll");

    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => {
      // 언마운트 시 스크롤 제한 클래스 제거 (다른 페이지에 영향 방지)
      document.body.classList.remove("dashboard-body-no-scroll");
      clearInterval(timer);
    };
  }, []);

  // TODO: 실제 API 연동 필요
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
            {/*시계 카드*/}
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

            {/* 시스템 상태 카드*/}
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

            {/* 컨베이어 제어 카드 */}
            <div className="panel-card">
              <h3>컨베이어 제어</h3>
              <div className="control-buttons">
                <button>자동 모드 시작</button>
                <button>수동 모드 시작</button>
                <button>정지</button>
                <button>위험구역 설정</button>
              </div>
            </div>

            {/* 긴급 정지 카드 */}
            <div className="panel-card">
              <button className="emergency-stop-btn">긴급 정지</button>
            </div>
          </div>

          {/* 로그박스 - 이벤트 로그 패널 */}
          <div className="log-board panel-card">
            <div className="log-board-header">
              <h3>이벤트 로그</h3>
              <button
                className="log-check-btn"
                onClick={() => setShowLogs(true)}
              >
                로그 및 통계
              </button>
            </div>
            <div className="log-preview">
              {DUMMY_LOGS.slice(0, 5).map((log) => (
                <div
                  key={log.id}
                  className={`log-item ${
                    log.event_type.includes("CRITICAL")
                      ? "log-danger"
                      : log.event_type.includes("WARN") ||
                          log.event_type.includes("SLOWDOWN")
                        ? "log-warning"
                        : "log-info"
                  }`}
                >
                  <span className="log-icon">
                    {log.event_type.includes("CRITICAL")
                      ? "🔴"
                      : log.event_type.includes("WARN") ||
                          log.event_type.includes("SLOWDOWN")
                        ? "🟡"
                        : "🟢"}
                  </span>
                  <span className="log-text">
                    {log.details?.description || log.event_type}
                  </span>
                  <span className="log-time">
                    {new Date(log.timestamp).toLocaleTimeString("ko-KR", {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </main>

      {/* 로그 확인 모달 */}
      {showLogs && (
        <div
          className="modal-overlay"
          onClick={() => {
            setShowLogs(false);
            setModalTab("logs");
            setTabDirection(null);
          }}
        >
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-tabs">
                <button
                  className={`modal-tab-btn ${modalTab === "logs" ? "active" : ""}`}
                  onClick={() => switchTab("logs")}
                >
                  이벤트 로그
                </button>
                <button
                  className={`modal-tab-btn ${modalTab === "stats" ? "active" : ""}`}
                  onClick={() => switchTab("stats")}
                >
                  통계
                </button>
              </div>
              <button
                className="modal-close-btn"
                onClick={() => {
                  setShowLogs(false);
                  setModalTab("logs");
                  setTabDirection(null);
                }}
              >
                &times;
              </button>
            </div>
            <div className="modal-body">
              {/*
                tab-slider: 탭 콘텐츠 슬라이더 컨테이너
                slide-left / slide-right: 전환 방향에 따라 CSS 슬라이드 애니메이션 트리거
                animating: 애니메이션 진행 중일 때 추가 클릭 방지 및 transition 활성화
              */}
              <div
                className={`tab-slider ${tabDirection ? `slide-${tabDirection}` : ""} ${isAnimating ? "animating" : ""}`}
              >
                {/* 로그 패널 */}
                <div className="tab-panel logs-panel">
                  <VideoLogTable logs={DUMMY_LOGS} />
                </div>
                {/* 통계 패널 */}
                <div className="tab-panel stats-panel">
                  <div className="stats-container">
                    <h3 className="stats-title">월별 위험도</h3>
                    <div className="bar-chart" ref={barChartRef}>
                      {MONTHLY_STATS.map((item) => (
                        <div className="bar-col" key={item.month}>
                          <div className="bar-value">{item.danger}</div>
                          <div
                            className="bar-fill"
                            style={{
                              height: `${Math.round((item.danger / maxDanger) * chartHeight)}px`,
                              backgroundColor:
                                item.danger <= 3
                                  ? "var(--status-ok)"
                                  : item.danger >= 7
                                    ? "var(--status-danger)"
                                    : "var(--accent-color)",
                            }}
                          />
                          <div className="bar-label">{item.month}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;
