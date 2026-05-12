import { useState, useEffect, useCallback } from "react";
import { safetyAPI } from "../../services/api";

const STORAGE_KEY = "dashboard_ai_analysis";
const SCORE_POLL_MS = 5 * 60 * 1000; // 5분마다 점수 갱신

function scoreColor(score) {
  if (score >= 80) return "sw-ok";
  if (score >= 60) return "sw-warning";
  return "sw-danger";
}

export default function SafetyWidget() {
  const [scoreData, setScoreData] = useState(null);
  const [aiCache, setAiCache] = useState(() => {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)); } catch { return null; }
  });
  const [aiLoading, setAiLoading] = useState(false);

  const fetchScore = useCallback(async () => {
    try {
      const data = await safetyAPI.getScore();
      setScoreData(data);
    } catch {}
  }, []);

  useEffect(() => {
    fetchScore();
    const id = setInterval(fetchScore, SCORE_POLL_MS);
    return () => clearInterval(id);
  }, [fetchScore]);

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
          <div className="sw-ai-empty">분석 결과 없음</div>
        ) : (
          <>
            {hasWarnings ? (
              <div className="sw-ai-warnings">
                {warnings.slice(0, 2).map((w, i) => (
                  <div key={i} className="sw-ai-warn-item">
                    <span className="sw-warn-dot" />
                    <span className="sw-warn-text">
                      <strong>{w.event_label}</strong> {w.count}회
                      <span className="sw-warn-msg"> — {w.message.slice(0, 30)}{w.message.length > 30 ? "…" : ""}</span>
                    </span>
                  </div>
                ))}
                {warnings.length > 2 && (
                  <div className="sw-ai-more">+{warnings.length - 2}건 더</div>
                )}
              </div>
            ) : (
              <div className="sw-ai-safe">경고 없음 — 정상 범위</div>
            )}
            {aiCache.summary && (
              <div className="sw-ai-summary">
                {aiCache.summary.slice(0, 60)}{aiCache.summary.length > 60 ? "…" : ""}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
