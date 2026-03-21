import React, { useRef, useEffect } from 'react';

export default function ZoneOverlay({ zones, selectedZoneId, imageSize }) {
  const ref = useRef(null);

  useEffect(() => {
    const draw = () => {
      const canvas = ref.current;
      if (!canvas) return;

      const ctx = canvas.getContext('2d');
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;

      // 캔버스 해상도 설정
      if (canvas.width !== rect.width * dpr || canvas.height !== rect.height * dpr) {
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
      }
      
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, rect.width, rect.height);

      if (!zones || zones.length === 0) return;

      const naturalWidth = imageSize?.naturalWidth;
      const naturalHeight = imageSize?.naturalHeight;

      zones.forEach((zone) => {
        if (!zone.points || zone.points.length < 3) return;

        const isSelected = zone.id === selectedZoneId;

        const pts = zone.points
          .map((p) => {
            // 비율 좌표(xRatio, yRatio)가 있는 경우
            if (typeof p.xRatio === 'number' && typeof p.yRatio === 'number') {
              return {
                x: p.xRatio * rect.width,
                y: p.yRatio * rect.height,
              };
            }

            // 절대 좌표(x, y)와 이미지 원본 해상도가 있는 경우
            if (
              typeof p.x === 'number' &&
              typeof p.y === 'number' &&
              naturalWidth &&
              naturalHeight
            ) {
              return {
                x: (p.x / naturalWidth) * rect.width,
                y: (p.y / naturalHeight) * rect.height,
              };
            }

            return null;
          })
          .filter(Boolean);

        if (pts.length < 3) return;

        ctx.fillStyle = isSelected ? 'rgba(255, 165, 0, 0.3)' : 'rgba(0, 255, 0, 0.2)';
        ctx.strokeStyle = isSelected ? 'rgba(255, 165, 0, 1)' : 'rgba(0, 255, 0, 0.8)';
        ctx.lineWidth = isSelected ? 3 : 2;

        ctx.beginPath();
        ctx.moveTo(pts[0].x, pts[0].y);
        pts.slice(1).forEach((pt) => ctx.lineTo(pt.x, pt.y));
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
      });
    };

    draw();
    window.addEventListener('resize', draw);
    return () => window.removeEventListener('resize', draw);
  }, [zones, selectedZoneId, imageSize]);

  return (
    <canvas
      ref={ref}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 5,
      }}
    />
  );
}
