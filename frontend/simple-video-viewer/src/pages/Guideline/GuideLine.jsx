// src/pages/GuideLine/GuideLine.jsx
import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./GuideLine.css";

const SECTIONS = [
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

export default function GuideLine() {
  const navigate = useNavigate();
  const [activeSection, setActiveSection] = useState("system");
  const [checked, setChecked] = useState(false);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 50);
    return () => clearTimeout(t);
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
