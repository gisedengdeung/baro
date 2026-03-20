// src/hooks/useWebRTC.js
import { useCallback, useEffect, useRef, useState } from 'react';
import { signalingAPI } from '../services/api';

const MAX_BACKOFF_MS = 10000;

export function useWebRTC(onImageLoad) {
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
      setStatus(delay >= MAX_BACKOFF_MS ? 'failed' : 'reconnecting');

      reconnectTimerRef.current = setTimeout(() => {
        if (!cancelledRef.current) {
          startOfferPolling();
        }
      }, delay);

      retryDelayRef.current = Math.min(delay * 2, MAX_BACKOFF_MS);
      console.warn('[useWebRTC] reconnect scheduled:', reason, 'delay=', delay);
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
              console.warn('[useWebRTC] remote ICE add failed:', e);
            }
          }

          if (ackIds.size > 0) {
            try {
              await signalingAPI.ackIce(Array.from(ackIds));
            } catch (e) {
              console.warn('[useWebRTC] ICE ack failed:', e);
            }
          }
        } catch (e) {
          console.warn('[useWebRTC] ICE polling failed:', e);
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
        console.warn('[useWebRTC] offer ack failed:', e);
      }
    };

    const attachOffer = async (offer) => {
      setStatus('connecting');

      const pc = new RTCPeerConnection({
        iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
      });
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
          setStatus('connected');
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
          console.warn('[useWebRTC] local ICE send failed:', e);
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
          setStatus('connected');
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

      setStatus('waiting_offer');

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
        console.warn('[useWebRTC] offer polling failed:', e);
        scheduleReconnect('offer_poll_failed');
      }
    };

    const startOfferPolling = () => {
      offerPollingEnabledRef.current = true;
      cleanup();
      setStatus(everConnectedRef.current ? 'reconnecting' : 'idle');
      pollOffer();
    };

    startOfferPolling();

    return () => {
      cancelledRef.current = true;
      cleanup();
    };
  }, [cleanup]);

  return {
    videoRef,
    status,
    connected: status === 'connected',
    handleLoadedMetadata,
  };
}
