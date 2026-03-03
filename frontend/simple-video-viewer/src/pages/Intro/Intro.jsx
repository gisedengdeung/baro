import { useState, useEffect } from "react";
import "./Intro.css";
import { useNavigate, Link, useLocation } from "react-router-dom";
import { useInView } from "react-intersection-observer";

// 스크롤 시 섹션이 애니메이션으로 등장하도록 처리하는 컴포넌트
const AnimatedSection = ({ children, reverse = false }) => {
  const { ref, inView } = useInView({
    triggerOnce: false,
    threshold: 0.1,
  });

  return (
    <div
      ref={ref}
      className={`section-content ${reverse ? "reverse" : ""} ${inView ? "visible" : ""}`}
    >
      {children}
    </div>
  );
};

function Intro() {
  const navigate = useNavigate();
  const currentLocation = useLocation();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 50);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const scrollToTop = (e) => {
    e.preventDefault();
    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  };

  return (
    <div className="intro-page">
      {/* ===== 상단 헤더 ===== */}
      <header className={`intro-header ${scrolled ? "scrolled" : ""}`}>
        <div className="intro-header-inner">
          <div className="logo">
            <Link
              to="/"
              onClick={scrollToTop}
              style={{ textDecoration: "none", color: "inherit" }}
            >
              STOP
            </Link>
          </div>
          <nav className="intro-nav">
            <a
              href="#streaming"
              className={currentLocation.hash === "#streaming" ? "active" : ""}
            >
              CCTV 활용
            </a>
            <a
              href="#safety"
              className={currentLocation.hash === "#safety" ? "active" : ""}
            >
              위험 구역
            </a>
            <a
              href="#service"
              className={currentLocation.hash === "#service" ? "active" : ""}
            >
              디지털 LOTO
            </a>
            <a
              href="#AI"
              className={currentLocation.hash === "#AI" ? "active" : ""}
            >
              AI 위험 감지
            </a>
          </nav>
          <button className="login-btn" onClick={() => navigate("/login")}>
            로그인
          </button>
        </div>
      </header>

      {/* ===== 히어로 섹션 ===== */}
      <div className="intro-hero">
        <div className="hero-text">
          <h2>
            산업 현장의 안전,
            <br />
            가장 스마트하게 지키는 방법
          </h2>
          <p>
            STOP은 최첨단 AI 기술로 중대재해를 예방하고
            <br />
            모두가 안심하고 일할 수 있는 작업 환경을 만듭니다.
          </p>
        </div>
      </div>

      {/* ===== 실시간 영상 스트리밍 ===== */}
      <section id="streaming" className="intro-section">
        <AnimatedSection>
          <div className="section-text">
            <h2>
              기존 CCTV를 활용한
              <br />
              실시간 스트리밍
            </h2>
            <p>
              별도의 카메라 설치 없이, 기존 공장에 설치된 CCTV를 그대로 활용하여
              현장을 실시간으로 확인할 수 있습니다. 언제 어디서든 웹 대시보드를
              통해 안전 상황을 모니터링하세요.
            </p>
          </div>
          <div className="section-visual">
            <svg
              className="feature-icon"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"
              />
            </svg>
          </div>
        </AnimatedSection>
      </section>

      {/* ===== 위험구역 설정 ===== */}
      <section id="safety" className="intro-section">
        <AnimatedSection reverse>
          <div className="section-text">
            <h2>
              사용자 정의 가능한
              <br />
              위험 구역 설정
            </h2>
            <p>
              CCTV 영상 위에서 마우스 클릭만으로 간단하게 위험 구역(ROI)을
              설정할 수 있습니다. 컨베이어 벨트, 로봇 팔 주변 등 사고 위험이
              높은 곳을 지정하여 집중적으로 관리하세요.
            </p>
          </div>
          <div className="section-visual">
            <svg
              className="feature-icon"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
              />
            </svg>
          </div>
        </AnimatedSection>
      </section>

      {/* ===== 디지털 로토 설정 ===== */}
      <section id="service" className="intro-section">
        <AnimatedSection>
          <div className="section-text">
            <h2>
              자동화된
              <br />
              디지털 LOTO 시스템
            </h2>
            <p>
              정비 작업자가 위험 구역에 들어가면 시스템이 이를 감지하여 해당
              설비의 작동을 즉시 차단합니다. 디지털 LOTO(Lockout/Tagout)를 통해
              인적 오류로 인한 사고를 원천적으로 방지합니다.
            </p>
          </div>
          <div className="section-visual">
            <svg
              className="feature-icon"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H4.5a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"
              />
            </svg>
          </div>
        </AnimatedSection>
      </section>

      {/* ===== AI 기능 ===== */}
      <section id="AI" className="intro-section">
        <AnimatedSection reverse>
          <div className="section-text">
            <h2>
              AI 기반의
              <br />
              실시간 위험 감지
            </h2>
            <p>
              YOLOv8 기반의 AI가 CCTV 영상을 실시간으로 분석하여 작업자를
              탐지하고, 넘어짐과 같은 위험한 행동을 신속하게 인식합니다.
              잠재적인 사고를 예측하고 예방 조치를 취할 수 있도록 지원합니다.
            </p>
          </div>
          <div className="section-visual">
            <svg
              className="feature-icon"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75-11.25L12 12.75l3.75-3.75M12 3v5.25"
              />
            </svg>
          </div>
        </AnimatedSection>
      </section>

      {/* ===== 마지막 CTA ===== */}
      <section className="intro-cta">
        <div className="cta-content">
          <h2>지금 바로 시작하세요</h2>
          <p>더 안전한 산업 현장, STOP이 함께합니다.</p>
          <button className="cta-button" onClick={() => navigate("/signup")}>
            무료로 시작하기
          </button>
        </div>
      </section>
    </div>
  );
}

export default Intro;
