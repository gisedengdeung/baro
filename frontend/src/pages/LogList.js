import React, { useEffect, useState } from 'react';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

function renderDetails(details) {
  if (!details) {
    return '-';
  }
  if (typeof details.description === 'string' && details.description.length > 0) {
    return details.description;
  }
  try {
    return JSON.stringify(details);
  } catch (e) {
    return String(details);
  }
}

function LogList() {
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchPastLogs = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/logs?limit=50`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        setLogs(data);
      } catch (e) {
        console.error('과거 로그를 불러오는 중 에러 발생:', e);
        setError(e.message);
      }
    };

    fetchPastLogs();
  }, []);

  if (error) {
    return <div style={{ color: 'red' }}>에러: {error}</div>;
  }

  return (
    <div className="log-list-container">
      <h2>과거 이벤트 로그 (최신 50개)</h2>
      <div className="log-list">
        {logs.length > 0 ? (
          logs.map((log, index) => {
            const level = (log.log_risk_level || log.risk_level || 'info').toLowerCase();
            const timestamp = log.timestamp ? new Date(log.timestamp).toLocaleString() : '-';
            return (
              <p key={`${log.event_type || 'LOG'}-${timestamp}-${index}`} className={`log-message log-${level}`}>
                <strong>[{timestamp}]</strong>
                <span> - {log.event_type || 'UNKNOWN'} (위험도: {log.log_risk_level || log.risk_level || '-'})</span>
                <span style={{ display: 'block', fontSize: '0.8em', opacity: 0.8 }}>
                  &nbsp;&nbsp;상세: {renderDetails(log.details)}
                </span>
              </p>
            );
          })
        ) : (
          <p>표시할 과거 로그가 없습니다.</p>
        )}
      </div>
    </div>
  );
}

export default LogList;
