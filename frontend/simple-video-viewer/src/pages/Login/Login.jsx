// src/pages/Login/Login.jsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import "./Login.css";
import bgImg from "../../assets/login_bg.jpg";

function Login() {
  const navigate = useNavigate();

  // 로그인 입력값
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");

  // 계정 생성 팝업 상태
  const [showSignup, setShowSignup] = useState(false);
  const [tempEmail, setTempEmail] = useState("");
  const [tempUsername, setTempUsername] = useState("");
  const [tempPw, setTempPw] = useState("");

  // 🔥 실제로 만들어둔 계정 정보 (백엔드 대신 메모리로 관리)
  const [createdEmail, setCreatedEmail] = useState("");
  const [createdPw, setCreatedPw] = useState("");
  const [createdUsername, setCreatedUsername] = useState("");

  // 로그인
  const handleLogin = () => {
    if (!createdEmail || !createdPw) {
      alert("먼저 계정을 생성해 주세요!");
      return;
    }

    if (email === createdEmail && pw === createdPw) {
      alert("✅ 로그인 성공!");
        localStorage.setItem("userEmail", createdEmail);
        localStorage.setItem("username", createdUsername || "관리자");
      navigate("/dashboard");
    } else {
      alert("❌ 이메일 또는 비밀번호가 일치하지 않습니다.");
    }
  };

  // 계정 생성
  const handleCreateAccount = () => {
    if (tempEmail.trim() && tempPw.trim()) {
      setCreatedEmail(tempEmail);
      setCreatedPw(tempPw);
      setEmail(tempEmail);
      setPw(tempPw);
      setCreatedUsername(tempUsername);
      alert("✅ 계정이 생성되었습니다!");
      setShowSignup(false);
      setTempEmail("");
      setTempUsername("");
      setTempPw("");
    } else {
      alert("이메일과 비밀번호를 입력하세요!");
    }
  };

  return (
    <div
      className="login-page"
      style={{ backgroundImage: `url(${bgImg})` }}
    >
      <div className="login-card">
        <div className="login-triangle" />
        <h1>Conveyor Guard</h1>
        <h2>Login</h2>
        <button
          className="signup-btn"
          onClick={() => setShowSignup(true)}
        >
          sign up
        </button>

        <input
          type="text"
          placeholder="이메일"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          type="password"
          placeholder="비밀번호"
          value={pw}
          onChange={(e) => setPw(e.target.value)}
        />

        <button
          className="login-btn"
          onClick={handleLogin}
        >
          login
        </button>

        {/* 인트로 페이지로 돌아가기 버튼 */}
        <button
          className="intro-btn"
          onClick={() => navigate("/intro")}
        >
          <ArrowLeft size={16} />
          인트로 돌아가기
        </button>
      </div>

      {/* 계정생성 팝업 */}
      {showSignup && (
        <div className="signup-overlay">
          <div className="signup-modal">
            <h2>Create Account</h2>
            <input
              type="text"
              placeholder="이메일"
              value={tempEmail}
              onChange={(e) => setTempEmail(e.target.value)}
            />
            <input
              type="text"
              placeholder="사용자명"
              value={tempUsername}
              onChange={(e) => setTempUsername(e.target.value)}
            />
            <input
              type="password"
              placeholder="비밀번호"
              value={tempPw}
              onChange={(e) => setTempPw(e.target.value)}
            />
            <div className="signup-buttons">
              <button
                className="cancel"
                onClick={() => setShowSignup(false)}
              >
                취소
              </button>
              <button
                className="create"
                onClick={handleCreateAccount}
              >
                계정 생성
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Login;
