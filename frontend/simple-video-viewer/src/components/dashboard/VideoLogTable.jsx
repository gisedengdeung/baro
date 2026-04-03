import React, { useState } from "react";
import "./VideoLogTable.css";

const API_BASE = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

const EVENT_CONFIG = {
  LOG_CRITICAL_FALLING: { label: "넘어짐 감지", type: "critical", icon: "🔥" },
  LOG_CRITICAL_SENSOR: { label: "센서 경고", type: "critical", icon: "🔥" },
  LOG_INTRUSION_SLOWDOWN: { label: "위험 구역 침입", type: "warn", icon: "⚠️" },
  LOG_CROUCHING_WARN: { label: "웅크린 자세", type: "medium", icon: "❗" },
  LOG_LOTO_ACTIVE: { label: "LOTO 활성", type: "warn", icon: "🔒" },
  LOG_MAINTENANCE_SAFE: { label: "정비 모드 안전", type: "safe", icon: "✅" },
  LOG_NORMAL_OPERATION: { label: "정상 운전", type: "safe", icon: "ℹ️" },
};

const MODE_LABEL = {
  AUTOMATIC: "자동 운전",
  MAINTENANCE: "정비 모드",
  STOPPED: "시스템 정지",
  MANUAL: "수동 제어",
};

export default function VideoLogTable({ logs = [], activeId, onSelect }) {
  const [selectedLog, setSelectedLog] = useState(null);

  const handleVideoClick = (e, log) => {
    e.stopPropagation();
    setSelectedLog(log);
  };

  const closeVideo = () => setSelectedLog(null);

  const videoUrl = selectedLog
    ? `${API_BASE}/api/logs/${selectedLog.id}/clip`
    : null;

  return (
    <div className="vlt-layout">
      {selectedLog && (
        <div className="vlt-player-panel">
          <div className="vlt-player-header">
            <div className="vlt-player-info">
              <span className="vlt-player-title">🎥 넘어짐 감지 영상</span>
              <span className="vlt-player-time">
                {new Date(selectedLog.timestamp).toLocaleString("ko-KR")}
              </span>
            </div>
            <button className="vlt-player-close" onClick={closeVideo}>
              ✕
            </button>
          </div>
          <div className="vlt-player-body">
            <video
              key={videoUrl}
              controls
              autoPlay
              className="vlt-video"
              onError={() => alert("영상을 불러올 수 없습니다.")}
            >
              <source src={videoUrl} type="video/mp4" />
            </video>
          </div>
        </div>
      )}

      <div className="video-log-container">
        <div className="table-wrapper">
          <table className="modern-table">
            <thead>
              <tr>
                <th className="col-time">일시</th>
                <th className="col-mode">모드</th>
                <th className="col-event">이벤트 내용</th>
                <th className="col-video"></th>
                <th className="col-status">상태</th>
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 ? (
                <tr>
                  <td colSpan="5" className="empty-row">
                    표시할 로그가 없습니다.
                  </td>
                </tr>
              ) : (
                logs.map((log, idx) => {
                  const dt = new Date(log.timestamp || Date.now());
                  const timeStr = dt.toLocaleTimeString("ko-KR", {
                    hour12: false,
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  });
                  const dateStr = `${dt.getMonth() + 1}/${dt.getDate()}`;
                  const modeText =
                    MODE_LABEL[log.operation_mode] || log.operation_mode || "-";
                  const config = EVENT_CONFIG[log.event_type] || {
                    label: log.details?.description || "알 수 없는 이벤트",
                    type: "info",
                    icon: "❓",
                  };
                  const isSelected = log.id === activeId;
                  const isPlaying = selectedLog?.id === log.id;

                  return (
                    <tr
                      key={log.id || idx}
                      className={`${isSelected ? "active" : ""} ${isPlaying ? "playing" : ""}`}
                      onClick={() => onSelect && onSelect(log.id)}
                    >
                      <td className="date-cell">
                        <span className="date-small">{dateStr}</span>
                        <span className="time-bold">{timeStr}</span>
                      </td>
                      <td className="mode-cell">
                        <span
                          className={`mode-badge ${(log.operation_mode || "").toLowerCase()}`}
                        >
                          {modeText}
                        </span>
                      </td>
                      <td className="description-cell">
                        <span className="event-icon">{config.icon}</span>
                        {config.label}
                      </td>
                      <td className="video-cell">
                        {log.event_type === "LOG_CRITICAL_FALLING" &&
                          (log.has_clip ? (
                            <button
                              className={`video-btn${isPlaying ? " playing" : ""}`}
                              onClick={(e) => handleVideoClick(e, log)}
                            >
                              🎥 영상 확인
                            </button>
                          ) : (
                            <button
                              className="video-btn"
                              style={{ opacity: 0.4, cursor: "not-allowed" }}
                              disabled
                            >
                              🎥 준비 중
                            </button>
                          ))}
                      </td>
                      <td className="status-cell">
                        <span className={`status-badge ${config.type}`}>
                          {config.type.toUpperCase()}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
