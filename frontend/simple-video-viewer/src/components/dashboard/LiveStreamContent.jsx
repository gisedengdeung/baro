import React, { useCallback, useEffect, useRef, useState } from 'react';
import '../../pages/Dashboard/Dashboard.css';
import { signalingAPI } from '../../services/api';

const STATUS_TEXT = {
  idle: '영상 연결 준비 중',
  waiting_offer: 'Edge 영상 Offer 대기 중',
  connecting: 'WebRTC 연결 중',
  connected: '영상 연결됨',
  reconnecting: '영상 재연결 시도 중',
  failed: '영상 연결 실패. Edge 실행 상태와 signaling API를 확인하세요.',
};

const MAX_BACKOFF_MS = 10000;

export default function LiveStreamContent({ onImageLoad, onStatusChange }) {
  const videoRef = useRef(null);

  const pcRef = useRef(null);
  const offerTimerRef = useRef(null);
  const iceTimerRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const retryDelayRef = useRef(1000);
  const everConnectedRef = useRef(false);
  const cancelledRef = useRef(false);
  const offerPollingEnabledRef = useRef(true);
  const seenCandidatesRef = useRef(new Set());
  const processedOfferIdRef = useRef(null);
  const pendingOfferIdRef = useRef(null);
  const processedIceIdsRef = useRef(new Set());

  const [status, setStatus] = useState('idle');

  const updateStatus = useCallback(
    (nextStatus) => {
      setStatus(nextStatus);
      if (onStatusChange) {
        onStatusChange(nextStatus);
      }
    },
    [onStatusChange]
  );

  const clearTimers = useCallback(() => {
    if (offerTimerRef.current) {
      clearTimeout(offerTimerRef.current);
      offerTimerRef.current = null;
    }
    if (iceTimerRef.current) {
      clearInterval(iceTimerRef.current);
      iceTimerRef.current = null;
    }
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const closePeer = useCallback(() => {
    const pc = pcRef.current;
    if (pc) {
      pc.ontrack = null;
      pc.onicecandidate = null;
      pc.onconnectionstatechange = null;
      try {
        pc.close();
      } catch (e) {
        // no-op
      }
      pcRef.current = null;
    }
  }, []);

  const cleanup = useCallback(() => {
    clearTimers();
    closePeer();
    const video = videoRef.current;
    if (video && video.srcObject) {
      video.srcObject.getTracks?.().forEach((track) => track.stop());
      video.srcObject = null;
    }
  }, [clearTimers, closePeer]);

  const handleLoadedMetadata = useCallback(() => {
    const video = videoRef.current;
    if (!video || !onImageLoad) {
      return;
    }

    onImageLoad({
      naturalWidth: video.videoWidth,
      naturalHeight: video.videoHeight,
      clientWidth: video.clientWidth,
      clientHeight: video.clientHeight,
    });
  }, [onImageLoad]);

  useEffect(() => {
    cancelledRef.current = false;
    offerPollingEnabledRef.current = true;

    const scheduleReconnect = (reason) => {
      if (cancelledRef.current) {
        return;
      }

      offerPollingEnabledRef.current = true;
      cleanup();
      const delay = retryDelayRef.current;
      updateStatus(delay >= MAX_BACKOFF_MS ? 'failed' : 'reconnecting');

      reconnectTimerRef.current = setTimeout(() => {
        if (!cancelledRef.current) {
          startOfferPolling();
        }
      }, delay);

      retryDelayRef.current = Math.min(delay * 2, MAX_BACKOFF_MS);
      console.warn('[WebRTC] reconnect scheduled:', reason, 'delay=', delay);
    };

    const startIcePolling = () => {
      if (iceTimerRef.current) {
        clearInterval(iceTimerRef.current);
      }

      iceTimerRef.current = setInterval(async () => {
        const pc = pcRef.current;
        if (!pc || pc.connectionState === 'closed') {
          return;
        }

        try {
          const payload = await signalingAPI.getIce();
          const candidates = payload?.candidates || [];
          const ackIds = new Set();

          for (const item of candidates) {
            const candidate = item?.candidate;
            const messageId = item?.message_id;
            if (!candidate?.candidate) {
              continue;
            }

            if (messageId && processedIceIdsRef.current.has(messageId)) {
              ackIds.add(messageId);
              continue;
            }

            if (!messageId && seenCandidatesRef.current.has(candidate.candidate)) {
              continue;
            }

            try {
              await pc.addIceCandidate(candidate);
              if (messageId) {
                processedIceIdsRef.current.add(messageId);
                ackIds.add(messageId);
              } else {
                seenCandidatesRef.current.add(candidate.candidate);
              }
            } catch (e) {
              console.warn('[WebRTC] remote ICE add failed:', e);
            }
          }

          if (ackIds.size > 0) {
            try {
              await signalingAPI.ackIce(Array.from(ackIds));
            } catch (e) {
              console.warn('[WebRTC] ICE ack failed:', e);
            }
          }
        } catch (e) {
          console.warn('[WebRTC] ICE polling failed:', e);
        }
      }, 1000);
    };

    const ackCurrentOfferIfNeeded = async () => {
      const offerId = pendingOfferIdRef.current;
      if (!offerId) {
        return;
      }
      if (processedOfferIdRef.current === offerId) {
        return;
      }
      try {
        await signalingAPI.ackOffer(offerId);
        processedOfferIdRef.current = offerId;
      } catch (e) {
        console.warn('[WebRTC] offer ack failed:', e);
      }
    };

    const attachOffer = async (offer) => {
      updateStatus('connecting');

      const pc = new RTCPeerConnection();
      pcRef.current = pc;
      seenCandidatesRef.current = new Set();

      const remoteStream = new MediaStream();
      if (videoRef.current) {
        videoRef.current.srcObject = remoteStream;
      }

      pc.ontrack = (event) => {
        const stream = event.streams?.[0];
        if (stream) {
          stream.getTracks().forEach((track) => remoteStream.addTrack(track));
          offerPollingEnabledRef.current = false;
          if (offerTimerRef.current) {
            clearTimeout(offerTimerRef.current);
            offerTimerRef.current = null;
          }
          updateStatus('connected');
          ackCurrentOfferIfNeeded();
        }
      };

      pc.onicecandidate = async (event) => {
        if (!event.candidate) {
          return;
        }

        try {
          await signalingAPI.postIce({
            candidate: event.candidate.candidate,
            sdpMid: event.candidate.sdpMid,
            sdpMLineIndex: event.candidate.sdpMLineIndex,
          });
        } catch (e) {
          console.warn('[WebRTC] local ICE send failed:', e);
        }
      };

      pc.onconnectionstatechange = () => {
        const connectionState = pc.connectionState;

        if (connectionState === 'connected') {
          everConnectedRef.current = true;
          retryDelayRef.current = 1000;
          offerPollingEnabledRef.current = false;
          if (offerTimerRef.current) {
            clearTimeout(offerTimerRef.current);
            offerTimerRef.current = null;
          }
          updateStatus('connected');
          ackCurrentOfferIfNeeded();
          return;
        }

        if (['disconnected', 'failed', 'closed'].includes(connectionState)) {
          scheduleReconnect(connectionState);
        }
      };

      await pc.setRemoteDescription(
        new RTCSessionDescription({
          type: offer.type,
          sdp: offer.sdp,
        })
      );

      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);

      await signalingAPI.postAnswer({
        type: answer.type,
        sdp: answer.sdp,
      });

      pendingOfferIdRef.current = offer?.message_id || null;

      offerPollingEnabledRef.current = false;
      if (offerTimerRef.current) {
        clearTimeout(offerTimerRef.current);
        offerTimerRef.current = null;
      }
      startIcePolling();
    };

    const pollOffer = async () => {
      if (cancelledRef.current) {
        return;
      }
      if (!offerPollingEnabledRef.current) {
        return;
      }

      updateStatus('waiting_offer');

      try {
        const payload = await signalingAPI.getOffer();
        const offer = payload?.offer;

        if (!offer) {
          offerTimerRef.current = setTimeout(pollOffer, 1000);
          return;
        }

        if (offer?.message_id && offer.message_id === processedOfferIdRef.current) {
          offerTimerRef.current = setTimeout(pollOffer, 1000);
          return;
        }

        await attachOffer(offer);
      } catch (e) {
        console.warn('[WebRTC] offer polling failed:', e);
        scheduleReconnect('offer_poll_failed');
      }
    };

    const startOfferPolling = () => {
      offerPollingEnabledRef.current = true;
      cleanup();
      updateStatus(everConnectedRef.current ? 'reconnecting' : 'idle');
      pollOffer();
    };

    startOfferPolling();

    return () => {
      cancelledRef.current = true;
      cleanup();
    };
  }, [cleanup, updateStatus]);

  const showOverlay = status !== 'connected';

  return (
    <div className="live-stream-container" style={{ position: 'relative' }}>
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        style={{ width: '100%', height: '100%', objectFit: 'cover', background: '#000' }}
        onLoadedMetadata={handleLoadedMetadata}
      />

      {showOverlay && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'rgba(0,0,0,0.55)',
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            textAlign: 'center',
            padding: '16px',
            fontSize: '14px',
            lineHeight: 1.4,
          }}
        >
          {STATUS_TEXT[status] || STATUS_TEXT.idle}
        </div>
      )}
    </div>
  );
}
