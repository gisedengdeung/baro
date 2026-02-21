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

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const logAPI = {
  getLogs: async (limit = 50) => {
    try {
      const response = await apiClient.get('/api/logs', { params: { limit } });
      return response.data;
    } catch (error) {
      console.error('Error fetching logs:', error);
      throw error;
    }
  },
};

export const zoneAPI = {
  getZones: async () => {
    try {
      const response = await apiClient.get('/api/zones');
      return response.data;
    } catch (error) {
      console.error('Error fetching zones:', error);
      throw error;
    }
  },
  createZone: async (zoneData) => {
    try {
      const response = await apiClient.post('/api/zones', zoneData, {
        params: withEdgeId(),
      });
      return response.data;
    } catch (error) {
      console.error('Error creating zone:', error);
      throw error;
    }
  },
  updateZone: async (zoneId, zoneData) => {
    try {
      const response = await apiClient.put(`/api/zones/${zoneId}`, zoneData, {
        params: withEdgeId(),
      });
      return response.data;
    } catch (error) {
      console.error(`Error updating zone ${zoneId}:`, error);
      throw error;
    }
  },
  deleteZone: async (zoneId) => {
    try {
      const response = await apiClient.delete(`/api/zones/${zoneId}`, {
        params: withEdgeId(),
      });
      return response.data;
    } catch (error) {
      console.error(`Error deleting zone ${zoneId}:`, error);
      throw error;
    }
  },
};

export const controlAPI = {
  startAutomaticMode: async (confirmed = false) => {
    try {
      const response = await apiClient.post('/api/control/start_automatic', null, {
        params: withEdgeId({ confirmed }),
      });
      return response.data;
    } catch (error) {
      console.error('Error starting automatic mode:', error);
      throw error;
    }
  },
  startMaintenanceMode: async () => {
    try {
      const response = await apiClient.post('/api/control/start_maintenance', null, {
        params: withEdgeId(),
      });
      return response.data;
    } catch (error) {
      console.error('Error starting maintenance mode:', error);
      throw error;
    }
  },
  stopSystem: async () => {
    try {
      const response = await apiClient.post('/api/control/stop', null, {
        params: withEdgeId(),
      });
      return response.data;
    } catch (error) {
      console.error('Error stopping system:', error);
      throw error;
    }
  },
  getStatus: async () => {
    try {
      const response = await apiClient.get('/api/control/status', {
        params: withEdgeId(),
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching status:', error);
      throw error;
    }
  },
  resetSystem: async () => {
    try {
      const response = await apiClient.post('/api/control/reset', null, {
        params: withEdgeId(),
      });
      return response.data;
    } catch (error) {
      console.error('Error resetting system:', error);
      throw error;
    }
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
