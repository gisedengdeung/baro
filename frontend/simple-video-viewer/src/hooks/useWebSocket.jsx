// // src/hooks/useWebSocket.js
// import { useEffect, useRef, useState, useCallback } from 'react';
//
// export function useWebSocket(
//   url,
//   onMessage,
//   protocols,
//   reconnectInterval = 5000,
//   maxRetries = 3
// ) {
//   const wsRef = useRef(null);
//   const reconnectTimer = useRef(null);
//   const retryCount = useRef(0);
//   const shouldReconnect = useRef(true);
//
//   const [status, setStatus] = useState('connecting');
//   const [error, setError] = useState(null);
//
//   const connect = useCallback(() => {
//     console.log("2. [WS-Debug] connect 함수 실행됨. 재접속 플래그:", shouldReconnect.current);
//     if (!shouldReconnect.current) {
//       console.log("3. [WS-Debug] 재접속이 비활성화되어 연결 시도를 중단합니다.");
//       return;
//     }
//
//     console.log("3. [WS-Debug] new WebSocket() 객체 생성을 시도합니다. URL:", url);
//     const ws = new WebSocket(url, protocols || []);
//     wsRef.current = ws;
//     setStatus('connecting');
//     setError(null);
//
//     ws.onopen = () => {
//       console.log("4. [WS-Debug] ✅ 연결 성공 (onopen)!");
//       setStatus('open');
//       retryCount.current = 0;
//     };
//
//     ws.onmessage = (event) => {
//       console.log("✉️ [useWebSocket] Message received:", event.data); // 디버깅 로그 추가
//       try {
//         const data = JSON.parse(event.data);
//         onMessage(data);
//       } catch {
//         onMessage(event.data);
//       }
//     };
//
//     ws.onclose = (e) => {
//       console.log("6. [WS-Debug] ⛔️ 연결 닫힘 (onclose)");
//       setStatus('closed');
//       if (!shouldReconnect.current) {
//         console.log("[WS-Debug] 재접속 플래그가 false이므로 여기서 종료합니다.");
//         return;
//       }
//       if (retryCount.current < maxRetries) {
//         retryCount.current += 1;
//         console.warn(
//           `[WS] Disconnected (reason: ${e.reason}), retry ${retryCount.current}/${maxRetries} in ${reconnectInterval}ms`
//         );
//         reconnectTimer.current = setTimeout(connect, reconnectInterval);
//       } else {
//         console.error(
//           `[WS] Disconnected. Max retries (${maxRetries}) reached. No further reconnects.`
//         );
//       }
//     };
//
//     ws.onerror = (err) => {
//       console.error("7. [WS-Debug] ❌ 에러 발생 (onerror)", err);
//       setError(err);
//       // onerror는 보통 onclose를 자동으로 트리거하므로, 여기서 상태를 'error'로 설정할 수 있습니다.
//       setStatus('error');
//       ws.close();
//     };
//   }, [url, protocols, reconnectInterval, maxRetries, onMessage]);
//
//   useEffect(() => {
//     console.log("1. [WS-Debug] useEffect 실행됨. connect 함수를 호출합니다.");
//     shouldReconnect.current = true;
//     connect();
//
//     return () => {
//       console.log("8. [WS-Debug] useEffect 클린업 함수 실행. 연결을 종료합니다.");
//       // 재연결 로직을 중단시키기 위해 플래그를 설정합니다.
//       shouldReconnect.current = false;
//       // 타이머가 있다면 제거합니다.
//       clearTimeout(reconnectTimer.current);
//       if (wsRef.current) {
//         wsRef.current.close();
//       }
//     };
//   }, [connect]);
//
//   return { socket: wsRef.current, status, error };
// }