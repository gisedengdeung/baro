import { useState, useEffect, useCallback } from "react";
import { safetyAPI } from "../../services/api";
import useDashboardStore from "../../store/useDashboardStore";

const STORAGE_KEY = "dashboard_ai_analysis";

function scoreColor(score) {
  if (score >= 80) return "sw-ok";
  if (score >= 60) return "sw-warning";
  return "sw-danger";
}

export default function SafetyWidget() {
  // 실시간 WebSocket 업데이트 (이벤트 발생 시 즉시 반영)
  const realtimeScoreData = useDashboardStore((s) => s.safetyScoreData);
  const [polledScoreData, setPolledScoreData] = useState(null);
  // 실시간 데이터가 있으면 우선 사용, 없으면 초기 폴링 데이터 사용
  const scoreData = realtimeScoreData ?? polledScoreData;

  const [aiCache, setAiCache] = useState(() => {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)); } catch { return null; }
  });
  const [aiLoading, setAiLoading] = useState(false);

  // 마운트 시 1회만 점수 로드 (초기값용)
  useEffect(() => {
    safetyAPI.getScore().then(setPolledScoreData).catch(() => {});
  }, []);

  const fetchAi = useCallback(async () => {
    setAiLoading(true);
    try {
      const result = await safetyAPI.explain();
      const cached = { ...result.analysis, fetchedAt: new Date().toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" }) };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(cached));
      setAiCache(cached);
    } catch {}
    finally { setAiLoading(false); }
  }, []);

  if (!scoreData) return null;

  const color = scoreColor(scoreData.score);
  const difficulty = scoreData.difficulty || {};
  const warnings = aiCache?.warnings || [];
  const hasWarnings = warnings.length > 0;

  return (
    <div className="safety-widget">
      <h3>안전 현황</h3>

      {/* 안전점수 */}
      <div className="sw-score-row">
        <div className={`sw-score-num ${color}`}>{scoreData.score}<span className="sw-score-unit">점</span></div>
        <div className="sw-score-info">
          <div className={`sw-badge ${color}`}>
            {color === "sw-ok" && "안전"}
            {color === "sw-warning" && "주의"}
            {color === "sw-danger" && "위험"}
          </div>
          <div className="sw-streak">🏆 {scoreData.accident_free_streak}일 무사고</div>
        </div>
        <div className="sw-difficulty">
          <span className="sw-diff-label">금일 위험도</span>
          <span className={`sw-diff-level sw-diff-${difficulty.color || "ok"}`}>
            {difficulty.level || "-"}
          </span>
          <span className="sw-diff-mult">×{difficulty.multiplier || 1}</span>
        </div>
      </div>

      {/* AI 분석 */}
      <div className="sw-ai-row">
        <div className="sw-ai-head">
          <span className="sw-ai-label">AI 분석</span>
          {aiCache?.fetchedAt && (
            <span className="sw-ai-time">{aiCache.fetchedAt}</span>
          )}
          <button
            className="sw-ai-btn"
            onClick={fetchAi}
            disabled={aiLoading}
          >
            {aiLoading ? "..." : "새 분석"}
          </button>
        </div>

        {!aiCache ? (
          <div className="sw-ai-empty">분석 결과 없음 — 새 분석을 실행하세요</div>
        ) : (
          <>
            {hasWarnings ? (
              <div className="sw-ai-warnings">
                {warnings.map((w, i) => (
                  <div key={i} className="sw-ai-warn-card">
                    <div className="sw-warn-card-header">
                      <span className="sw-warn-card-label">{w.event_label}</span>
                      <span className="sw-warn-card-count">{w.count}회</span>
                    </div>
                    <div className="sw-warn-card-msg">{w.message}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="sw-ai-safe">✓ 경고 없음 — 정상 범위</div>
            )}
            {aiCache.summary && (
              <div className="sw-ai-summary">
                <span className="sw-ai-summary-icon">💬</span>
                {aiCache.summary}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
