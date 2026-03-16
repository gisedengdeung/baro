// src/hooks/useWebRTC.js
import { useEffect, useRef, useState } from "react";

const CLOUD_URL = "http://localhost:8000";
const EDGE_ID = "edge-default";

export function useWebRTC() {
  const videoRef = useRef(null);
  const pcRef = useRef(null);
  const pollingRef = useRef(null);
  const [error, setError] = useState(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let stopped = false;

    async function start() {
      try {
        // 1. Cloud에서 edge offer 폴링 (edge가 올릴 때까지 대기)
        let offer = null;
        for (let i = 0; i < 20; i++) {
          const res = await fetch(
            `${CLOUD_URL}/api/signaling/offer?edge_id=${EDGE_ID}&receiver=browser`,
            { credentials: "include" },
          );
          const data = await res.json();
          if (data.offer?.sdp) {
            offer = data.offer;
            break;
          }
          await new Promise((r) => setTimeout(r, 1500));
        }
        if (!offer) throw new Error("Edge offer를 받지 못했습니다.");
        if (stopped) return;

        // offer ack
        await fetch(`${CLOUD_URL}/api/signaling/offer/ack`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            edge_id: EDGE_ID,
            receiver: "browser",
            message_id: offer.message_id,
          }),
        });

        // 2. RTCPeerConnection 생성 및 offer 설정
        const pc = new RTCPeerConnection({
          iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
        });
        pcRef.current = pc;

        pc.ontrack = (event) => {
          if (videoRef.current && event.streams[0]) {
            videoRef.current.srcObject = event.streams[0];
            setConnected(true);
          }
        };

        pc.onconnectionstatechange = () => {
          if (
            pc.connectionState === "failed" ||
            pc.connectionState === "disconnected"
          ) {
            setConnected(false);
            setError("WebRTC 연결이 끊겼습니다. 새로고침 해주세요.");
          }
        };

        // 3. ICE candidate → cloud로 전송
        pc.onicecandidate = async (event) => {
          if (!event.candidate) return;
          await fetch(`${CLOUD_URL}/api/signaling/ice`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({
              edge_id: EDGE_ID,
              sender: "browser",
              receiver: "edge",
              candidate: {
                candidate: event.candidate.candidate,
                sdpMid: event.candidate.sdpMid,
                sdpMLineIndex: event.candidate.sdpMLineIndex,
              },
            }),
          });
        };

        await pc.setRemoteDescription(
          new RTCSessionDescription({ type: offer.type, sdp: offer.sdp }),
        );

        // 4. Answer 생성 및 전송
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);

        const answerRes = await fetch(`${CLOUD_URL}/api/signaling/answer`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            edge_id: EDGE_ID,
            sender: "browser",
            receiver: "edge",
            type: answer.type,
            sdp: answer.sdp,
          }),
        });
        const answerData = await answerRes.json();

        // 5. Edge ICE candidates 폴링
        const seenIds = new Set();
        pollingRef.current = setInterval(async () => {
          try {
            const iceRes = await fetch(
              `${CLOUD_URL}/api/signaling/ice?edge_id=${EDGE_ID}&receiver=browser`,
              { credentials: "include" },
            );
            const iceData = await iceRes.json();
            const candidates = iceData.candidates || [];
            const newIds = [];

            for (const raw of candidates) {
              if (raw.message_id && seenIds.has(raw.message_id)) continue;
              if (raw.message_id) {
                seenIds.add(raw.message_id);
                newIds.push(raw.message_id);
              }
              const c = raw.candidate;
              if (!c?.candidate) continue;
              await pc.addIceCandidate(new RTCIceCandidate(c));
            }

            if (newIds.length > 0) {
              await fetch(`${CLOUD_URL}/api/signaling/ice/ack`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify({
                  edge_id: EDGE_ID,
                  receiver: "browser",
                  message_ids: newIds,
                }),
              });
            }
          } catch (e) {
            // polling 오류는 무시
          }
        }, 1000);
      } catch (err) {
        if (!stopped) setError(err.message);
      }
    }

    start();

    return () => {
      stopped = true;
      clearInterval(pollingRef.current);
      pcRef.current?.close();
    };
  }, []);

  return { videoRef, connected, error };
}
