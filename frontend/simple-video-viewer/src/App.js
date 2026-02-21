import React from "react";

import { Routes, Route, Navigate } from "react-router-dom";
import "./App.css";

// 최상위 페이지들
import Intro from "./pages/Intro/Intro";
import Login from "./pages/Login/Login";
import Signup from "./pages/Signup/Signup";

// Dashboard 레이아웃
import Dashboard from "./pages/Dashboard/Dashboard";

export default function App() {
  return (
    <Routes>
      {/* 기본 경로는 Intro으로 시작 */}
      <Route path="/" element={<Intro />} />
      {/* 독립 페이지 */}
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      {/* Dashboard 레이아웃 */}
      <Route path="/dashboard" element={<Dashboard />} />
      {/* 정의되지 않은 경로는 Main으로 리다이렉트 */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
