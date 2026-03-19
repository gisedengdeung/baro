import React, { useEffect } from 'react';
import { useWebRTC } from '../../hooks/useWebRTC';
import '../../pages/Dashboard/Dashboard.css';

const STATUS_TEXT = {
  idle: '영상 연결 준비 중',
  waiting_offer: 'Edge 영상 Offer 대기 중',
  connecting: 'WebRTC 연결 중',
  connected: '영상 연결됨',
  reconnecting: '영상 재연결 시도 중',
  failed: '영상 연결 실패. Edge 실행 상태와 signaling API를 확인하세요.',
};

export default function LiveStreamContent({ onImageLoad, onStatusChange }) {
  const { 
    videoRef, 
    status, 
    handleLoadedMetadata 
  } = useWebRTC(onImageLoad);

  // 상태 변화를 부모에게 알림
  useEffect(() => {
    if (onStatusChange) {
      onStatusChange(status);
    }
  }, [status, onStatusChange]);

  const showOverlay = status !== 'connected';

  return (
    <div className="live-stream-container" style={{ position: 'relative', width: '100%', height: '100%' }}>
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        style={{ width: '100%', height: '100%', objectFit: 'contain', background: '#000' }}
        onLoadedMetadata={handleLoadedMetadata}
      />

      {showOverlay && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'rgba(0,0,0,0.55)',
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            textAlign: 'center',
            padding: '16px',
            fontSize: '14px',
            lineHeight: 1.4,
            zIndex: 10,
          }}
        >
          {STATUS_TEXT[status] || STATUS_TEXT.idle}
        </div>
      )}
    </div>
  );
}
