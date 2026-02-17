import React from 'react';

import { Routes, Route, Navigate } from 'react-router-dom';
import './App.css';

// 최상위 페이지들
import Main  from './pages/main/Main';
import Intro from './pages/Intro/Intro';
import Login from './pages/Login/Login';

// Dashboard 레이아웃
import Dashboard from './pages/Dashboard/Dashboard';


export default function App() {
  return (
    <Routes>
      {/* 기본 경로는 Main으로 시작 */}
      <Route path="/" element={<Main />} />
      {/* 독립 페이지 */}
      <Route path="/intro" element={<Intro />} />
      <Route path="/login" element={<Login />} />
      {/* Dashboard 레이아웃 */}
      <Route path="/dashboard" element={<Dashboard />} />
      {/* 정의되지 않은 경로는 Main으로 리다이렉트 */}
      <Route path="*" element={<Navigate to="/" replace />} />

    </Routes>
  );
}


