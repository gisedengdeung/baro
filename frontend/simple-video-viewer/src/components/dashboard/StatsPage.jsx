// src/components/dashboard/StatsPage.jsx
import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { runtimeConfig, safetyAPI } from "../../services/api";
import "./StatsPage.css";

const ALL_EVENT_IDS = [
  "LOG_CRITICAL_FALLING",
  "LOG_INTRUSION_SLOWDOWN",
  "LOG_CRITICAL_SENSOR",
];

const EVENT_TYPES = [
  { id: "LOG_CRITICAL_FALLING", label: "넘어짐 감지", color: "#8b5cf6" },
  { id: "LOG_INTRUSION_SLOWDOWN", label: "위험구역 접근", color: "#ef4444" },
  { id: "LOG_CRITICAL_SENSOR", label: "끼임 감지", color: "#f59e0b" },
];

const ZONE_PALETTE = [
  "#ef4444",
  "#f59e0b",
  "#3b82f6",
  "#8b5cf6",
  "#10b981",
  "#ec4899",
  "#f97316",
];
const DAYS = ["일", "월", "화", "수", "목", "금", "토"];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

const EVENT_LABELS = {
  LOG_CRITICAL_FALLING: "넘어짐 감지",
  LOG_INTRUSION_SLOWDOWN: "위험구역 접근",
  LOG_CRITICAL_SENSOR: "끼임 감지",
};

function scoreColor(score) {
  if (score >= 80) return "ok";
  if (score >= 60) return "warning";
  return "danger";
}

function formatEventTime(timestamp) {
  if (!timestamp) return "-";
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return timestamp;
  return date.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" });
}

function weatherText(weather) {
  if (!weather) return "ASOS 기록 없음";
  const parts = [];
  if (weather.avg_temp !== null && weather.avg_temp !== undefined) parts.push(`평균 ${weather.avg_temp}도`);
  if (weather.min_temp !== null && weather.min_temp !== undefined && weather.max_temp !== null && weather.max_temp !== undefined) {
    parts.push(`${weather.min_temp}~${weather.max_temp}도`);
  }
  if (weather.avg_humidity !== null && weather.avg_humidity !== undefined) parts.push(`습도 ${weather.avg_humidity}%`);
  if (weather.max_wind !== null && weather.max_wind !== undefined) parts.push(`최대풍속 ${weather.max_wind}m/s`);
  if (weather.total_rain !== null && weather.total_rain !== undefined) parts.push(`강수 ${weather.total_rain}mm`);
  return parts.length > 0 ? parts.join(" · ") : "ASOS 값 없음";
}

function formatDeduction(value) {
  const num = Number(value ?? 0);
  if (!Number.isFinite(num)) return "0";
  return Number.isInteger(num) ? String(num) : num.toFixed(1);
}

