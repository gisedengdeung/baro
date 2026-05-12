import axios from 'axios';

const trimSlash = (value) => value.replace(/\/$/, '');
const isBrowser = typeof window !== 'undefined';
const defaultOrigin = isBrowser ? window.location.origin : 'http://localhost:8000';
const defaultWsOrigin = defaultOrigin.replace(/^http/i, 'ws');

const resolveBaseUrl = (value, fallback) => {
  const normalized = (value || '').trim();
  return trimSlash(normalized || fallback);
};

const parseIceServers = (rawValue) => {
  const fallback = [{ urls: 'stun:stun.l.google.com:19302' }];
  const normalized = (rawValue || '').trim();
  if (!normalized) {
    return fallback;
  }

  try {
    const parsed = JSON.parse(normalized);
    if (!Array.isArray(parsed) || parsed.length === 0) {
      return fallback;
    }
    return parsed;
  } catch (error) {
    console.warn('[api] invalid REACT_APP_WEBRTC_ICE_SERVERS_JSON, using fallback STUN server', error);
    return fallback;
  }
};

const API_BASE_URL = resolveBaseUrl(process.env.REACT_APP_API_BASE_URL, defaultOrigin);
const WS_BASE_URL = resolveBaseUrl(process.env.REACT_APP_WS_BASE_URL, defaultWsOrigin);
const EDGE_ID = process.env.REACT_APP_EDGE_ID || 'edge-default';
const WEBRTC_ICE_SERVERS = parseIceServers(process.env.REACT_APP_WEBRTC_ICE_SERVERS_JSON);

const SESSION_ID = (() => {
  const key = 'signaling_session_id';
  let id = sessionStorage.getItem(key);
  if (!id) {
    id = (typeof crypto !== 'undefined' && crypto.randomUUID)
      ? crypto.randomUUID()
      : Math.random().toString(36).slice(2) + Date.now().toString(36);
    sessionStorage.setItem(key, id);
  }
  return id;
})();
const BROWSER_RECEIVER = `browser-${SESSION_ID}`;

const withEdgeId = (params = {}) => ({
  ...params,
  edge_id: params.edge_id || EDGE_ID,
});

export const runtimeConfig = {
  apiBaseUrl: API_BASE_URL,
  wsBaseUrl: WS_BASE_URL,
  edgeId: EDGE_ID,
  webrtcIceServers: WEBRTC_ICE_SERVERS,
};

