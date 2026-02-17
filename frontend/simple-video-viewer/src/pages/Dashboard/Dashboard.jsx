import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut } from 'lucide-react';

import LiveStreamContent from '../../components/dashboard/LiveStreamContent';
import VideoLogTable from '../../components/dashboard/VideoLogTable';
import DangerZoneSelector from '../../components/dashboard/DangerZoneSelector';
import ConveyorMode from '../../components/dashboard/ConveyorMode';
import ZoneConfigPanel from '../../components/dashboard/ZoneConfigPanel';
import ZoneOverlay from '../../components/dashboard/ZoneOverlay';

import useDashboardStore from '../../store/useDashboardStore';

import './Dashboard.css';

const ErrorPopup = ({ message, onClose }) => {
  if (!message) return null;
  return (
    <div className="error-popup-overlay">
      <div className="error-popup">
        <div className="error-popup-header">
          <span>⚠️ 작업 실패 ⚠️</span>
          <button onClick={onClose}>&times;</button>
        </div>
        <div className="error-popup-content">{message}</div>
      </div>
    </div>
  );
};

const LogoutModal = ({ onConfirm, onCancel }) => (
  <div className="logout-overlay">
    <div className="logout-modal">
      <div className="logout-title">로그아웃 하시겠습니까?</div>
      <div className="logout-buttons">
        <button className="logout-yes" onClick={onConfirm}>네</button>
        <button className="logout-no" onClick={onCancel}>아니요</button>
      </div>
    </div>
  </div>
);

const videoStatusText = {
  idle: '영상 준비 중',
  waiting_offer: 'Offer 대기 중',
  connecting: 'WebRTC 연결 중',
  connected: '영상 연결됨',
  reconnecting: '영상 재연결 중',
  failed: '영상 연결 실패',
};

export default function Dashboard() {
  const {
    logs,
    zones,
    operationMode,
    loading,
    error,
    popupError,
    globalAlert,
    isLocked,
    activeId,
    isDangerMode,
    configAction,
    newZoneName,
    selectedZoneId,
    wsStatus,
    videoStatus,
    currentTime,
    imageSize,
    initialize,
    setActiveId,
    handleControl,
    resetSystem,
    enterDangerMode,
    exitDangerMode,
    setConfigAction,
    setSelectedZoneId,
    setNewZoneName,
    setImageSize,
    handleCreateZone,
    handleUpdateZone,
    handleDeleteZone,
    setPopupError,
    setVideoStatus,
    testLotoCondition,
  } = useDashboardStore();

  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    initialize();
    return () => {
      useDashboardStore.getState().disconnect();
    };
  }, [initialize]);

  const [username, setUsername] = useState('');
  useEffect(() => {
    const savedUsername = localStorage.getItem('username') || 'admin';
    setUsername(savedUsername);
  }, []);

  return (
    <div className="dashboard">
      <div className="header-bar">
        <div className="header-left">
          <div className="logo">Conveyor Guard</div>
          <div className="factory-label">경기대 가상 공장</div>
        </div>
        <div className="right-info">
          <div className="date-time">{currentTime}</div>
          <div className="user-label">🧑‍💻 {username}(admin)</div>
          <button className="logout-btn" onClick={() => setShowLogoutModal(true)}>
            <LogOut size={18} /> Logout
          </button>
        </div>
      </div>

      <div className="ws-status" style={{ display: 'flex', gap: 12 }}>
        <span>
          {wsStatus === 'connecting' && '🔄 로그 채널 연결 중'}
          {wsStatus === 'open' && '✅ 로그 채널 연결됨'}
          {wsStatus === 'closed' && '⛔ 로그 채널 연결 끊김'}
          {wsStatus === 'error' && '❌ 로그 채널 오류'}
        </span>
        <span>
          🎥 {videoStatusText[videoStatus] || videoStatusText.idle}
        </span>
      </div>

      <div className="main-layout">
        <div className="stream-panel">
          <div className="live-stream-wrapper">
            {isDangerMode && (configAction === 'create' || configAction === 'update') ? (
              <DangerZoneSelector
                onComplete={configAction === 'create' ? handleCreateZone : handleUpdateZone}
                onImageLoad={setImageSize}
              />
            ) : (
              <div style={{ position: 'relative', width: '100%', height: '100%' }}>
                <LiveStreamContent
                  eventId={activeId}
                  onImageLoad={setImageSize}
                  onStatusChange={setVideoStatus}
                />
                <ZoneOverlay
                  zones={zones}
                  selectedZoneId={selectedZoneId}
                  imageSize={imageSize}
                />
              </div>
            )}
          </div>
        </div>

        <div className="control-panel">
          {isLocked ? (
            <div className="system-locked-panel">
              <div className="system-locked-title">SYSTEM LOCKED</div>
              <p className="system-locked-message">
                치명적인 위험이 감지되어 시스템이 비상 정지되었습니다. 관리자의 확인 후 시스템을 리셋하세요.
              </p>
              <button
                className="system-reset-btn"
                onClick={resetSystem}
                disabled={loading}
              >
                {loading ? '리셋 중...' : '🚨 시스템 리셋'}
              </button>
            </div>
          ) : loading ? (
            <div className="loading">로딩 중…</div>
          ) : error ? (
            <div className="error">{error}</div>
          ) : !isDangerMode ? (
            <>
              <div className="emergency-response-panel">
                <button
                  className="emergency-stop-btn"
                  onClick={() => handleControl('stop')}
                  disabled={loading}
                >
                  🚨 긴급 정지
                </button>
              </div>

              <ConveyorMode
                className="control-board"
                operationMode={operationMode}
                loading={loading}
                onStartAutomatic={() => handleControl('start_automatic')}
                onStartMaintenance={() => handleControl('start_maintenance')}
                onStop={() => handleControl('stop')}
                onDangerMode={enterDangerMode}
              />

              <button
                onClick={testLotoCondition}
                style={{
                  marginTop: '10px',
                  background: '#777',
                  color: 'white',
                  border: 'none',
                  padding: '10px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                }}
              >
                [DEBUG] LOTO 테스트 상태 만들기
              </button>

              <VideoLogTable
                className="log-board"
                logs={logs}
                activeId={activeId}
                onSelect={setActiveId}
              />
            </>
          ) : (
            <ZoneConfigPanel
              zones={zones}
              selected={selectedZoneId}
              onSelect={setSelectedZoneId}
              currentAction={configAction}
              onActionSelect={setConfigAction}
              newZoneName={newZoneName}
              onNameChange={setNewZoneName}
              onDelete={handleDeleteZone}
              onCancel={exitDangerMode}
            />
          )}
        </div>
      </div>

      {globalAlert && (
        <div className={`global-alert ${globalAlert.log_risk_level?.toLowerCase()}`}>
          <div className="global-alert-content">
            <h2>{globalAlert.log_risk_level}</h2>
            <p>{globalAlert.details?.description || '긴급 상황 발생!'}</p>
            <span>({new Date(globalAlert.timestamp).toLocaleTimeString()})</span>
          </div>
        </div>
      )}

      <ErrorPopup message={popupError} onClose={() => setPopupError(null)} />

      {showLogoutModal && (
        <LogoutModal
          onConfirm={() => {
            localStorage.clear();
            navigate('/login');
          }}
          onCancel={() => setShowLogoutModal(false)}
        />
      )}
    </div>
  );
}