function DailySafetyReport({ report, onRefreshAsos, refreshingAsosDate }) {
  const [expandedDates, setExpandedDates] = useState(() => new Set());

  const toggleExpandedDate = (date) => {
    setExpandedDates((prev) => {
      const next = new Set(prev);
      if (next.has(date)) {
        next.delete(date);
      } else {
        next.add(date);
      }
      return next;
    });
  };

  if (!report.length) {
    return (
      <div className="sp2-card">
        <h3 className="sp2-card-title">일별 안전 리포트</h3>
        <p className="sp2-card-sub">아직 일별 안전점수 기록이 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="sp2-card">
      <div className="sp2-card-top">
        <div>
          <h3 className="sp2-card-title">일별 안전 리포트</h3>
          <p className="sp2-card-sub">날짜별 안전점수, ASOS 날씨, 이벤트와 영상 매핑</p>
        </div>
      </div>
      <div className="sp2-daily-list">
        {report.map((day) => {
          const color = scoreColor(day.score);
          const events = day.events || [];
          const isExpanded = expandedDates.has(day.date);
          const visibleEvents = isExpanded ? events : events.slice(0, 5);
          const hiddenCount = Math.max(events.length - 5, 0);
          return (
            <div key={day.date} className="sp2-daily-row">
              <div className="sp2-daily-main">
                <div className="sp2-daily-date">{day.date}</div>
                <div className={`sp2-daily-score sp2-score-${color}`}>{day.score}<span>점</span></div>
                <div className="sp2-daily-weather">
                  <strong>{day.daily_weather?.station_name || "기상 기록"}</strong>
                  <span>{weatherText(day.daily_weather)}</span>
                  {!day.daily_weather && onRefreshAsos && (
                    <button
                      type="button"
                      className="sp2-asos-refresh"
                      onClick={() => onRefreshAsos(day.date)}
                      disabled={refreshingAsosDate === day.date}
                    >
                      {refreshingAsosDate === day.date ? "조회 중" : "ASOS 조회"}
                    </button>
                  )}
                </div>
              </div>
              <div className="sp2-daily-events">
                {events.length ? (
                  visibleEvents.map((event) => (
                    <div key={event.id} className="sp2-daily-event">
                      <span className="sp2-event-time">{formatEventTime(event.timestamp)}</span>
                      <span className="sp2-event-label">
                        {EVENT_LABELS[event.event_type] || event.event_type}
                      </span>
                      <span
                        className={`sp2-event-deduction ${
                          event.deduction_applied ? "" : "sp2-event-deduction-muted"
                        }`}
                      >
                        -{formatDeduction(event.deduction_adjusted_points ?? event.deduction_points)}점
                      </span>
                      {event.has_clip ? (
                        <a
                          className="sp2-clip-link"
                          href={`${runtimeConfig.apiBaseUrl}/api/logs/${event.id}/clip`}
                          target="_blank"
                          rel="noreferrer"
                        >
                          영상
                        </a>
                      ) : (
                        <span className="sp2-clip-missing">영상 없음</span>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="sp2-daily-empty">이벤트 없음</div>
                )}
                {hiddenCount > 0 && (
                  <button
                    type="button"
                    className="sp2-daily-more"
                    onClick={() => toggleExpandedDate(day.date)}
                  >
                    {isExpanded ? "접기" : `외 ${hiddenCount}건 더 보기`}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ── 반원 게이지 ── */
function SemiGauge({ label, value, total, color }) {
  const pct = total > 0 ? Math.min(value / total, 1) : 0;
  const angle = pct * 180;
  const r = 38,
    cx = 50,
    cy = 50;
  const toRad = (d) => (d * Math.PI) / 180;
  const ex = cx + r * Math.cos(toRad(180 + angle));
  const ey = cy + r * Math.sin(toRad(180 + angle));
  return (
    <div className="sp2-gauge">
      <svg viewBox="0 0 100 58" className="sp2-gauge-svg">
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          stroke="#1e293b"
          strokeWidth="10"
          strokeLinecap="round"
        />
        {value > 0 && (
          <path
            d={`M ${cx - r} ${cy} A ${r} ${r} 0 ${angle > 180 ? 1 : 0} 1 ${ex} ${ey}`}
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeLinecap="round"
          />
        )}
        <text
          x={cx}
          y={cy - 5}
          textAnchor="middle"
          fontSize="16"
          fontWeight="800"
          fill={color}
        >
          {value}
        </text>
        <text x={cx} y={cy + 7} textAnchor="middle" fontSize="8" fill="#64748b">
          건
        </text>
      </svg>
      <span className="sp2-gauge-label">{label}</span>
    </div>
  );
}

/* ── 전월 대비 뱃지 ── */
function MomBadge({ cur, prev }) {
  if (prev === 0 && cur === 0) return <span className="sp2-mom flat">-</span>;
  if (prev === 0) return <span className="sp2-mom up">NEW</span>;
  const p = Math.round(((cur - prev) / prev) * 100);
  if (p === 0) return <span className="sp2-mom flat">±0%</span>;
  return (
    <span className={`sp2-mom ${p > 0 ? "up" : "down"}`}>
      {p > 0 ? "▲" : "▼"}
      {Math.abs(p)}%
    </span>
  );
}

/* ── 히트맵 ── */
function Heatmap({ logs }) {
  const matrix = useMemo(() => {
    const m = Array.from({ length: 7 }, () => Array(24).fill(0));
    logs.forEach((l) => {
      if (!ALL_EVENT_IDS.includes(l.event_type)) return;
      const d = new Date(l.timestamp);
      m[d.getDay()][d.getHours()] += 1;
    });
    return m;
  }, [logs]);
  const maxV = Math.max(1, ...matrix.flat());
  const alpha = (v) => (v === 0 ? 0 : 0.12 + (v / maxV) * 0.88);
  return (
    <div className="sp2-hm-scroll">
      <div className="sp2-hm-grid">
        <div className="sp2-hm-corner" />
        {HOURS.map((h) => (
          <div key={h} className="sp2-hm-h">
            {h}
          </div>
        ))}
        {DAYS.map((day, di) => (
          <React.Fragment key={day}>
            <div className="sp2-hm-d">{day}</div>
            {matrix[di].map((val, hi) => (
              <div
                key={hi}
                className="sp2-hm-cell"
                style={{ background: `rgba(245,158,11,${alpha(val)})` }}
                title={`${day} ${hi}시 ${val}건`}
              >
                {val > 0 && <span className="sp2-hm-n">{val}</span>}
              </div>
            ))}
          </React.Fragment>
        ))}
      </div>
      <div className="sp2-hm-leg">
        <span className="sp2-hm-leg-t">낮음</span>
        {[0.12, 0.35, 0.55, 0.75, 1].map((a, i) => (
          <div
            key={i}
            className="sp2-hm-leg-box"
            style={{ background: `rgba(245,158,11,${a})` }}
          />
        ))}
        <span className="sp2-hm-leg-t">높음</span>
      </div>
    </div>
  );
}

/* ── 시간대별 집중도 히트맵 ── */
function HourHeatmap({ logs }) {
  const counts = useMemo(() => {
    const arr = Array(24).fill(0);
    logs.forEach((l) => {
      if (!ALL_EVENT_IDS.includes(l.event_type)) return;
      arr[new Date(l.timestamp).getHours()] += 1;
    });
    return arr;
  }, [logs]);

  const maxV = Math.max(1, ...counts);
  const peakHour = counts.some((v) => v > 0) ? counts.indexOf(Math.max(...counts)) : null;
  const alpha = (v) => (v === 0 ? 0 : 0.15 + (v / maxV) * 0.85);
  const am = counts.slice(0, 12);
  const pm = counts.slice(12);

  return (
    <div className="sp2-hour-hm">
      <div className="sp2-hour-cols">
        {[
          { label: "AM", data: am, offset: 0 },
          { label: "PM", data: pm, offset: 12 },
        ].map(({ label, data, offset }) => (
          <div key={label} className="sp2-hour-col">
            <div className="sp2-hour-col-label">{label}</div>
            {data.map((v, i) => {
              const h = i + offset;
              return (
                <div
                  key={h}
                  className={`sp2-hour-row${h === peakHour && v > 0 ? " sp2-hour-row--peak" : ""}`}
                  title={`${h}시 ${v}건`}
                >
                  <span className="sp2-hour-lbl">{h}시</span>
                  <div className="sp2-hour-track">
                    <div
                      className="sp2-hour-fill"
                      style={{
                        width: `${(v / maxV) * 100}%`,
                        background: `rgba(245,158,11,${alpha(v)})`,
                      }}
                    />
                  </div>
                  <span className="sp2-hour-cnt">{v > 0 ? v : ""}</span>
                </div>
              );
            })}
          </div>
        ))}
      </div>
      {peakHour !== null && (
        <p className="sp2-hour-peak">
          피크: {String(peakHour).padStart(2, "0")}:00 — {counts[peakHour]}건
        </p>
      )}
    </div>
  );
}

/* ── 구역 순위 ── */
function ZoneRanking({ logs }) {
  const items = useMemo(() => {
    const map = {};
    logs.forEach((l) => {
      if (!ALL_EVENT_IDS.includes(l.event_type)) return;
      const z = l.zone || l.camera_id || l.location || "구역 미지정";
      map[z] = (map[z] || 0) + 1;
    });
    const s = Object.entries(map)
      .map(([z, c]) => ({ zone: z, count: c }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 7);
    return s.length > 0 ? s : [];
  }, [logs]);
  const max = items[0]?.count || 1;
  return (
    <div className="sp2-zone-list">
      {items.map(({ zone, count }, i) => (
        <div key={zone} className="sp2-zone-row">
          <span
            className="sp2-zone-rank"
            style={{ color: i < 3 ? "#f59e0b" : "#475569" }}
          >
            {i + 1}
          </span>
          <span className="sp2-zone-name">{zone}</span>
          <div className="sp2-zone-track">
            <div
              className="sp2-zone-fill"
              style={{
                width: `${(count / max) * 100}%`,
                background: ZONE_PALETTE[i % ZONE_PALETTE.length],
              }}
            />
          </div>
          <span className="sp2-zone-cnt">{count}건</span>
        </div>
      ))}
    </div>
  );
}

/* ══ 메인 ══════════════════════════════════════════════════════ */
export default function StatsPage({ logs = [] }) {
  const today = new Date();
  const todayStr = new Date().toLocaleDateString("sv-SE");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [applied, setApplied] = useState({ from: "", to: "" });

  const [selectedYear, setSelectedYear] = useState(today.getFullYear());
  const [activeFilters, setActiveFilters] = useState(new Set(ALL_EVENT_IDS));
  const [chartHeight, setChartHeight] = useState(220);
  const [dailyReport, setDailyReport] = useState([]);
  const [refreshingAsosDate, setRefreshingAsosDate] = useState("");
  const barChartRef = useRef(null);

  const loadDailyReport = useCallback(() => {
    safetyAPI.getDailyReport(30).then(setDailyReport).catch(() => setDailyReport([]));
  }, []);

  useEffect(() => {
    loadDailyReport();
  }, [loadDailyReport]);

  const handleRefreshAsos = async (date) => {
    setRefreshingAsosDate(date);
    try {
      await safetyAPI.refreshDailyWeather(date);
      loadDailyReport();
    } catch {
      window.alert("ASOS 기록을 조회하지 못했습니다.");
    } finally {
      setRefreshingAsosDate("");
    }
  };

  /* 적용된 날짜 필터 */
  const parsedFrom = applied.from ? new Date(applied.from + "T00:00:00") : null;
  const parsedTo = applied.to ? new Date(applied.to + "T23:59:59") : null;

  const filteredLogs = useMemo(() => {
    if (!parsedFrom && !parsedTo) return logs;
    return logs.filter((l) => {
      const d = new Date(l.timestamp);
      if (parsedFrom && d < parsedFrom) return false;
      if (parsedTo && d > parsedTo) return false;
      return true;
    });
  }, [logs, parsedFrom, parsedTo]);

  /* 요약 */
  const summary = useMemo(
    () => ({
      total: filteredLogs.filter((l) => ALL_EVENT_IDS.includes(l.event_type))
        .length,
      falling: filteredLogs.filter(
        (l) => l.event_type === "LOG_CRITICAL_FALLING",
      ).length,
      intrusion: filteredLogs.filter(
        (l) => l.event_type === "LOG_INTRUSION_SLOWDOWN",
      ).length,
      sensor: filteredLogs.filter((l) => l.event_type === "LOG_CRITICAL_SENSOR")
        .length,
    }),
    [filteredLogs],
  );

  /* 전월 대비 */
  const mom = useMemo(() => {
    const nm = today.getMonth(),
      ny = today.getFullYear();
    const pm = nm === 0 ? 11 : nm - 1,
      py = nm === 0 ? ny - 1 : ny;
    const cnt = (y, m, t) =>
      logs.filter((l) => {
        const d = new Date(l.timestamp);
        return (
          d.getFullYear() === y &&
          d.getMonth() === m &&
          (t ? l.event_type === t : ALL_EVENT_IDS.includes(l.event_type))
        );
      }).length;
    return {
      total: { cur: cnt(ny, nm), prev: cnt(py, pm) },
      falling: {
        cur: cnt(ny, nm, "LOG_CRITICAL_FALLING"),
        prev: cnt(py, pm, "LOG_CRITICAL_FALLING"),
      },
      intrusion: {
        cur: cnt(ny, nm, "LOG_INTRUSION_SLOWDOWN"),
        prev: cnt(py, pm, "LOG_INTRUSION_SLOWDOWN"),
      },
      sensor: {
        cur: cnt(ny, nm, "LOG_CRITICAL_SENSOR"),
        prev: cnt(py, pm, "LOG_CRITICAL_SENSOR"),
      },
    };
  }, [logs]);

  /* 월별 통계 */
  const monthly = useMemo(() => {
    const c = Array.from({ length: 12 }, (_, i) => ({
      month: `${i + 1}월`,
      falling: 0,
      intrusion: 0,
      sensor: 0,
    }));
    logs.forEach((l) => {
      const d = new Date(l.timestamp);
      if (d.getFullYear() !== selectedYear) return;
      const m = d.getMonth();
      if (l.event_type === "LOG_CRITICAL_FALLING") c[m].falling += 1;
      else if (l.event_type === "LOG_INTRUSION_SLOWDOWN") c[m].intrusion += 1;
      else if (l.event_type === "LOG_CRITICAL_SENSOR") c[m].sensor += 1;
    });
    return c;
  }, [logs, selectedYear]);

  useEffect(() => {
    if (!barChartRef.current) return;
    const ro = new ResizeObserver((entries) => {
      for (const e of entries)
        setChartHeight(Math.max(e.contentRect.height - 50, 40));
    });
    ro.observe(barChartRef.current);
    return () => ro.disconnect();
  }, []);

  const toggleFilter = (id) =>
    setActiveFilters((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        if (next.size > 1) next.delete(id);
      } else next.add(id);
      return next;
    });

  const nm = today.getMonth(),
    ny = today.getFullYear();
  const prevLabel = nm === 0 ? `${ny - 1}년 12월` : `${ny}년 ${nm}월`;
  const curLabel = `${ny}년 ${nm + 1}월`;

  return (
    <main className="sp2-page">
      <div className="sp2-inner">
        {/* 검색 바 */}
        <div className="sp2-search-bar">
          <div className="sp2-search-titles">
            <h2 className="sp2-search-h">현장 통계 검색</h2>
            <p className="sp2-search-sub">
              통계 데이터를 보려는 기간을 설정하세요.
            </p>
          </div>
          <div className="sp2-search-controls">
            <div className="sp2-ctrl-group">
              <label className="sp2-ctrl-label">현장</label>
              <select className="sp2-select">
                <option>전체 선택</option>
              </select>
            </div>
            <div className="sp2-ctrl-group">
              <label className="sp2-ctrl-label">기간</label>
              <div className="sp2-date-row">
                <input
                  type="date"
                  className="sp2-date-input"
                  value={dateFrom}
                  max={dateTo || todayStr}
                  onChange={(e) => setDateFrom(e.target.value)}
                />
                <span className="sp2-date-sep">~</span>
                <input
                  type="date"
                  className="sp2-date-input"
                  value={dateTo}
                  min={dateFrom}
                  max={todayStr}
                  onChange={(e) => setDateTo(e.target.value)}
                />
              </div>
            </div>
            <div className="sp2-ctrl-btns">
              {(applied.from || applied.to) && (
                <button
                  className="sp2-reset-btn"
                  onClick={() => {
                    setDateFrom("");
                    setDateTo("");
                    setApplied({ from: "", to: "" });
                  }}
                >
                  초기화
                </button>
              )}
              <button
                className="sp2-search-btn"
                onClick={() => setApplied({ from: dateFrom, to: dateTo })}
              >
                🔍 조회
              </button>
            </div>
          </div>
        </div>

        <DailySafetyReport
          report={dailyReport}
          onRefreshAsos={handleRefreshAsos}
          refreshingAsosDate={refreshingAsosDate}
        />

        {/* 전체 감지내역 카드 */}
        <div className="sp2-card">
          <div className="sp2-card-top">
            <div>
              <h3 className="sp2-card-title">전체 감지내역</h3>
              <p className="sp2-card-sub">
                조회: {applied.from || "전체"}{" "}
                {applied.to ? `to ${applied.to}` : ""} · 모든 이벤트
              </p>
            </div>
            <div className="sp2-mom-block">
              <span className="sp2-mom-title">
                {prevLabel} → {curLabel}
              </span>
              <div className="sp2-mom-items">
                {[
                  { l: "전체", d: mom.total },
                  { l: "넘어짐", d: mom.falling },
                  { l: "위험구역", d: mom.intrusion },
                  { l: "화재", d: mom.sensor },
                ].map(({ l, d }) => (
                  <div key={l} className="sp2-mom-item">
                    <span className="sp2-mom-lbl">{l}</span>
                    <MomBadge cur={d.cur} prev={d.prev} />
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="sp2-gauge-row">
            <SemiGauge
              label="총 발생"
              value={summary.total}
              total={Math.max(summary.total, 1)}
              color="#6366f1"
            />
            <div className="sp2-gauge-sep" />
            <SemiGauge
              label="넘어짐 감지"
              value={summary.falling}
              total={Math.max(summary.total, 1)}
              color="#8b5cf6"
            />
            <SemiGauge
              label="위험구역 접근"
              value={summary.intrusion}
              total={Math.max(summary.total, 1)}
              color="#ef4444"
            />
            <SemiGauge
              label="끼임 감지"
              value={summary.sensor}
              total={Math.max(summary.total, 1)}
              color="#f59e0b"
            />
          </div>
        </div>

        {/* 상단 2열: 월별 차트 + 구역 순위 */}
        <div className="sp2-bottom">
          {/* 월별 막대 차트 */}
          <div className="sp2-card sp2-col-chart">
            <div className="sp2-chart-head">
              <h3 className="sp2-card-title">월별 위험 이벤트</h3>
              <div className="sp2-yr-ctrl">
                <button
                  className="sp2-yr-btn"
                  onClick={() => setSelectedYear((y) => y - 1)}
                >
                  ◀
                </button>
                <span className="sp2-yr-lbl">{selectedYear}년</span>
                <button
                  className="sp2-yr-btn"
                  disabled={selectedYear >= today.getFullYear()}
                  onClick={() => setSelectedYear((y) => y + 1)}
                >
                  ▶
                </button>
              </div>
            </div>
            <div className="sp2-legend">
              {EVENT_TYPES.map(({ id, label, color }) => (
                <span
                  key={id}
                  className={`sp2-leg ${activeFilters.has(id) ? "on" : "off"}`}
                  onClick={() => toggleFilter(id)}
                >
                  <span className="sp2-leg-dot" style={{ background: color }} />
                  {label}
                </span>
              ))}
            </div>
            <div className="sp2-chart-area">
              <div className="sp2-y-axis">
                {[50, 40, 30, 20, 10, 0].map((v) => (
                  <div key={v} className="sp2-y-row">
                    <span className="sp2-y-num">{v}</span>
                    <span className="sp2-y-line" />
                  </div>
                ))}
              </div>
              <div className="sp2-bars-scroll">
                {/* 항상 3개 슬롯 고정 렌더 — 비활성 시 투명 처리 */}
                <div className="sp2-bar-chart" ref={barChartRef}>
                  {monthly.map((item) => (
                    <div className="sp2-bcol" key={item.month}>
                      <div className="sp2-bgroup">
                        <div
                          className="sp2-bwrap"
                          style={{
                            visibility: activeFilters.has(
                              "LOG_CRITICAL_FALLING",
                            )
                              ? "visible"
                              : "hidden",
                          }}
                        >
                          <span className="sp2-bnum">
                            {activeFilters.has("LOG_CRITICAL_FALLING")
                              ? item.falling || ""
                              : ""}
                          </span>
                          <div
                            className="sp2-bar"
                            style={{
                              height: `${Math.round((item.falling / 50) * chartHeight)}px`,
                              background: "#8b5cf6",
                            }}
                          />
                        </div>
                        <div
                          className="sp2-bwrap"
                          style={{
                            visibility: activeFilters.has(
                              "LOG_INTRUSION_SLOWDOWN",
                            )
                              ? "visible"
                              : "hidden",
                          }}
                        >
                          <span className="sp2-bnum">
                            {activeFilters.has("LOG_INTRUSION_SLOWDOWN")
                              ? item.intrusion || ""
                              : ""}
                          </span>
                          <div
                            className="sp2-bar"
                            style={{
                              height: `${Math.round((item.intrusion / 50) * chartHeight)}px`,
                              background: "#ef4444",
                            }}
                          />
                        </div>
                        <div
                          className="sp2-bwrap"
                          style={{
                            visibility: activeFilters.has("LOG_CRITICAL_SENSOR")
                              ? "visible"
                              : "hidden",
                          }}
                        >
                          <span className="sp2-bnum">
                            {activeFilters.has("LOG_CRITICAL_SENSOR")
                              ? item.sensor || ""
                              : ""}
                          </span>
                          <div
                            className="sp2-bar"
                            style={{
                              height: `${Math.round((item.sensor / 50) * chartHeight)}px`,
                              background: "#f59e0b",
                            }}
                          />
                        </div>
                      </div>
                      <span className="sp2-blabel">{item.month}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* 구역 순위 */}
          <div className="sp2-card sp2-col-zone">
            <h3 className="sp2-card-title">구역별 순위</h3>
            <p className="sp2-card-sub">이벤트 발생 건수 기준 상위 구역</p>
            <ZoneRanking logs={filteredLogs} />
          </div>
        </div>

        {/* 하단: 히트맵 2개 나란히 */}
        <div className="sp2-heat-row">
          <div className="sp2-card sp2-col-heat">
            <h3 className="sp2-card-title">시간대별 발생 히트맵</h3>
            <p className="sp2-card-sub">요일 × 시간 · 색이 진할수록 빈도 높음</p>
            <Heatmap logs={filteredLogs} />
          </div>
          <div className="sp2-card sp2-col-hour-heat">
            <h3 className="sp2-card-title">시간대 집중도</h3>
            <p className="sp2-card-sub">0~23시 중 사고가 많은 시간대</p>
            <HourHeatmap logs={filteredLogs} />
          </div>
        </div>
      </div>
    </main>
  );
}