export const getWsUrl = (path = '/ws/logs') => `${WS_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;

const baseConfig = {
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
};

const rawClient = axios.create(baseConfig);
const apiClient = axios.create(baseConfig);

let refreshPromise = null;
let authFailureHandler = null;

export const setAuthFailureHandler = (handler) => {
  authFailureHandler = typeof handler === 'function' ? handler : null;
};

const shouldSkipRefresh = (url = '') => {
  return url.includes('/api/auth/login') || url.includes('/api/auth/logout') || url.includes('/api/auth/refresh');
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error?.config;
    const status = error?.response?.status;

    if (!originalRequest || status !== 401 || originalRequest._retry || shouldSkipRefresh(originalRequest.url)) {
      throw error;
    }

    originalRequest._retry = true;

    try {
      if (!refreshPromise) {
        refreshPromise = rawClient.post('/api/auth/refresh').finally(() => {
          refreshPromise = null;
        });
      }
      await refreshPromise;
      return apiClient(originalRequest);
    } catch (refreshError) {
      if (authFailureHandler) {
        authFailureHandler();
      }
      throw refreshError;
    }
  }
);

export const authAPI = {
  signup: async (email, password, role) => {
    const response = await rawClient.post('/api/auth/signup', { email, password, role });
    return response.data;
  },
  login: async (email, password) => {
    const response = await rawClient.post('/api/auth/login', { email, password });
    return response.data;
  },
  me: async () => {
    const response = await rawClient.get('/api/auth/me');
    return response.data;
  },
  refresh: async () => {
    const response = await rawClient.post('/api/auth/refresh');
    return response.data;
  },
  logout: async () => {
    const response = await rawClient.post('/api/auth/logout');
    return response.data;
  },
};

export const logAPI = {
  getLogs: async (limit = 50) => {
    const response = await apiClient.get('/api/logs', { params: { limit } });
    return response.data;
  },
  getClipBlob: async (logId) => {
    const response = await apiClient.get(`/api/logs/${logId}/clip`, {
      responseType: 'blob',
    });
    return response.data;
  },
};

export const zoneAPI = {
  getZones: async () => {
    const response = await apiClient.get('/api/zones');
    return response.data;
  },
  createZone: async (zoneData) => {
    const response = await apiClient.post('/api/zones', zoneData, {
      params: withEdgeId(),
    });
    return response.data;
  },
  updateZone: async (zoneId, zoneData) => {
    const response = await apiClient.put(`/api/zones/${zoneId}`, zoneData, {
      params: withEdgeId(),
    });
    return response.data;
  },
  deleteZone: async (zoneId) => {
    const response = await apiClient.delete(`/api/zones/${zoneId}`, {
      params: withEdgeId(),
    });
    return response.data;
  },
};

export const controlAPI = {
  startAutomaticMode: async (confirmed = false) => {
    const response = await apiClient.post('/api/control/start_automatic', null, {
      params: withEdgeId({ confirmed }),
    });
    return response.data;
  },
  startMaintenanceMode: async () => {
    const response = await apiClient.post('/api/control/start_maintenance', null, {
      params: withEdgeId(),
    });
    return response.data;
  },
  stopSystem: async () => {
    const response = await apiClient.post('/api/control/stop', null, {
      params: withEdgeId(),
    });
    return response.data;
  },
  getStatus: async () => {
    const response = await apiClient.get('/api/control/status', {
      params: withEdgeId(),
    });
    return response.data;
  },
  resetSystem: async () => {
    const response = await apiClient.post('/api/control/reset', null, {
      params: withEdgeId(),
    });
    return response.data;
  },
  startTestRun: async (speedPercent = 30) => {
    const response = await apiClient.post('/api/control/test/start', null, {
      params: withEdgeId({ speed_percent: speedPercent }),
    });
    return response.data;
  },
  setTestSpeed: async (speedPercent) => {
    const response = await apiClient.post('/api/control/test/speed', null, {
      params: withEdgeId({ speed_percent: speedPercent }),
    });
    return response.data;
  },
  stopTestRun: async () => {
    const response = await apiClient.post('/api/control/test/stop', null, {
      params: withEdgeId(),
    });
    return response.data;
  },
};

export const safetyAPI = {
  getScore: async () => {
    const response = await apiClient.get('/api/safety/score');
    return response.data;
  },
  getHistory: async (days = 7) => {
    const response = await apiClient.get('/api/safety/history', { params: { days } });
    return response.data;
  },
  explain: async () => {
    const response = await apiClient.post('/api/safety/explain');
    return response.data;
  },
};

export const signalingAPI = {
  getOffer: async () => {
    const response = await apiClient.get('/api/signaling/offer', {
      params: { edge_id: EDGE_ID, receiver: BROWSER_RECEIVER },
    });
    return response.data;
  },
  ackOffer: async (messageId) => {
    const response = await apiClient.post('/api/signaling/offer/ack', {
      edge_id: EDGE_ID,
      receiver: BROWSER_RECEIVER,
      message_id: messageId,
    });
    return response.data;
  },
  postAnswer: async ({ type, sdp }) => {
    const response = await apiClient.post('/api/signaling/answer', {
      edge_id: EDGE_ID,
      sender: BROWSER_RECEIVER,
      receiver: `edge-${SESSION_ID}`,
      type,
      sdp,
    });
    return response.data;
  },
  postIce: async (candidate) => {
    const response = await apiClient.post('/api/signaling/ice', {
      edge_id: EDGE_ID,
      sender: BROWSER_RECEIVER,
      receiver: `edge-${SESSION_ID}`,
      candidate,
    });
    return response.data;
  },
  getIce: async () => {
    const response = await apiClient.get('/api/signaling/ice', {
      params: { edge_id: EDGE_ID, receiver: BROWSER_RECEIVER },
    });
    return response.data;
  },
  ackIce: async (messageIds) => {
    const response = await apiClient.post('/api/signaling/ice/ack', {
      edge_id: EDGE_ID,
      receiver: BROWSER_RECEIVER,
      message_ids: messageIds,
    });
    return response.data;
  },
};
