import React, { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import useAuthStore from "../../store/useAuthStore";
import "./Login.css";

function Login() {
  // 이메일, 비밀번호 입력값 상태 관리
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // 스토어에서 필요한 상태와 함수 가져오기
  const login = useAuthStore((state) => state.login);
  const isLoading = useAuthStore((state) => state.isLoading); // 로그인 요청 중 여부
  const error = useAuthStore((state) => state.error); // 로그인 실패 시 에러 메시지

  const navigate = useNavigate();
  const location = useLocation();

  // 로그인 성공시 /dashboard로 이동
  const from = location.state?.from?.pathname || "/dashboard";

  // 폼 제출 핸들러
  const handleSubmit = async (e) => {
    e.preventDefault(); // 브라우저 기본 제출 동작 방지
    try {
      await login(email, password);
      navigate(from, { replace: true }); // 로그인 성공 시 목적지로 이동 (뒤로가기로 로그인 페이지 재방문 방지)
    } catch (err) {
      // 에러 처리는 스토어에서 담당 (error 상태에 저장됨)
    }
  };

  return (
    <div className="login-container">
      <form className="login-form" onSubmit={handleSubmit}>
        <div className="login-head">Login</div>

        {error && (
          <div
            style={{
              color: "red",
              marginBottom: "10px",
              textAlign: "center",
              fontSize: "14px",
            }}
          >
            {error}
          </div>
        )}

        <div className="flex-column">
          <label>이메일 </label>
        </div>
        <div className="login-inputForm">
          <svg
            height="20"
            viewBox="0 0 32 32"
            width="20"
            xmlns="http://www.w3.org/2000/svg"
          >
            <g id="Layer_3" data-name="Layer 3">
              <path d="m30.853 13.87a15 15 0 0 0 -29.729 4.082 15.1 15.1 0 0 0 12.876 12.918 15.6 15.6 0 0 0 2.016.13 14.85 14.85 0 0 0 7.715-2.145 1 1 0 1 0 -1.031-1.711 13.007 13.007 0 1 1 5.458-6.529 2.149 2.149 0 0 1 -4.158-.759v-10.856a1 1 0 0 0 -2 0v1.726a8 8 0 1 0 .2 10.325 4.135 4.135 0 0 0 7.83.274 15.2 15.2 0 0 0 .823-7.455zm-14.853 8.13a6 6 0 1 1 6-6 6.006 6.006 0 0 1 -6 6z"></path>
            </g>
          </svg>
          <input
            type="email"
            className="input"
            placeholder="이메일을 입력해주세요"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>

        <div className="flex-column">
          <label>비밀번호 </label>
        </div>
        <div className="login-inputForm">
          <svg
            height="20"
            viewBox="-64 0 512 512"
            width="20"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path d="m336 512h-288c-26.453125 0-48-21.523438-48-48v-224c0-26.476562 21.546875-48 48-48h288c26.453125 0 48 21.523438 48 48v224c0 26.476562-21.546875 48-48 48zm-288-288c-8.8125 0-16 7.167969-16 16v224c0 8.832031 7.1875 16 16 16h288c8.8125 0 16-7.167969 16-16v-224c0-8.832031-7.1875-16-16-16zm0 0"></path>
            <path d="m304 224c-8.832031 0-16-7.167969-16-16v-80c0-52.929688-43.070312-96-96-96s-96 43.070312-96 96v80c0 8.832031-7.167969 16-16 16s-16-7.167969-16-16v-80c0-70.59375 57.40625-128 128-128s128 57.40625 128 128v80c0 8.832031-7.167969 16-16 16zm0 0"></path>
          </svg>
          <input
            type="password"
            className="input"
            placeholder="비밀번호를 입력해주세요"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        <button className="button-submit" type="submit" disabled={isLoading}>
          {isLoading ? "로그인하는중..." : "로그인"}
        </button>

        <p className="p">
          계정이 없으신가요?{" "}
          <Link to="/signup" className="span">
            회원가입
          </Link>
        </p>
      </form>
    </div>
  );
}

export default Login;
