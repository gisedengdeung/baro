// src/components/dashboard/StatsPage.jsx
import React, { useState, useEffect, useRef, useMemo } from "react";
import "./StatsPage.css";

const ALL_EVENT_IDS = [
  "LOG_CRITICAL_FALLING",
  "LOG_INTRUSION_SLOWDOWN",
  "LOG_CRITICAL_SENSOR",
];

const EVENT_TYPES = [
  { id: "LOG_CRITICAL_FALLING", label: "넘어짐 감지", color: "#ef4444" },
  { id: "LOG_INTRUSION_SLOWDOWN", label: "위험구역 접근", color: "#f59e0b" },
  { id: "LOG_CRITICAL_SENSOR", label: "화재 감지", color: "#3b82f6" },
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
    return s.length > 0
      ? s
      : [
          { zone: "A구역 (1F 출입구)", count: 24 },
          { zone: "B구역 (2F 창고)", count: 18 },
          { zone: "C구역 (옥상)", count: 12 },
          { zone: "D구역 (지하 주차)", count: 9 },
          { zone: "E구역 (3F 복도)", count: 5 },
        ];
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
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [applied, setApplied] = useState({ from: "", to: "" });

  const [selectedYear, setSelectedYear] = useState(today.getFullYear());
  const [activeFilters, setActiveFilters] = useState(new Set(ALL_EVENT_IDS));
  const [chartHeight, setChartHeight] = useState(220);
  const barChartRef = useRef(null);

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
                  max={dateTo || today.toISOString().slice(0, 10)}
                  onChange={(e) => setDateFrom(e.target.value)}
                />
                <span className="sp2-date-sep">~</span>
                <input
                  type="date"
                  className="sp2-date-input"
                  value={dateTo}
                  min={dateFrom}
                  max={today.toISOString().slice(0, 10)}
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
              color="#ef4444"
            />
            <SemiGauge
              label="위험구역 접근"
              value={summary.intrusion}
              total={Math.max(summary.total, 1)}
              color="#f59e0b"
            />
            <SemiGauge
              label="화재 감지"
              value={summary.sensor}
              total={Math.max(summary.total, 1)}
              color="#3b82f6"
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
                              background: "#ef4444",
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
                              background: "#f59e0b",
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
                              background: "#3b82f6",
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

        {/* 하단: 히트맵 전체 너비 */}
        <div className="sp2-card sp2-col-heat">
          <h3 className="sp2-card-title">시간대별 발생 히트맵</h3>
          <p className="sp2-card-sub">요일 × 시간 · 색이 진할수록 빈도 높음</p>
          <Heatmap logs={filteredLogs} />
        </div>
      </div>
    </main>
  );
}
