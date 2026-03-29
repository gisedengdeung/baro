// src/pages/Dashboard/Dashboard.jsx
import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import useAuthStore from "../../store/useAuthStore";
import useDashboardStore from "../../store/useDashboardStore";

import LiveStreamContent from "../../components/dashboard/LiveStreamContent";
import DangerZoneSelector from "../../components/dashboard/DangerZoneSelector";
import ZoneConfigPanel from "../../components/dashboard/ZoneConfigPanel";
import ZoneOverlay from "../../components/dashboard/ZoneOverlay";
import VideoLogTable from "../../components/dashboard/VideoLogTable";
import StatsPage from "../../components/dashboard/StatsPage";
import "./Dashboard.css";

function Dashboard() {
  const navigate = useNavigate();

  // Auth Store
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);

  // Dashboard Store - System State
  const {
    logs,
    activeId,
    operationMode,
    conveyorSpeed,
    riskLevel,
    isLocked,
    loading,
    popupError,
    testSpeed,
    testSpeedInput,
    currentTime,
    videoStatus,
    globalAlert,
  } = useDashboardStore();

  // Dashboard Store - Actions
  const {
    initialize: initializeDashboard,
    disconnect: disconnectDashboard,
    handleControl,
    resetSystem,
    setTestSpeedInput,
    startTestRun,
    applyTestSpeed,
    stopTestRun,
    setVideoStatus,
    setActiveId,
  } = useDashboardStore();

  // Dashboard Store - Danger Zone State & Actions
  const {
    isDangerMode,
    zones,
    selectedZoneId,
    configAction,
    newZoneName,
    imageSize,
    enterDangerMode,
    exitDangerMode,
    setSelectedZoneId,
    setConfigAction,
    setNewZoneName,
    handleCreateZone,
    handleUpdateZone,
    handleDeleteZone,
    setImageSize,
  } = useDashboardStore();

  // Local UI State
  const [sidebarSection, setSidebarSection] = useState("dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [hour12, setHour12] = useState(true);
  const [showLogs, setShowLogs] = useState(false);
  const [isEmergencyStopped, setIsEmergencyStopped] = useState(false);
  const [showTestRun, setShowTestRun] = useState(false);
  const [modalTab, setModalTab] = useState("logs");
  const [tabDirection, setTabDirection] = useState(null);
  const [isAnimating, setIsAnimating] = useState(false);
  const [panelTab, setPanelTab] = useState("logs"); // logs | stats | testrun
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [statsFilter, setStatsFilter] = useState("all");

  const barChartRef = useRef(null);
  const chartHeight = 160;

  // 로그 기반 감지 통계 (전체 요약)
  const DETECTION_SUMMARY = React.useMemo(() => {
    const falling = logs.filter((l) =>
      (l.details?.description || l.event_type || "").startsWith(
        "A person falling",
      ),
    ).length;
    const intrusion = logs.filter((l) =>
      (l.details?.description || l.event_type || "").startsWith(
        "Person detected in danger zone",
      ),
    ).length;
    const sensor = logs.filter((l) =>
      (l.details?.description || l.event_type || "")
        .toLowerCase()
        .includes("fire"),
    ).length;
    return { total: logs.length, falling, intrusion, sensor };
  }, [logs]);

  // 선택된 연도 기준 월별 통계
  const MONTHLY_STATS = React.useMemo(() => {
    const months = Array.from({ length: 12 }, (_, i) => ({
      month: `${i + 1}월`,
      falling: 0,
      intrusion: 0,
      sensor: 0,
    }));
    logs.forEach((l) => {
      const d = new Date(l.timestamp);
      if (d.getFullYear() !== selectedYear) return;
      const m = d.getMonth();
      const desc = l.details?.description || l.event_type || "";
      if (desc.startsWith("A person falling")) months[m].falling += 1;
      else if (desc.startsWith("Person detected in danger zone"))
        months[m].intrusion += 1;
      else if (desc.toLowerCase().includes("fire")) months[m].sensor += 1;
    });
    return months;
  }, [logs, selectedYear]);

  // 막대 차트 최대값 (높이 스케일링용)
  const maxCount = React.useMemo(() => {
    const vals = MONTHLY_STATS.flatMap((m) => [
      m.falling,
      m.intrusion,
      m.sensor,
    ]);
    return Math.max(...vals, 1);
  }, [MONTHLY_STATS]);

  // 모달 탭 전환 (애니메이션 포함)
  const switchTab = (tab) => {
    if (tab === modalTab || isAnimating) return;
    const direction = tab === "stats" ? "left" : "right";
    setTabDirection(direction);
    setIsAnimating(true);
    setModalTab(tab);
    setTimeout(() => {
      setIsAnimating(false);
      setTabDirection(null);
    }, 300);
  };
  useEffect(() => {
    if (operationMode !== "STOPPED") setIsEmergencyStopped(false);
  }, [operationMode]);

  const handleLogout = async () => {
    if (window.confirm("로그아웃 하시겠습니까?")) {
      await logout();
      navigate("/");
    }
  };

  useEffect(() => {
    initializeDashboard();
    document.body.classList.add("dashboard-body-no-scroll");
    return () => {
      disconnectDashboard();
      document.body.classList.remove("dashboard-body-no-scroll");
    };
  }, [initializeDashboard, disconnectDashboard]);

  const systemStatus =
    isLocked || riskLevel === "CRITICAL"
      ? "danger"
      : riskLevel === "WARNING" ||
          riskLevel === "NOTICE" ||
          riskLevel === "LOTO_RISK_DETECTED"
        ? "warning"
        : !operationMode || operationMode === "STOPPED"
          ? "offline"
          : operationMode === "MAINTENANCE" || operationMode === "TEST"
            ? "warning"
            : "ok";

  const isStopped = operationMode === "STOPPED";
  const isTestMode = operationMode === "TEST";
  const previewLogs = logs.slice(0, 5);

  const NAV_ITEMS = [
    { id: "dashboard", icon: "⊞", label: "대시보드" },
    { id: "cctv", icon: "📹", label: "CCTV" },
    { id: "multicctv", icon: "📍", label: "멀티CCTV" },
    { id: "detections", icon: "📋", label: "감지내역" },
    { id: "stats", icon: "📊", label: "통계" },
  ];

  return (
    <div className="dashboard">
      <header className="header-bar">
        <div className="header-left">
          <button
            className="sidebar-toggle-btn"
            onClick={() => setSidebarOpen((prev) => !prev)}
            aria-label="사이드바 열기/닫기"
          >
            <span></span>
            <span></span>
            <span></span>
          </button>
          <div className="logo">STOP</div>
          <div className="factory-label">Subtitle</div>
        </div>
        <div className="right-info">
          <div className="date-time">{currentTime.split(" / ")[0]}</div>
        </div>
      </header>

      <div className="dashboard-body">
        {/* 좌측 사이드바 */}
        <nav className={`sidebar${sidebarOpen ? "" : " sidebar-closed"}`}>
          <div className="sidebar-nav">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.id}
                className={`sidebar-item${sidebarSection === item.id ? " active" : ""}`}
                onClick={() => {
                  setSidebarSection(item.id);
                }}
              >
                <span className="sidebar-icon">{item.icon}</span>
                <span className="sidebar-label">{item.label}</span>
              </button>
            ))}
          </div>
          <div className="sidebar-bottom">
            <button
              className="sidebar-item sidebar-logout-btn"
              onClick={handleLogout}
            >
              <span className="sidebar-icon">🚪</span>
              <span className="sidebar-label">로그아웃</span>
            </button>
            <button className="sidebar-item">
              <span className="sidebar-icon">👤</span>
              <span className="sidebar-label">{user?.role || "user"}</span>
            </button>
            <button className="sidebar-item">
              <span className="sidebar-icon">⚙</span>
              <span className="sidebar-label">설정</span>
            </button>
          </div>
        </nav>

        {sidebarSection === "stats" ? (
          <StatsPage logs={logs} />
        ) : sidebarSection === "detections" ? (
          <main className="stats-page">
            <div className="stats-page-inner">
              <h2 className="stats-page-title">전체 이벤트 로그</h2>
              <VideoLogTable logs={logs} />
            </div>
          </main>
        ) : (
          <main className="main-layout">
            <section className="stream-panel">
              {/* 카메라 스트림은 항상 유지 — 위험구역 설정 모드에서도 끊기지 않음 */}
              <div
                className="live-stream-wrapper"
                style={{ position: "relative", width: "100%", height: "100%" }}
              >
                <LiveStreamContent
                  onImageLoad={setImageSize}
                  onStatusChange={setVideoStatus}
                />
                {/* 구역 오버레이는 항상 표시 (선택된 구역 강조 포함) */}
                <ZoneOverlay
                  zones={zones}
                  selectedZoneId={selectedZoneId}
                  imageSize={imageSize}
                />

                {/* 구역 그리기 모드: 스트림 위에 선택기 표시 (create/update 시에만) */}
                {isDangerMode &&
                  (configAction === "create" || configAction === "update") && (
                    <div style={{ position: "absolute", inset: 0 }}>
                      <DangerZoneSelector
                        onComplete={
                          configAction === "create"
                            ? handleCreateZone
                            : handleUpdateZone
                        }
                        imageSize={imageSize}
                      />
                    </div>
                  )}
              </div>
            </section>

            <aside className="control-panel" style={{ position: "relative" }}>
              {/* 긴급 알림 오버레이 - globalAlert가 null이 될 때까지 유지 */}
              {globalAlert && (
                <div className="global-alert-overlay">
                  <div className="global-alert-overlay-content">
                    <div className="global-alert-title">⚠ SYSTEM LOCKED</div>
                    <div className="global-alert-desc">
                      {globalAlert.details?.description ||
                        globalAlert.event_type}
                    </div>
                    <div className="global-alert-desc-sub">
                      관리자의 확인 후 시스템을 리셋하세요.
                    </div>
                    <div className="global-alert-time">
                      {new Date(globalAlert.timestamp).toLocaleTimeString(
                        "ko-KR",
                        {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        },
                      )}
                    </div>
                    <button
                      className="alert-reset-btn"
                      disabled={loading}
                      onClick={() => {
                        useDashboardStore.setState({ globalAlert: null });
                        resetSystem();
                      }}
                    >
                      ⚡ 시스템 리셋
                    </button>
                  </div>
                </div>
              )}
              <div className="system-infos">
                <h3>시스템 정보</h3>
                <div className="time-card">
                  <div className="string-time">
                    {(() => {
                      const now = new Date();
                      if (hour12) {
                        const period = now.getHours() >= 12 ? "PM" : "AM";
                        const h = now.getHours() % 12 || 12;
                        const m = String(now.getMinutes()).padStart(2, "0");
                        return `${period} ${h}:${m}`;
                      } else {
                        const h = String(now.getHours()).padStart(2, "0");
                        const m = String(now.getMinutes()).padStart(2, "0");
                        return `${h}:${m}`;
                      }
                    })()}
                    <button onClick={() => setHour12((prev) => !prev)}>
                      {hour12 ? "24H" : "12H"}
                    </button>
                  </div>
                </div>

                <div
                  className={`panel-card system-status status-${systemStatus}`}
                >
                  <div className="status-indicator">
                    <span className="status-light"></span>
                    <span>
                      {systemStatus === "danger" && "긴급 위험 감지"}
                      {systemStatus !== "danger" &&
                        (() => {
                          if (!operationMode) return "시스템 꺼짐";
                          if (operationMode === "STOPPED" && isEmergencyStopped)
                            return "긴급 정지 (STOPPED)";
                          switch (operationMode) {
                            case "STOPPED":
                              return `시스템 대기 중 (${operationMode})`;
                            case "AUTOMATIC":
                            case "RUNNING":
                              return `정상 운전 중 (${operationMode})`;
                            case "MAINTENANCE":
                              return `정비 모드 (${operationMode})`;
                            case "TEST":
                              return `테스트 운행 중 (${operationMode})`;
                            default:
                              return operationMode;
                          }
                        })()}
                    </span>
                  </div>

                  <div className="status-meta">
                    <div className="status-lock-inline">
                      <span className="status-lock-icon">
                        {isLocked ? "🔒" : "🔓"}
                      </span>
                      <span
                        className={`status-lock-value ${isLocked ? "locked" : "safe"}`}
                      >
                        {isLocked ? "LOCKED" : "SAFE"}
                      </span>
                      <span className="status-divider">│</span>
                      <span className="status-lock-icon">📡</span>
                      <span
                        className={`status-lock-value ${videoStatus === "connected" ? "safe" : "locked"}`}
                      >
                        {videoStatus === "connected"
                          ? "카메라 연결됨"
                          : "카메라 연결 끊김"}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="system-power-card">
                <div className="system-power-buttons">
                  <button
                    className="system-power-btn system-on-btn"
                    disabled={loading || isDangerMode}
                    onClick={() => handleControl("start_automatic")}
                  >
                    <span className="power-icon">⏻</span> 전체 시스템 ON
                  </button>
                  <button
                    className="system-power-btn system-off-btn"
                    disabled={loading || isDangerMode}
                    onClick={() => handleControl("stop")}
                  >
                    <span className="power-icon">⏼</span> 전체 시스템 OFF
                  </button>
                </div>
              </div>

              <div className="conveyor-control-section">
                <div className="conveyor-control-header">
                  <h3>컨베이어 제어</h3>
                  <button
                    className="test-run-toggle-btn"
                    disabled={isDangerMode}
                    onClick={() => setShowTestRun((prev) => !prev)}
                  >
                    테스트 운행
                  </button>
                </div>
                <div className="control-buttons">
                  <button
                    disabled={loading || isDangerMode}
                    onClick={() => handleControl("start_maintenance")}
                  >
                    🖥️ 정비 모드
                  </button>
                  <button
                    className={isDangerMode ? "active" : ""}
                    disabled={loading}
                    onClick={isDangerMode ? exitDangerMode : enterDangerMode}
                  >
                    ⚠️ 위험구역 설정
                  </button>
                </div>

                <button
                  className="emergency-stop-btn"
                  disabled={loading || isDangerMode}
                  onClick={() => {
                    handleControl("stop");
                    setIsEmergencyStopped(true);
                  }}
                >
                  🛑 긴급 정지
                </button>
                {popupError && (
                  <div className="dashboard-error-banner">{popupError}</div>
                )}
              </div>

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
                  {previewLogs.length === 0 ? (
                    <div className="log-empty">기록된 로그가 없습니다.</div>
                  ) : (
                    previewLogs.map((log, idx) => (
                      <div
                        key={log.id || idx}
                        className={`log-item ${log.log_risk_level?.toLowerCase() || "info"}`}
                      >
                        <span className="log-icon">
                          {log.log_risk_level === "CRITICAL"
                            ? "🔴"
                            : log.log_risk_level === "HIGH" ||
                                log.log_risk_level === "WARNING"
                              ? "🟡"
                              : "🟢"}
                        </span>
                        <span className="log-text">
                          {(() => {
                            const raw =
                              log.details?.description || log.event_type || "";
                            if (
                              raw.startsWith(
                                "A person falling has been detected",
                              )
                            )
                              return "🔥  넘어짐 감지  🔥";
                            if (
                              raw.startsWith(
                                "Person detected in danger zone(s):",
                              )
                            )
                              return "⚠️  위험구역 침입 감지  ⚠️";
                            if (raw.startsWith("System is operating normally"))
                              return "ℹ️  정상 운행  ℹ️";
                            if (raw.startsWith("System has been reset"))
                              return "ℹ️  시스템 리셋  ℹ️";
                            if (raw.startsWith("Emergency stop"))
                              return "🚫  긴급 정지 실행  🚫";
                            if (raw.startsWith("Conveyor started"))
                              return "ℹ️  컨베이어 운행  ℹ️";
                            if (raw.startsWith("Conveyor stopped"))
                              return "ℹ️  컨베이어 정지  ℹ️";
                            if (raw.startsWith("Maintenance mode"))
                              return "✅  정비 모드 전환  ✅";
                            return raw;
                          })()}
                        </span>
                        <span className="log-time">
                          {new Date(log.timestamp).toLocaleTimeString("ko-KR", {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </aside>
          </main>
        )}
        {/* end stats ternary */}
      </div>
      {/* end .dashboard-body */}

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
              <div
                className={`tab-slider ${tabDirection ? `slide-${tabDirection}` : ""} ${isAnimating ? "animating" : ""}`}
              >
                <div className="tab-panel logs-panel">
                  <VideoLogTable logs={logs} />
                </div>
                <div className="tab-panel stats-panel">
                  <div className="stats-container">
                    {/* 전체 감지 내역 */}
                    <div className="detection-summary">
                      <h3 className="stats-title" style={{ margin: "0 0 4px" }}>
                        전체 감지 내역
                      </h3>
                      <p className="detection-summary-sub">
                        전체 기간 · 모든 이벤트
                      </p>
                      <div className="gauge-list">
                        {[
                          {
                            label: "총 발생",
                            value: DETECTION_SUMMARY.total,
                            max: DETECTION_SUMMARY.total || 1,
                            color: "#6366f1",
                          },
                          {
                            label: "넘어짐 감지",
                            value: DETECTION_SUMMARY.falling,
                            max: DETECTION_SUMMARY.total || 1,
                            color: "var(--status-danger)",
                          },
                          {
                            label: "위험구역 접근",
                            value: DETECTION_SUMMARY.intrusion,
                            max: DETECTION_SUMMARY.total || 1,
                            color: "var(--accent-color)",
                          },
                          {
                            label: "화재 감지",
                            value: DETECTION_SUMMARY.sensor,
                            max: DETECTION_SUMMARY.total || 1,
                            color: "#3b82f6",
                          },
                        ].map(({ label, value, max, color }) => {
                          const pct = Math.min((value / max) * 100, 100);
                          const angle = pct * 1.8; // 0~180도
                          const r = 36;
                          const cx = 44,
                            cy = 44;
                          const toRad = (deg) => (deg * Math.PI) / 180;
                          const startAngle = 180;
                          const endAngle = 180 + angle;
                          const x1 = cx + r * Math.cos(toRad(startAngle));
                          const y1 = cy + r * Math.sin(toRad(startAngle));
                          const x2 = cx + r * Math.cos(toRad(endAngle));
                          const y2 = cy + r * Math.sin(toRad(endAngle));
                          const largeArc = angle > 180 ? 1 : 0;
                          return (
                            <div className="gauge-item" key={label}>
                              <svg viewBox="0 0 88 50" className="gauge-svg">
                                {/* 배경 반원 */}
                                <path
                                  d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
                                  fill="none"
                                  stroke="#374151"
                                  strokeWidth="8"
                                  strokeLinecap="round"
                                />
                                {/* 채워진 반원 */}
                                {value > 0 && (
                                  <path
                                    d={`M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`}
                                    fill="none"
                                    stroke={color}
                                    strokeWidth="8"
                                    strokeLinecap="round"
                                  />
                                )}
                                {/* 수치 텍스트 */}
                                <text
                                  x={cx}
                                  y={cy - 2}
                                  textAnchor="middle"
                                  fontSize="13"
                                  fontWeight="bold"
                                  fill={color}
                                >
                                  {value}
                                </text>
                                <text
                                  x={cx}
                                  y={cy + 10}
                                  textAnchor="middle"
                                  fontSize="8"
                                  fill="#9ca3af"
                                >
                                  건
                                </text>
                              </svg>
                              <div className="gauge-label">{label}</div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    <div className="stats-divider" />
                    <div className="stats-header">
                      <h3 className="stats-title">월별 위험 이벤트</h3>
                      <div className="year-selector">
                        <button
                          className="year-btn"
                          onClick={() => setSelectedYear((y) => y - 1)}
                        >
                          ◀
                        </button>
                        <span className="year-label">{selectedYear}년</span>
                        <button
                          className="year-btn"
                          disabled={selectedYear >= new Date().getFullYear()}
                          onClick={() => setSelectedYear((y) => y + 1)}
                        >
                          ▶
                        </button>
                      </div>
                    </div>
                    <div className="stats-legend">
                      <span
                        className={`legend-item legend-btn ${statsFilter === "all" ? "active" : ""}`}
                        onClick={() => setStatsFilter("all")}
                      >
                        <span
                          className="legend-dot"
                          style={{ background: "var(--text-secondary)" }}
                        ></span>
                        전체
                      </span>
                      <span
                        className={`legend-item legend-btn ${statsFilter === "falling" ? "active" : ""}`}
                        onClick={() => setStatsFilter("falling")}
                      >
                        <span
                          className="legend-dot"
                          style={{ background: "var(--status-danger)" }}
                        ></span>
                        넘어짐 감지
                      </span>
                      <span
                        className={`legend-item legend-btn ${statsFilter === "intrusion" ? "active" : ""}`}
                        onClick={() => setStatsFilter("intrusion")}
                      >
                        <span
                          className="legend-dot"
                          style={{ background: "var(--accent-color)" }}
                        ></span>
                        위험구역 접근
                      </span>
                      <span
                        className={`legend-item legend-btn ${statsFilter === "sensor" ? "active" : ""}`}
                        onClick={() => setStatsFilter("sensor")}
                      >
                        <span
                          className="legend-dot"
                          style={{ background: "#3b82f6" }}
                        ></span>
                        화재 감지
                      </span>
                    </div>
                    <div className="bar-chart-area">
                      {/* Y축 눈금 */}
                      <div className="y-axis">
                        {Array.from({ length: 10 }, (_, i) => {
                          const val = 50 - i * 5;
                          return (
                            <div key={i} className="y-tick">
                              <span className="y-tick-label">{val}</span>
                              <span className="y-tick-line" />
                            </div>
                          );
                        })}
                        <div className="y-tick">
                          <span className="y-tick-label">0</span>
                          <span className="y-tick-line" />
                        </div>
                      </div>
                      <div className="bar-chart-wrapper">
                        <div className="bar-chart" ref={barChartRef}>
                          {MONTHLY_STATS.map((item) => (
                            <div className="bar-col" key={item.month}>
                              <div className="bar-group">
                                {(statsFilter === "all" ||
                                  statsFilter === "falling") && (
                                  <div className="bar-wrap">
                                    <div className="bar-value">
                                      {item.falling || ""}
                                    </div>
                                    <div
                                      className="bar-fill"
                                      style={{
                                        height: `${Math.round((item.falling / maxCount) * chartHeight)}px`,
                                        backgroundColor: "var(--status-danger)",
                                      }}
                                    />
                                  </div>
                                )}
                                {(statsFilter === "all" ||
                                  statsFilter === "intrusion") && (
                                  <div className="bar-wrap">
                                    <div className="bar-value">
                                      {item.intrusion || ""}
                                    </div>
                                    <div
                                      className="bar-fill"
                                      style={{
                                        height: `${Math.round((item.intrusion / maxCount) * chartHeight)}px`,
                                        backgroundColor: "var(--accent-color)",
                                      }}
                                    />
                                  </div>
                                )}
                                {(statsFilter === "all" ||
                                  statsFilter === "sensor") && (
                                  <div className="bar-wrap">
                                    <div className="bar-value">
                                      {item.sensor || ""}
                                    </div>
                                    <div
                                      className="bar-fill"
                                      style={{
                                        height: `${Math.round((item.sensor / maxCount) * chartHeight)}px`,
                                        backgroundColor: "#3b82f6",
                                      }}
                                    />
                                  </div>
                                )}
                              </div>
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
          </div>
        </div>
      )}

      {/* 테스트 운행 팝업 모달 */}
      {showTestRun && (
        <div className="test-run-overlay" onClick={() => setShowTestRun(false)}>
          <div className="test-run-popup" onClick={(e) => e.stopPropagation()}>
            <div className="test-run-popup-header">
              <h3>테스트 운행</h3>
              <button
                className="modal-close-btn"
                onClick={() => setShowTestRun(false)}
              >
                &times;
              </button>
            </div>
            <div className="test-run-popup-body">
              <div className="test-speed-display">
                <div className="speed-box">
                  <span className="label">설정 목표</span>
                  <span className="value">{testSpeedInput}%</span>
                </div>
                <div className="speed-box">
                  <span className="label">현재 속도</span>
                  <span className="value current">
                    {isTestMode ? `${testSpeed}%` : "-"}
                  </span>
                </div>
              </div>
              <div className="test-run-actions">
                <button
                  disabled={loading || !isStopped || isLocked}
                  onClick={startTestRun}
                >
                  테스트 운행 시작
                </button>
                <button disabled={loading || !isTestMode} onClick={stopTestRun}>
                  테스트 종료
                </button>
              </div>
              <div className="test-speed-row">
                <label htmlFor="test-speed-range">테스트 속도 설정</label>
                <input
                  id="test-speed-range"
                  type="range"
                  min="0"
                  max="100"
                  step="5"
                  value={testSpeedInput}
                  disabled={!isTestMode || loading}
                  onChange={(e) => setTestSpeedInput(Number(e.target.value))}
                />
                <button
                  disabled={loading || !isTestMode}
                  onClick={applyTestSpeed}
                >
                  속도 즉시 적용
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 위험구역 설정 팝업 모달 */}
      {isDangerMode && (
        <div className="danger-zone-overlay" onClick={exitDangerMode}>
          <div
            className="danger-zone-popup"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="danger-zone-popup-header">
              <h3>⚠ 위험구역 설정</h3>
              <button className="modal-close-btn" onClick={exitDangerMode}>
                &times;
              </button>
            </div>
            <div className="danger-zone-popup-body">
              <ZoneConfigPanel
                zones={zones}
                selected={selectedZoneId}
                onSelect={setSelectedZoneId}
                currentAction={configAction}
                onActionSelect={setConfigAction}
                onDelete={handleDeleteZone}
                onCancel={exitDangerMode}
                newZoneName={newZoneName}
                onNameChange={setNewZoneName}
                loading={loading}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;
