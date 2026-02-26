import { create } from 'zustand';
import { authAPI, setAuthFailureHandler } from '../services/api';

const getAuthErrorMessage = (error, fallbackMessage) => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') {
    return detail;
  }
  if (Array.isArray(detail) && detail.length > 0 && typeof detail[0]?.msg === 'string') {
    return detail[0].msg;
  }
  return fallbackMessage;
};

const useAuthStore = create((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  initialized: false,
  error: null,

  clearAuth: () => {
    set({
      user: null,
      isAuthenticated: false,
      error: null,
      isLoading: false,
      initialized: true,
    });
  },

  bootstrapAuth: async () => {
    if (get().initialized || get().isLoading) {
      return;
    }

    set({ isLoading: true, error: null });

    try {
      const me = await authAPI.me();
      set({
        user: me,
        isAuthenticated: true,
        isLoading: false,
        initialized: true,
        error: null,
      });
      return;
    } catch (_error) {
      // ignore and try refresh below
    }

    try {
      await authAPI.refresh();
      const me = await authAPI.me();
      set({
        user: me,
        isAuthenticated: true,
        isLoading: false,
        initialized: true,
        error: null,
      });
    } catch (_error) {
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        initialized: true,
        error: null,
      });
    }
  },

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authAPI.login(email, password);
      set({
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
        initialized: true,
        error: null,
      });
      return response.user;
    } catch (error) {
      set({ isLoading: false, error: getAuthErrorMessage(error, '로그인에 실패했습니다.') });
      throw error;
    }
  },

  signup: async (email, password, role) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authAPI.signup(email, password, role);
      set({
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
        initialized: true,
        error: null,
      });
      return response.user;
    } catch (error) {
      set({ isLoading: false, error: getAuthErrorMessage(error, '회원가입에 실패했습니다.') });
      throw error;
    }
  },

  refresh: async () => {
    await authAPI.refresh();
    const me = await authAPI.me();
    set({
      user: me,
      isAuthenticated: true,
      initialized: true,
      error: null,
    });
  },

  logout: async () => {
    try {
      await authAPI.logout();
    } finally {
      get().clearAuth();
    }
  },
}));

setAuthFailureHandler(() => {
  useAuthStore.getState().clearAuth();
});

export default useAuthStore;
