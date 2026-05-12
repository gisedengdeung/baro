// src/pages/GuideLine/GuideLine.jsx
import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { safetyAPI } from "../../services/api";
import "./GuideLine.css";

const SECTIONS = [
  {
    id: "safety",
    icon: "🛡️",
    label: "안전점수",
    title: "오늘의 안전점수",
    color: "ok",
    isSafety: true,
    items: [],
  },
  {
    id: "system",
    icon: "⏻",
    label: "시스템 제어",
    title: "시스템 운행 제어",
    color: "ok",
    items: [
      {
        icon: "⏻",
        name: "전체 시스템 ON",
        desc: "자동 감지 모드로 컨베이어를 가동합니다. 위험구역 내 인원이 없을 때만 활성화됩니다.",
      },
      {
        icon: "⏼",
        name: "전체 시스템 OFF",
        desc: "컨베이어 운행을 정지합니다. 언제든지 즉시 정지 가능합니다.",
      },
      {
        icon: "🖥️",
        name: "정비 모드",
        desc: "시스템을 정비 모드로 전환합니다. 이 모드에서는 컨베이어가 정지되고 안전하게 장비를 점검할 수 있습니다.",
      },
      {
        icon: "🔄",
        name: "시스템 리셋",
        desc: "잠금(LOCKED) 상태 또는 오류 발생 시 시스템을 초기화합니다. 관리자 확인 후 진행하세요.",
      },
      {
        icon: "🛑",
        name: "긴급 정지",
        desc: "즉각적으로 모든 운행을 중단합니다. 위급 상황 발생 시 즉시 누르세요.",
        highlight: true,
      },
    ],
  },
  {
    id: "status",
    icon: "●",
    label: "상태 표시",
    title: "시스템 상태 표시등",
    color: "ok",
    items: [
      {
        badge: "ok",
        name: "정상 운전 중",
        desc: "시스템이 정상적으로 운행 중입니다. 위험 요소가 감지되지 않은 상태입니다.",
        dotColor: "ok",
      },
      {
        badge: "intrusion",
        name: "위험구역 침입 감지",
        desc: "운행 중 위험구역 내 인원이 감지되었습니다. 시스템이 자동으로 속도를 줄이거나 경고를 발생시킵니다.",
        dotColor: "warning",
      },
      {
        badge: "maintenance",
        name: "정비 모드",
        desc: "장비 점검 중인 상태입니다. 컨베이어는 정지되어 있으며 안전하게 작업할 수 있습니다.",
        dotColor: "warning",
      },
      {
        badge: "danger",
        name: "긴급 위험 감지",
        desc: "낙상 감지 또는 심각한 위험이 발생했습니다. 시스템이 잠금 상태로 전환되며 관리자 확인이 필요합니다.",
        dotColor: "danger",
      },
      {
        badge: "offline",
        name: "시스템 대기 / 꺼짐",
        desc: "시스템이 정지 또는 꺼진 상태입니다.",
        dotColor: "offline",
      },
    ],
  },
  {
    id: "dangerzone",
    icon: "⚠️",
    label: "위험구역 설정",
    title: "위험구역 설정 방법",
    color: "warning",
    items: [
      {
        step: "01",
        name: "위험구역 설정 버튼 클릭",
        desc: "컨베이어 제어 패널의 '⚠️ 위험구역 설정' 버튼을 누릅니다.",
      },
      {
        step: "02",
        name: "구역 생성 선택",
        desc: "팝업에서 '새 구역 생성'을 선택한 뒤 구역 이름을 입력합니다.",
      },
      {
        step: "03",
        name: "영상에서 구역 지정",
        desc: "라이브 영상 위를 클릭하여 위험구역의 꼭짓점을 순서대로 지정합니다. 최소 3개 이상의 점이 필요합니다.",
      },
      {
        step: "04",
        name: "구역 저장",
        desc: "지정이 완료되면 저장 버튼을 눌러 구역을 등록합니다. 이후 해당 구역에 인원이 감지되면 경고가 발생합니다.",
      },
    ],
  },
  {
    id: "emergency",
    icon: "🚨",
    label: "비상 절차",
    title: "비상 상황 대응 절차",
    color: "danger",
    items: [
      {
        step: "01",
        name: "긴급 정지 버튼 즉시 클릭",
        desc: "화면 하단의 '🛑 긴급 정지' 버튼을 눌러 즉시 모든 운행을 중단하세요.",
        highlight: true,
      },
      {
        step: "02",
        name: "현장 인원 대피 확인",
        desc: "위험구역 및 컨베이어 주변 인원이 모두 안전한 위치로 대피했는지 확인합니다.",
      },
      {
        step: "03",
        name: "관리자에게 상황 보고",
        desc: "이벤트 로그에 기록된 감지 내용을 캡처하고 담당 관리자에게 즉시 보고합니다.",
      },
      {
        step: "04",
        name: "시스템 리셋 후 재가동",
        desc: "안전이 확인된 후에만 '🔄 리셋' 버튼을 눌러 시스템을 초기화하고 재가동하세요.",
      },
    ],
  },
];

