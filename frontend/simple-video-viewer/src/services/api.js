import axios from 'axios';

const trimSlash = (value) => value.replace(/\/$/, '');

const API_BASE_URL = trimSlash(process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000');
const WS_BASE_URL = trimSlash(
  process.env.REACT_APP_WS_BASE_URL || API_BASE_URL.replace(/^http/i, 'ws')
);
const EDGE_ID = process.env.REACT_APP_EDGE_ID || 'edge-default';

const withEdgeId = (params = {}) => ({
  ...params,
  edge_id: params.edge_id || EDGE_ID,
});

export const runtimeConfig = {
  apiBaseUrl: API_BASE_URL,
  wsBaseUrl: WS_BASE_URL,
  edgeId: EDGE_ID,
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

export const signalingAPI = {
  getOffer: async () => {
    const response = await apiClient.get('/api/signaling/offer', {
      params: { edge_id: EDGE_ID, receiver: 'browser' },
    });
    return response.data;
  },
  ackOffer: async (messageId) => {
    const response = await apiClient.post('/api/signaling/offer/ack', {
      edge_id: EDGE_ID,
      receiver: 'browser',
      message_id: messageId,
    });
    return response.data;
  },
  postAnswer: async ({ type, sdp }) => {
    const response = await apiClient.post('/api/signaling/answer', {
      edge_id: EDGE_ID,
      sender: 'browser',
      receiver: 'edge',
      type,
      sdp,
    });
    return response.data;
  },
  postIce: async (candidate) => {
    const response = await apiClient.post('/api/signaling/ice', {
      edge_id: EDGE_ID,
      sender: 'browser',
      receiver: 'edge',
      candidate,
    });
    return response.data;
  },
  getIce: async () => {
    const response = await apiClient.get('/api/signaling/ice', {
      params: { edge_id: EDGE_ID, receiver: 'browser' },
    });
    return response.data;
  },
  ackIce: async (messageIds) => {
    const response = await apiClient.post('/api/signaling/ice/ack', {
      edge_id: EDGE_ID,
      receiver: 'browser',
      message_ids: messageIds,
    });
    return response.data;
  },
};
