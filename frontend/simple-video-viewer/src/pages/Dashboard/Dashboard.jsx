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
import "./Dashboard.css";

function Dashboard() {
  const navigate = useNavigate();

  // Auth Store
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);

  // Dashboard Store - System State
  const {
    logs,
    operationMode,
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
  const [hour12, setHour12] = useState(true);
  const [showLogs, setShowLogs] = useState(false);
  const [isEmergencyStopped, setIsEmergencyStopped] = useState(false);
  const [showTestRun, setShowTestRun] = useState(false);
  const [modalTab, setModalTab] = useState("logs");
  const [tabDirection, setTabDirection] = useState(null);
  const [isAnimating, setIsAnimating] = useState(false);

  const switchTab = (tab) => {
    if (tab === modalTab || isAnimating) return;
    const dir = tab === "stats" ? "left" : "right";
    setTabDirection(dir);
    setIsAnimating(true);
    setModalTab(tab);
    setTimeout(() => setIsAnimating(false), 350);
  };

  // 월별 위험도 데이터 (임시)
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
  const maxDanger = Math.max(...MONTHLY_STATS.map((d) => d.danger));
  const barChartRef = useRef(null);
  const [chartHeight, setChartHeight] = useState(193);

  useEffect(() => {
    if (!barChartRef.current) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const usable = entry.contentRect.height - 20 - 22 - 25;
        setChartHeight(Math.max(usable, 40));
      }
    });
    ro.observe(barChartRef.current);
    return () => ro.disconnect();
  }, []);

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

  return (
    <div className="dashboard">
      <header className="header-bar">
        <div className="header-left">
          <div className="logo">STOP</div>
          <div className="factory-label">Subtitle</div>
        </div>
        <div className="right-info">
          <div className="date-time">{currentTime.split(" / ")[0]}</div>
          <div className="user-label">
            🧑‍💻 {user?.role || "user"} ({user?.email})
          </div>
          <button className="logout-btn" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

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
                  {globalAlert.details?.description || globalAlert.event_type}
                </div>
                <div className="global-alert-desc-sub">
                  관리자의 확인 후 시스템을 리셋하세요.
                </div>
                <div className="global-alert-time">
                  {new Date(globalAlert.timestamp).toLocaleTimeString("ko-KR", {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })}
                </div>
                <button
                  className="alert-reset-btn"
                  disabled={loading}
                  onClick={() => {
                    resetSystem();
                    useDashboardStore.setState({ globalAlert: null });
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

            <div className={`panel-card system-status status-${systemStatus}`}>
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
                onClick={() => handleControl("start_automatic")}
              >
                컨베이어 운행
              </button>

              <button
                disabled={loading || isDangerMode}
                onClick={() => handleControl("stop")}
              >
                컨베이어 정지
              </button>
              <button
                disabled={loading || isDangerMode}
                onClick={() => handleControl("start_maintenance")}
              >
                정비 모드
              </button>
              <button
                className={isDangerMode ? "active" : ""}
                disabled={loading}
                onClick={isDangerMode ? exitDangerMode : enterDangerMode}
              >
                위험구역 설정
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
                          raw.startsWith("A person falling has been detected")
                        )
                          return "🔥  넘어짐 감지  🔥";
                        if (
                          raw.startsWith("Person detected in danger zone(s):")
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