function scoreColor(score) {
  if (score >= 80) return "ok";
  if (score >= 60) return "warning";
  return "danger";
}

function AiAnalysisPanel({ analysis, loading, error, onRequest }) {
  if (loading) {
    return (
      <div className="gl-ai-panel gl-ai-loading">
        <span className="gl-ai-spinner" />
        <span>AI가 오늘 안전 데이터를 분석하고 있습니다...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="gl-ai-panel gl-ai-error">
        <div className="gl-ai-error-msg">{error}</div>
        <button className="gl-ai-retry-btn" onClick={onRequest}>다시 시도</button>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="gl-ai-panel gl-ai-idle">
        <div className="gl-ai-idle-icon">✦</div>
        <div className="gl-ai-idle-text">AI가 오늘의 이벤트 로그와 안전점수를 종합 분석합니다.</div>
        <button className="gl-ai-btn" onClick={onRequest}>AI 안전 분석 시작</button>
      </div>
    );
  }

  const { summary, warnings = [], recommendations = [] } = analysis;
  return (
    <div className="gl-ai-panel gl-ai-result">
      <div className="gl-ai-result-head">
        <span className="gl-ai-badge">AI 분석</span>
        <button className="gl-ai-refresh-btn" onClick={onRequest}>새로고침</button>
      </div>

      <div className="gl-ai-summary">{summary}</div>

      {warnings.length > 0 && (
        <div className="gl-ai-warnings">
          <div className="gl-ai-section-title">주의 필요 항목</div>
          {warnings.map((w, i) => (
            <div key={i} className="gl-ai-warning-card">
              <div className="gl-ai-warning-head">
                <span className="gl-ai-warning-label">{w.event_label}</span>
                <span className="gl-ai-warning-count">
                  {w.count}회 발생 · AI 기준 {w.threshold}회 이상
                </span>
              </div>
              <div className="gl-ai-warning-msg">{w.message}</div>
            </div>
          ))}
        </div>
      )}

      {warnings.length === 0 && (
        <div className="gl-ai-no-warning">주의 필요 항목 없음 — 오늘 이벤트는 정상 범위입니다.</div>
      )}

      {recommendations.length > 0 && (
        <div className="gl-ai-recs">
          <div className="gl-ai-section-title">오늘의 안전 권고</div>
          <ul className="gl-ai-rec-list">
            {recommendations.map((r, i) => (
              <li key={i} className="gl-ai-rec-item">{r}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function SafetyContent({ data, history, loading, aiAnalysis, aiLoading, aiError, onAiRequest }) {
  if (loading) {
    return <div className="gl-safety-loading">데이터 불러오는 중...</div>;
  }
  if (!data) {
    return (
      <div className="gl-safety-loading">안전점수를 불러올 수 없습니다.</div>
    );
  }

  const color = scoreColor(data.score);
  const difficulty = data.difficulty || {};
  const eventDeduction = data.event_deduction || {};
  const eventDetails = eventDeduction.events || data.deductions?.events || [];
  const hasDeductions = eventDetails.length > 0;
  const difficultyColor = difficulty.color || "ok";
  const difficultyFactors = difficulty.factors || {};
  const weatherDetails = difficultyFactors.weather?.details || [];
  const weatherObservation = weatherDetails.find(
    (item) => item.key === "weather_observation" || item.key === "weather_api_error",
  );
  const weatherAlerts = weatherDetails.filter(
    (item) => item.key !== "weather_observation" && item.key !== "weather_api_error",
  );
  const weatherValues = weatherObservation?.values || {};

  return (
    <div className="gl-safety-grid">
      {/* 점수 + 무사고 스트릭 */}
      <div className="gl-score-hero">
        <div className={`gl-score-ring gl-ring-${color}`}>
          <span className={`gl-score-number gl-score-${color}`}>
            {data.score}
          </span>
          <span className="gl-score-label">/ 100점</span>
        </div>
        <div className="gl-score-info">
          <div className="gl-streak">
            <span className="gl-streak-icon">🏆</span>
            <div>
              <div className="gl-streak-num">
                {data.accident_free_streak}일째
              </div>
              <div className="gl-streak-sub">무사고 연속</div>
            </div>
          </div>
          <div className={`gl-status-badge gl-status-${color}`}>
            {color === "ok" && "안전 유지 중"}
            {color === "warning" && "주의 필요"}
            {color === "danger" && "위험 수준"}
          </div>
          <div className="gl-score-note">
            금일 위험도는 직접 감점하지 않고, 이벤트 감점 배율로만 반영됩니다.
          </div>
        </div>
        <div className="gl-weather-box">
          <div className="gl-weather-head">
            <span>기상 API 상태</span>
            <strong
              className={
                weatherObservation?.status === "error"
                  ? "gl-weather-error"
                  : "gl-weather-ok"
              }
            >
              {weatherObservation?.status === "error" ? "오류" : "연결됨"}
            </strong>
          </div>
          {weatherObservation?.status === "error" ? (
            <div className="gl-weather-message">
              {weatherObservation.message || "기상 정보를 불러오지 못했습니다."}
            </div>
          ) : weatherObservation ? (
            <>
              <div className="gl-weather-meta">
                관측소 {weatherObservation.station_no}
                {weatherObservation.observed_at
                  ? ` · ${weatherObservation.observed_at}`
                  : ""}
              </div>
              <div className="gl-weather-values">
                <span>기온 {weatherValues.temp_c ?? "-"}도</span>
                <span>습도 {weatherValues.humidity_pct ?? "-"}%</span>
                <span>풍속 {weatherValues.wind_mps ?? "-"}m/s</span>
                <span>강수 {weatherValues.rain_mm ?? "-"}mm</span>
              </div>
              <div className="gl-weather-message">
                {weatherAlerts.length > 0
                  ? weatherAlerts.map((item) => item.label).join(" · ")
                  : "위험 기상 조건 없음"}
              </div>
            </>
          ) : (
            <div className="gl-weather-message">
              아직 기상 관측값이 갱신되지 않았습니다.
            </div>
          )}
        </div>
      </div>

      {/* 금일 위험도 */}
      <div className="gl-difficulty-panel">
        <div className="gl-panel-title">금일 위험도</div>
        <div className="gl-difficulty-summary">
          <div>
            <span className={`gl-difficulty-score gl-score-${difficultyColor}`}>
              {difficulty.score ?? "-"}
            </span>
            <span className="gl-difficulty-unit">점</span>
          </div>
          <div className={`gl-status-badge gl-status-${difficultyColor}`}>
            {difficulty.level || "계산 대기"} · x{difficulty.multiplier || 1}
          </div>
        </div>
        <div className="gl-factor-list">
          <div className="gl-factor-row">
            <span>업종 위험도</span>
            <strong>+{difficultyFactors.industry?.risk ?? 0}</strong>
          </div>
          <div className="gl-factor-row">
            <span>
              규모 위험도
              {difficultyFactors.size?.scale
                ? ` · ${difficultyFactors.size.scale}`
                : ""}
            </span>
            <strong>+{difficultyFactors.size?.risk ?? 0}</strong>
          </div>
          <div className="gl-factor-row">
            <span>기상 위험도</span>
            <strong>+{difficultyFactors.weather?.risk ?? 0}</strong>
          </div>
        </div>
      </div>

      {/* 감점 내역 */}
      <div className="gl-deductions-panel">
        <div className="gl-panel-title">AI 이벤트 감점</div>
        {!hasDeductions ? (
          <div className="gl-no-deductions">
            감점 없음 — 오늘 하루 무사고입니다!
          </div>
        ) : (
          <>
            {eventDetails.map((e) => {
              const applied = Math.min(e.count, e.daily_cap);
              const pts = applied * e.points_per;
              return (
                <div key={e.event_type} className="gl-deduction-row">
                  <span className="gl-ded-label">{e.label}</span>
                  <span className="gl-ded-meta">
                    {e.count}회 발생 · 최대 {e.daily_cap}회 반영
                  </span>
                  <span className="gl-ded-pts gl-ded-danger">-{pts}점</span>
                </div>
              );
            })}
            <div className="gl-deduction-total">
              기본 이벤트 감점 -{eventDeduction.base ?? 0}점 × 난이도 배율 x
              {difficulty.multiplier || 1} = 최종 감점 -
              {eventDeduction.adjusted ?? 0}점
            </div>
          </>
        )}
      </div>

      {/* 최근 7일 히스토리 */}
      {history.length > 0 && (
        <div className="gl-history-panel">
          <div className="gl-panel-title">최근 {history.length}일 기록</div>
          <div className="gl-history-bars">
            {[...history].reverse().map((h) => {
              const c = scoreColor(h.score);
              return (
                <div key={h.date} className="gl-bar-col">
                  <div className="gl-bar-score-top">{h.score}</div>
                  <div className="gl-bar-track">
                    <div
                      className={`gl-bar-fill gl-bar-${c}`}
                      style={{ height: `${h.score}%` }}
                    />
                  </div>
                  <div className="gl-bar-date">{h.date.slice(5)}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* AI 안전 분석 */}
      <div className="gl-ai-wrap">
        <AiAnalysisPanel
          analysis={aiAnalysis}
          loading={aiLoading}
          error={aiError}
          onRequest={onAiRequest}
        />
      </div>
    </div>
  );
}

export default function GuideLine() {
  const navigate = useNavigate();
  const [activeSection, setActiveSection] = useState("safety");
  const [checked, setChecked] = useState(false);
  const [visible, setVisible] = useState(false);
  const [safetyData, setSafetyData] = useState(null);
  const [safetyHistory, setSafetyHistory] = useState([]);
  const [safetyLoading, setSafetyLoading] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState(null);

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 50);
    return () => clearTimeout(t);
  }, []);

  const fetchSafety = useCallback(async () => {
    setSafetyLoading(true);
    try {
      const [score, history] = await Promise.all([
        safetyAPI.getScore(),
        safetyAPI.getHistory(7),
      ]);
      setSafetyData(score);
      setSafetyHistory(history);
    } catch {
      setSafetyData(null);
    } finally {
      setSafetyLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeSection === "safety") {
      fetchSafety();
    }
  }, [activeSection, fetchSafety]);

  const fetchAiAnalysis = useCallback(async () => {
    setAiLoading(true);
    setAiError(null);
    try {
      const result = await safetyAPI.explain();
      setAiAnalysis(result.analysis);
    } catch (e) {
      const msg = e?.response?.data?.detail || "AI 분석 요청에 실패했습니다.";
      setAiError(msg);
    } finally {
      setAiLoading(false);
    }
  }, []);

  const current = SECTIONS.find((s) => s.id === activeSection);

  return (
    <div className={`guideline-root${visible ? " gl-visible" : ""}`}>
      {/* 배경 그리드 */}
      <div className="gl-bg-grid" />
      <div className="gl-bg-glow" />

      <div className="gl-container">
        {/* 헤더 */}
        <header className="gl-header">
          <div className="gl-logo-row">
            <span className="gl-logo">STOP</span>
            <span className="gl-logo-sub">Safety Total Operation Platform</span>
          </div>
          <h1 className="gl-title">
            시스템 운영<br />
            <span className="gl-title-accent">가이드라인</span>
          </h1>
          <p className="gl-subtitle">
            대시보드 진입 전 아래 내용을 숙지하세요.<br />
            안전한 시스템 운영을 위한 필수 안내입니다.
          </p>
        </header>

        {/* 탭 네비게이션 */}
        <nav className="gl-tabs">
          {SECTIONS.map((s) => (
            <button
              key={s.id}
              className={`gl-tab${activeSection === s.id ? " gl-tab-active" : ""} gl-tab-${s.color}`}
              onClick={() => setActiveSection(s.id)}
            >
              <span className="gl-tab-icon">{s.icon}</span>
              <span className="gl-tab-label">{s.label}</span>
            </button>
          ))}
        </nav>

        {/* 콘텐츠 */}
        <div className="gl-content" key={activeSection}>
          <h2 className="gl-section-title">
            <span className={`gl-section-accent gl-accent-${current.color}`}>
              {current.icon}
            </span>
            {current.title}
          </h2>

          {current.isSafety ? (
            <SafetyContent
              data={safetyData}
              history={safetyHistory}
              loading={safetyLoading}
              aiAnalysis={aiAnalysis}
              aiLoading={aiLoading}
              aiError={aiError}
              onAiRequest={fetchAiAnalysis}
            />
          ) : (
            <div className="gl-cards">
              {current.items.map((item, i) => (
                <div
                  key={i}
                  className={`gl-card gl-card-delay-${i}${item.highlight ? " gl-card-highlight" : ""}`}
                >
                  {item.step && (
                    <div className={`gl-step-badge gl-badge-${current.color}`}>
                      STEP {item.step}
                    </div>
                  )}
                  {item.dotColor && (
                    <div className="gl-card-dot-row">
                      <span className={`gl-dot gl-dot-${item.dotColor}`} />
                    </div>
                  )}
                  {item.icon && !item.step && !item.dotColor && (
                    <div className="gl-card-icon">{item.icon}</div>
                  )}
                  <div className="gl-card-body">
                    <div className="gl-card-name">{item.name}</div>
                    <div className="gl-card-desc">{item.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 하단 확인 영역 */}
        <footer className="gl-footer">
          <label className="gl-check-label">
            <input
              type="checkbox"
              className="gl-checkbox"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
            />
            <span className="gl-check-custom" />
            <span className="gl-check-text">
              위 가이드라인을 모두 숙지하였으며, 안전 수칙을 준수하겠습니다.
            </span>
          </label>
          <button
            className={`gl-enter-btn${checked ? " gl-enter-active" : ""}`}
            disabled={!checked}
            onClick={() => navigate("/dashboard")}
          >
            <span>대시보드 진입</span>
            <span className="gl-enter-arrow">→</span>
          </button>
        </footer>
      </div>
    </div>
  );
}
