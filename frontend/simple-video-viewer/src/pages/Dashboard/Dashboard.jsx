import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useShallow } from 'zustand/react/shallow';

import LiveStreamContent from '../../components/dashboard/LiveStreamContent';
import ConveyorMode from '../../components/dashboard/ConveyorMode';
import VideoLogTable from '../../components/dashboard/VideoLogTable';
import { logAPI } from '../../services/api';
import useAuthStore from '../../store/useAuthStore';
import useDashboardStore from '../../store/useDashboardStore';
import './Dashboard.css';

const CLIP_STATUS_MESSAGE = {
  NONE: '이 로그에는 저장된 클립이 없습니다.',
  PENDING: '클립을 생성 중입니다. 잠시 후 다시 시도하세요.',
  FAILED: '클립 생성에 실패했습니다.',
  EXPIRED: '클립 보관 기간(7일)이 만료되었습니다.',
};

const MODE_TEXT = {
  AUTOMATIC: '운전 모드',
  MAINTENANCE: '정비 모드',
  STOPPED: '정지',
};

const formatLogTimestamp = (value) => {
  if (!value) return '-';
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return String(value);
  return dt.toLocaleString('ko-KR');
};

export default function Dashboard() {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);

  const {
    logs,
    activeId,
    operationMode,
    loading,
    wsStatus,
    videoStatus,
    currentTime,
    popupError,
    initialize,
    disconnect,
    setActiveId,
    setPopupError,
    setVideoStatus,
    handleControl,
    resetSystem,
  } = useDashboardStore(
    useShallow((state) => ({
      logs: state.logs,
      activeId: state.activeId,
      operationMode: state.operationMode,
      loading: state.loading,
      wsStatus: state.wsStatus,
      videoStatus: state.videoStatus,
      currentTime: state.currentTime,
      popupError: state.popupError,
      initialize: state.initialize,
      disconnect: state.disconnect,
      setActiveId: state.setActiveId,
      setPopupError: state.setPopupError,
      setVideoStatus: state.setVideoStatus,
      handleControl: state.handleControl,
      resetSystem: state.resetSystem,
    }))
  );

  const [clipLoading, setClipLoading] = useState(false);
  const [clipModal, setClipModal] = useState({
    open: false,
    url: '',
    title: '',
  });

  useEffect(() => {
    document.body.classList.add('dashboard-body-no-scroll');
    initialize();
    return () => {
      document.body.classList.remove('dashboard-body-no-scroll');
      disconnect();
    };
  }, [initialize, disconnect]);

  useEffect(() => {
    return () => {
      if (clipModal.url) {
        URL.revokeObjectURL(clipModal.url);
      }
    };
  }, [clipModal.url]);

  const closeClipModal = useCallback(() => {
    setClipModal((prev) => {
      if (prev.url) {
        URL.revokeObjectURL(prev.url);
      }
      return { open: false, url: '', title: '' };
    });
  }, []);

  const handleLogout = useCallback(async () => {
    await logout();
    navigate('/login', { replace: true });
  }, [logout, navigate]);

  const handleLogSelect = useCallback(
    async (logId) => {
      setActiveId(logId);
      const target = logs.find((log) => log.id === logId);
      if (!target) {
        return;
      }

      const clipStatus = (target.clip_status || 'NONE').toUpperCase();
      if (clipStatus !== 'READY') {
        setPopupError(CLIP_STATUS_MESSAGE[clipStatus] || `클립 상태: ${clipStatus}`);
        return;
      }

      try {
        setClipLoading(true);
        const blob = await logAPI.getClipBlob(logId);
        const nextUrl = URL.createObjectURL(blob);
        setClipModal((prev) => {
          if (prev.url) {
            URL.revokeObjectURL(prev.url);
          }
          return {
            open: true,
            url: nextUrl,
            title: `${target.event_type} / ${formatLogTimestamp(target.timestamp)}`,
          };
        });
      } catch (error) {
        const detail = error?.response?.data?.detail || '클립을 불러오지 못했습니다.';
        setPopupError(typeof detail === 'string' ? detail : '클립을 불러오지 못했습니다.');
      } finally {
        setClipLoading(false);
      }
    },
    [logs, setActiveId, setPopupError]
  );

  const modeText = useMemo(
    () => MODE_TEXT[operationMode] || operationMode || '불러오는 중...',
    [operationMode]
  );

  return (
    <div className="dashboard">
      <header className="header-bar">
        <div className="header-left">
          <div className="logo">Conveyor Guard</div>
          <div className="factory-label">실시간 안전 모니터링</div>
        </div>
        <div className="right-info">
          <div className="date-time">{currentTime}</div>
          <div className="status-pill">WS: {wsStatus}</div>
          <div className="status-pill">VIDEO: {videoStatus}</div>
          <div className="user-label">{user?.email || 'admin'}</div>
          <button className="logout-btn" onClick={handleLogout}>Logout</button>
        </div>
      </header>

      <main className="main-layout">
        <section className="stream-panel panel-card">
          <div className="section-title-row">
            <h3>라이브 영상</h3>
            <span className="mode-badge">{modeText}</span>
          </div>
          <div className="live-frame">
            <LiveStreamContent onStatusChange={setVideoStatus} />
          </div>
        </section>

        <aside className="control-panel">
          <div className="panel-card">
            <ConveyorMode
              className="control-board"
              operationMode={operationMode}
              loading={loading}
              onStartAutomatic={() => handleControl('start_automatic')}
              onStartMaintenance={() => handleControl('start_maintenance')}
              onStop={() => handleControl('stop')}
              onDangerMode={() => setPopupError('위험 구역 편집 UI는 다음 단계에서 연결합니다.')}
            />
            <button className="reset-btn" onClick={resetSystem} disabled={loading}>
              시스템 리셋
            </button>
          </div>
          <VideoLogTable
            className="panel-card log-board"
            logs={logs}
            activeId={activeId}
            onSelect={handleLogSelect}
          />
        </aside>
      </main>

      {popupError && <div className="error-toast">{popupError}</div>}
      {clipLoading && <div className="loading-toast">클립 로딩 중...</div>}

      {clipModal.open && (
        <div className="clip-modal-backdrop" onClick={closeClipModal}>
          <div className="clip-modal" onClick={(e) => e.stopPropagation()}>
            <div className="clip-modal-header">
              <h4>{clipModal.title}</h4>
              <button className="clip-close-btn" onClick={closeClipModal}>닫기</button>
            </div>
            <video controls autoPlay src={clipModal.url} className="clip-video" />
          </div>
        </div>
      )}
    </div>
  );
}
