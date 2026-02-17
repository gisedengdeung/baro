import React, { useRef, useState, useEffect } from 'react';
import LiveStreamContent from './LiveStreamContent';
import './DangerZoneSelector.css';

export default function DangerZoneSelector({ eventId, onComplete, onImageLoad }) {
  const canvasRef = useRef(null);
  const [points, setPoints] = useState([]);
  const [hasImageInfo, setHasImageInfo] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;

    if (canvas.width !== rect.width * dpr || canvas.height !== rect.height * dpr) {
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
    }

    ctx.clearRect(0, 0, rect.width, rect.height);

    ctx.fillStyle = 'rgba(255, 0, 0, 0.7)';
    points.forEach((p) => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
      ctx.fill();
    });

    if (points.length >= 2) {
      ctx.strokeStyle = 'rgba(255, 0, 0, 0.9)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      points.slice(1).forEach((p) => ctx.lineTo(p.x, p.y));
      if (points.length >= 3) {
        ctx.closePath();
        ctx.fillStyle = 'rgba(255, 0, 0, 0.2)';
        ctx.fill();
      }
      ctx.stroke();
    }
  }, [points]);

  const handleCanvasClick = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setPoints((prevPoints) => [...prevPoints, { x, y }]);
  };

  const handleComplete = () => {
    if (!hasImageInfo) {
      alert('영상 해상도 정보를 아직 받지 못했습니다. 잠시 후 다시 시도하세요.');
      return;
    }

    if (points.length < 3) {
      alert('위험 구역을 설정하려면 최소 3개 이상의 점을 찍어야 합니다.');
      return;
    }

    const rect = canvasRef.current.getBoundingClientRect();
    const ratioPoints = points.map((p) => ({
      x: p.x / rect.width,
      y: p.y / rect.height,
    }));
    onComplete(ratioPoints);
  };

  const handleClear = () => {
    setPoints([]);
  };

  const handleImageLoad = (size) => {
    setHasImageInfo(Boolean(size?.naturalWidth && size?.naturalHeight));
    if (onImageLoad) {
      onImageLoad(size);
    }
  };

  return (
    <div className="dz-wrapper">
      <LiveStreamContent eventId={eventId} onImageLoad={handleImageLoad} />

      <canvas
        ref={canvasRef}
        className="dz-canvas"
        onClick={handleCanvasClick}
      />

      <div className="dz-controls">
        <p className="dz-info-text">영역을 클릭하여 점을 추가하세요.</p>
        <button
          onClick={handleComplete}
          className="dz-btn dz-btn-complete"
          disabled={!hasImageInfo || points.length < 3}
        >
          완료
        </button>
        <button onClick={handleClear} className="dz-btn dz-btn-clear">초기화</button>
      </div>
    </div>
  );
}
