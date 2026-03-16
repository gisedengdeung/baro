import React from 'react';
import './VideoLogTable.css';

// event_type → 한글 라벨 및 스타일 매핑
const EVENT_CONFIG = {
  LOG_CRITICAL_FALLING:   { label: '넘어짐 감지',   type: 'critical', icon: '🔥' },
  LOG_CRITICAL_SENSOR:    { label: '센서 경고',     type: 'critical', icon: '🔥' },
  LOG_INTRUSION_SLOWDOWN: { label: '위험 구역 침입', type: 'high',     icon: '⚠️' },
  LOG_CROUCHING_WARN:     { label: '웅크린 자세',   type: 'medium',   icon: '❗' },
  LOG_LOTO_ACTIVE:        { label: 'LOTO 활성',    type: 'high',     icon: '🔒' },
  LOG_MAINTENANCE_SAFE:   { label: '정비 모드 안전', type: 'safe',     icon: '✅' },
  LOG_NORMAL_OPERATION:   { label: '정상 운전',     type: 'safe',     icon: 'ℹ️' },
};

// operation_mode → 한글 라벨 매핑
const MODE_LABEL = {
  AUTOMATIC: '자동 운전',
  MAINTENANCE: '정비 모드',
  STOPPED: '시스템 정지',
  MANUAL: '수동 제어',
};

export default function VideoLogTable({ logs = [], activeId, onSelect }) {
  return (
    <div className="video-log-container">
      <div className="table-wrapper">
        <table className="modern-table">
          <thead>
            <tr>
              <th className="col-time">일시</th>
              <th className="col-mode">모드</th>
              <th className="col-event">이벤트 내용</th>
              <th className="col-status">상태</th>
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 ? (
              <tr>
                <td colSpan="4" className="empty-row">표시할 로그가 없습니다.</td>
              </tr>
            ) : (
              logs.map((log, idx) => {
                const dt = new Date(log.timestamp || Date.now());
                const timeStr = dt.toLocaleTimeString('ko-KR', {
                  hour12: false,
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit'
                });
                const dateStr = `${dt.getMonth() + 1}/${dt.getDate()}`;

                const modeText = MODE_LABEL[log.operation_mode] || log.operation_mode || '-';
                const config = EVENT_CONFIG[log.event_type] || { label: log.details?.description || '알 수 없는 이벤트', type: 'info', icon: '❓' };
                
                const isSelected = log.id === activeId;

                return (
                  <tr
                    key={log.id || idx}
                    className={`${isSelected ? 'active' : ''}`}
                    onClick={() => onSelect && onSelect(log.id)}
                  >
                    <td className="date-cell">
                      <span className="date-small">{dateStr}</span>
                      <span className="time-bold">{timeStr}</span>
                    </td>
                    <td className="mode-cell">
                      <span className={`mode-badge ${(log.operation_mode || '').toLowerCase()}`}>
                        {modeText}
                      </span>
                    </td>
                    <td className="description-cell">
                      <span className="event-icon">{config.icon}</span>
                      {config.label}
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
  );
}
