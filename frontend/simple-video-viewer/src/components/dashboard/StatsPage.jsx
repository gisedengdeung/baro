// src/components/dashboard/StatsPage.jsx
import React, { useState, useEffect, useRef, useMemo } from "react";
import "./StatsPage.css";

const GAUGE_ITEMS = (summary) => [
  { label: "총 발생", value: summary.total, color: "#6366f1" },
  {
    label: "넘어짐 감지",
    value: summary.falling,
    color: "var(--status-danger)",
  },
  {
    label: "위험구역 접근",
    value: summary.intrusion,
    color: "var(--accent-color)",
  },
  { label: "화재 감지", value: summary.sensor, color: "#3b82f6" },
];

const FILTER_ITEMS = [
  { id: "all", label: "전체", color: "var(--text-secondary)" },
  { id: "falling", label: "넘어짐 감지", color: "var(--status-danger)" },
  { id: "intrusion", label: "위험구역 접근", color: "var(--accent-color)" },
  { id: "sensor", label: "화재 감지", color: "#3b82f6" },
];

function Gauge({ label, value, max, color }) {
  const angle = Math.min((value / max) * 100, 100) * 1.8;
  const r = 36,
    cx = 44,
    cy = 44;
  const toRad = (d) => (d * Math.PI) / 180;
  const x1 = cx + r * Math.cos(toRad(180));
  const y1 = cy + r * Math.sin(toRad(180));
  const x2 = cx + r * Math.cos(toRad(180 + angle));
  const y2 = cy + r * Math.sin(toRad(180 + angle));

  return (
    <div className="sp-gauge-item">
      <svg viewBox="0 0 88 50" className="sp-gauge-svg">
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          stroke="#374151"
          strokeWidth="8"
          strokeLinecap="round"
        />
        {value > 0 && (
          <path
            d={`M ${x1} ${y1} A ${r} ${r} 0 ${angle > 180 ? 1 : 0} 1 ${x2} ${y2}`}
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeLinecap="round"
          />
        )}
        <text
          x={cx}
          y={cy - 2}
          textAnchor="middle"
          fontSize="13"
          fontWeight="bold"
          fill={color}
        >
          {value}
        </text>
        <text
          x={cx}
          y={cy + 10}
          textAnchor="middle"
          fontSize="8"
          fill="#9ca3af"
        >
          건
        </text>
      </svg>
      <div className="sp-gauge-label">{label}</div>
    </div>
  );
}

