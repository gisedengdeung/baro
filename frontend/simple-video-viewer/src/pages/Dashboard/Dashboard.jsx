// src/pages/Dashboard/Dashboard.jsx
import React, { useState, useEffect } from "react";
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

  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);

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
  const [isEmergencyStopped, setIsEmergencyStopped] = useState(false);
  const [showTestRun, setShowTestRun] = useState(false);

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
                onClick={() => setSidebarSection(item.id)}
              >
                <span className="sidebar-icon">{item.icon}</span>
                <span className="sidebar-label">{item.label}</span>
              </button>
            ))}
          </div>
          <div className="sidebar-bottom-nav">
            <button className="sidebar-item" onClick={handleLogout}>
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

        {/* 통계 탭 */}
        {sidebarSection === "stats" && <StatsPage logs={logs} />}

        {/* 감지내역 탭 */}
        {sidebarSection === "detections" && (
          <main className="stats-page">
            <div className="stats-page-inner">
              <h2 className="stats-page-title">전체 이벤트 로그</h2>
              <VideoLogTable logs={logs} />
            </div>
          </main>
        )}

        {/* 대시보드 탭 - 항상 마운트 유지 (WebRTC 연결 끊김 방지), 다른 탭일 때 숨김 */}
        <main
          className="main-layout"
          style={{ display: sidebarSection === "dashboard" ? "flex" : "none" }}
        >
          <section className="stream-panel">
            <div
              className="live-stream-wrapper"
              style={{ position: "relative", width: "100%", height: "100%" }}
            >
              <LiveStreamContent
                onImageLoad={setImageSize}
                onStatusChange={setVideoStatus}
              />
              <ZoneOverlay
                zones={zones}
                selectedZoneId={selectedZoneId}
                imageSize={imageSize}
              />
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
                          if (log.event_type === "LOG_MAINTENANCE_SAFE")
                            return "✅  정비 모드 안전  ✅";
                          if (log.event_type === "LOG_CRITICAL_FALLING")
                            return "🔥  넘어짐 감지  🔥";
                          if (log.event_type === "LOG_INTRUSION_SLOWDOWN")
                            return "⚠️  위험구역 침입 감지  ⚠️";
                          if (log.event_type === "LOG_NORMAL_OPERATION")
                            return "ℹ️  정상 운행  ℹ️";
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
        {/* end dashboard main-layout */}
      </div>

      {/* 테스트 운행 팝업 */}
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

      {/* 위험구역 설정 팝업 */}
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