export default function StatsPage({ logs }) {
  const [statsFilter, setStatsFilter] = useState("all");
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [chartHeight, setChartHeight] = useState(300);
  const barChartRef = useRef(null);
  const maxCount = 50;

  const detectionSummary = useMemo(() => {
    const total = logs.filter((l) =>
      [
        "LOG_CRITICAL_FALLING",
        "LOG_INTRUSION_SLOWDOWN",
        "LOG_CRITICAL_SENSOR",
      ].includes(l.event_type),
    ).length;
    const falling = logs.filter(
      (l) => l.event_type === "LOG_CRITICAL_FALLING",
    ).length;
    const intrusion = logs.filter(
      (l) => l.event_type === "LOG_INTRUSION_SLOWDOWN",
    ).length;
    const sensor = logs.filter(
      (l) => l.event_type === "LOG_CRITICAL_SENSOR",
    ).length;
    return { total, falling, intrusion, sensor };
  }, [logs]);

  const monthlyStats = useMemo(() => {
    const counts = Array.from({ length: 12 }, (_, i) => ({
      month: `${i + 1}월`,
      falling: 0,
      intrusion: 0,
      sensor: 0,
    }));
    logs.forEach((log) => {
      const date = new Date(log.timestamp);
      if (date.getFullYear() !== selectedYear) return;
      const m = date.getMonth();
      if (log.event_type === "LOG_CRITICAL_FALLING") counts[m].falling += 1;
      else if (log.event_type === "LOG_INTRUSION_SLOWDOWN")
        counts[m].intrusion += 1;
      else if (log.event_type === "LOG_CRITICAL_SENSOR") counts[m].sensor += 1;
    });
    return counts;
  }, [logs, selectedYear]);

  useEffect(() => {
    if (!barChartRef.current) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setChartHeight(Math.max(entry.contentRect.height - 67, 40));
      }
    });
    ro.observe(barChartRef.current);
    return () => ro.disconnect();
  }, []);

  return (
    <main className="sp-page">
      <div className="sp-inner">
        <h2 className="sp-page-title">통계</h2>

        {/* 전체 감지 내역 */}
        <section className="sp-summary">
          <h3 className="sp-section-title">전체 감지 내역</h3>
          <p className="sp-summary-sub">전체 기간 · 모든 이벤트</p>
          <div className="sp-gauge-list">
            {GAUGE_ITEMS(detectionSummary).map(({ label, value, color }) => (
              <Gauge
                key={label}
                label={label}
                value={value}
                max={detectionSummary.total || 1}
                color={color}
              />
            ))}
          </div>
        </section>

        <div className="sp-divider" />

        {/* 월별 위험 이벤트 */}
        <section className="sp-chart-section">
          <div className="sp-chart-header">
            <h3 className="sp-section-title">월별 위험 이벤트</h3>
            <div className="sp-year-selector">
              <button
                className="sp-year-btn"
                onClick={() => setSelectedYear((y) => y - 1)}
              >
                ◀
              </button>
              <span className="sp-year-label">{selectedYear}년</span>
              <button
                className="sp-year-btn"
                disabled={selectedYear >= new Date().getFullYear()}
                onClick={() => setSelectedYear((y) => y + 1)}
              >
                ▶
              </button>
            </div>
          </div>

          <div className="sp-legend">
            {FILTER_ITEMS.map(({ id, label, color }) => (
              <span
                key={id}
                className={`sp-legend-btn ${statsFilter === id ? "active" : ""}`}
                onClick={() => setStatsFilter(id)}
              >
                <span className="sp-legend-dot" style={{ background: color }} />
                {label}
              </span>
            ))}
          </div>

          <div className="sp-chart-area">
            <div className="sp-y-axis">
              {Array.from({ length: 10 }, (_, i) => (
                <div key={i} className="sp-y-tick">
                  <span className="sp-y-tick-label">{50 - i * 5}</span>
                  <span className="sp-y-tick-line" />
                </div>
              ))}
              <div className="sp-y-tick">
                <span className="sp-y-tick-label">0</span>
                <span className="sp-y-tick-line" />
              </div>
            </div>
            <div className="sp-bar-wrapper">
              <div className="sp-bar-chart" ref={barChartRef}>
                {monthlyStats.map((item) => (
                  <div className="sp-bar-col" key={item.month}>
                    <div className="sp-bar-group">
                      {(statsFilter === "all" || statsFilter === "falling") && (
                        <div className="sp-bar-wrap">
                          <div className="sp-bar-value">
                            {item.falling || ""}
                          </div>
                          <div
                            className="sp-bar-fill"
                            style={{
                              height: `${Math.round((item.falling / maxCount) * chartHeight)}px`,
                              backgroundColor: "var(--status-danger)",
                            }}
                          />
                        </div>
                      )}
                      {(statsFilter === "all" ||
                        statsFilter === "intrusion") && (
                        <div className="sp-bar-wrap">
                          <div className="sp-bar-value">
                            {item.intrusion || ""}
                          </div>
                          <div
                            className="sp-bar-fill"
                            style={{
                              height: `${Math.round((item.intrusion / maxCount) * chartHeight)}px`,
                              backgroundColor: "var(--accent-color)",
                            }}
                          />
                        </div>
                      )}
                      {(statsFilter === "all" || statsFilter === "sensor") && (
                        <div className="sp-bar-wrap">
                          <div className="sp-bar-value">
                            {item.sensor || ""}
                          </div>
                          <div
                            className="sp-bar-fill"
                            style={{
                              height: `${Math.round((item.sensor / maxCount) * chartHeight)}px`,
                              backgroundColor: "#3b82f6",
                            }}
                          />
                        </div>
                      )}
                    </div>
                    <div className="sp-bar-label">{item.month}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
