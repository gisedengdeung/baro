import { create } from "zustand";
import {
  controlAPI,
  getWsUrl,
  logAPI,
  runtimeConfig,
  zoneAPI,
} from "../services/api";

let socketInstance = null;
let timerInstance = null;

const isSameLog = (a, b) => {
  if (!a || !b) return false;
  if (a.id != null && b.id != null) {
    return String(a.id) === String(b.id);
  }
  if (a.event_uid && b.event_uid) {
    return a.event_uid === b.event_uid;
  }
  return false;
};

const toRatioZones = (zones, imageSize) => {
  const width = imageSize?.naturalWidth;
  const height = imageSize?.naturalHeight;

  return (zones || []).map((zone) => ({
    ...zone,
    points: (zone.points || []).map((p) => {
      if (typeof p.xRatio === "number" && typeof p.yRatio === "number") {
        return p;
      }

      if (width && height) {
        return {
          ...p,
          xRatio: p.x / width,
          yRatio: p.y / height,
        };
      }

      return {
        ...p,
        xRatio: null,
        yRatio: null,
      };
    }),
  }));
};

const useDashboardStore = create((set, get) => ({
  logs: [],
  zones: [],
  zonesRaw: [],
  operationMode: null,
  conveyorStatus: null,
  conveyorSpeed: 0,
  riskLevel: "SAFE",
  isLocked: false,
  testIsActive: false,
  testSpeed: 0,
  testSpeedInput: 30,
  loading: false,
  error: null,
  popupError: null,
  globalAlert: null,

  personDetectedInMaintenance: false,
  lotoSensorOn: false,

  activeId: null,
  isDangerMode: false,
  configAction: null,
  selectedZoneId: null,
  newZoneName: "",
  imageSize: null,

  wsStatus: "closed",
  videoStatus: "idle",
  currentTime: "",

  initialize: async () => {
    get().connect();
    get().startTimer();
    await get().fetchSystemStatus();
    await get().fetchLogs(true);
    await get().fetchZones();
  },

  disconnect: () => {
    if (socketInstance) {
      socketInstance.close(4000, "User-initiated disconnect");
      socketInstance = null;
    }
    get().stopTimer();
    set({ wsStatus: "closed" });
  },

  connect: () => {
    if (socketInstance) {
      return;
    }

    set({ wsStatus: "connecting" });
    socketInstance = new WebSocket(getWsUrl("/ws/logs"));

    socketInstance.onopen = () => {
      set({ wsStatus: "open" });
    };

    socketInstance.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);

        switch (message.type) {
          case "LOG":
            get().addLog(message.data);
            break;
          case "STATUS_UPDATE": {
            const {
              operation_mode,
              conveyor_status,
              conveyor_speed,
              risk_level,
              is_locked,
              test_is_active,
              test_speed,
            } = message.data;
            const normalizedMode = operation_mode || null;
            const normalizedTestSpeed = Number.isFinite(Number(test_speed))
              ? Number(test_speed)
              : 0;
            set({
              operationMode: normalizedMode,
              conveyorStatus: conveyor_status,
              conveyorSpeed: conveyor_speed,
              riskLevel: risk_level,
              isLocked: is_locked,
              testIsActive: Boolean(
                test_is_active || normalizedMode === "TEST",
              ),
              testSpeed: normalizedTestSpeed,
              testSpeedInput:
                normalizedMode === "TEST"
                  ? normalizedTestSpeed
                  : get().testSpeedInput,
            });
            break;
          }
          default:
            break;
        }
      } catch (e) {
        console.error("WebSocket 메시지 처리 오류:", e);
      }
    };

    socketInstance.onerror = () => {
      set({ wsStatus: "error" });
    };

    socketInstance.onclose = () => {
      socketInstance = null;
      set({ wsStatus: "closed" });
    };
  },

  startTimer: () => {
    if (timerInstance) {
      return;
    }

    timerInstance = setInterval(() => {
      const now = new Date();
      const year = now.getFullYear();
      const month = String(now.getMonth() + 1).padStart(2, "0");
      const date = String(now.getDate()).padStart(2, "0");
      const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
      const day = dayNames[now.getDay()];
      let h = now.getHours();
      const m = String(now.getMinutes()).padStart(2, "0");
      const ampm = h >= 12 ? "PM" : "AM";
      if (h > 12) h -= 12;
      if (h === 0) h = 12;
      set({
        currentTime: `${year}-${month}-${date} (${day}) / ${ampm}-${h}:${m}`,
      });
    }, 1000);
  },

  stopTimer: () => {
    if (!timerInstance) {
      return;
    }
    clearInterval(timerInstance);
    timerInstance = null;
  },

  setVideoStatus: (status) => set({ videoStatus: status }),

  fetchSystemStatus: async () => {
    try {
      const data = await controlAPI.getStatus();
      const edge = data?.edge_status;
      if (!edge) {
        return;
      }
      const normalizedMode = edge.operation_mode || null;
      const normalizedTestSpeed = Number.isFinite(Number(edge.test_speed))
        ? Number(edge.test_speed)
        : 0;
      set({
        operationMode: normalizedMode,
        conveyorSpeed: edge.conveyor_speed || 0,
        riskLevel: edge.risk_level || "SAFE",
        isLocked: Boolean(edge.is_locked),
        testIsActive: Boolean(edge.test_is_active || normalizedMode === "TEST"),
        testSpeed: normalizedTestSpeed,
        testSpeedInput:
          normalizedMode === "TEST"
            ? normalizedTestSpeed
            : get().testSpeedInput,
      });
    } catch (e) {
      console.error("상태 조회 실패", e);
    }
  },

  fetchLogs: async (showLoading = false) => {
    if (showLoading) set({ loading: true });
    set({ error: null });
    try {
      const data = await logAPI.getLogs();
      set({ logs: data });
    } catch (e) {
      console.error(e);
      set({ error: "로그를 불러오는 중 오류가 발생했습니다." });
    } finally {
      if (showLoading) set({ loading: false });
    }
  },

  fetchZones: async () => {
    try {
      const data = await zoneAPI.getZones();
      set((state) => ({
        zonesRaw: data,
        zones: toRatioZones(data, state.imageSize),
      }));
    } catch (e) {
      console.error("구역 조회 실패", e);
    }
  },

  addLog: (newLog) => {
    set((state) => {
      const exists = state.logs.some((log) => isSameLog(log, newLog));
      if (exists) {
        return {
          logs: state.logs.map((log) => (isSameLog(log, newLog) ? { ...log, ...newLog } : log)),
        };
      }
      return { logs: [newLog, ...state.logs] };
    });

    const riskLevel = newLog?.log_risk_level;
    if (riskLevel === "CRITICAL" || riskLevel === "HIGH") {
      set({ globalAlert: newLog });
    }
  },

  upsertLog: (updatedLog) => {
    set((state) => {
      const found = state.logs.some((log) => isSameLog(log, updatedLog));
      if (!found) {
        return { logs: [updatedLog, ...state.logs] };
      }
      return {
        logs: state.logs.map((log) => (isSameLog(log, updatedLog) ? { ...log, ...updatedLog } : log)),
      };
    });
  },

  resetSystem: async () => {
    set({ loading: true });
    try {
      await controlAPI.resetSystem();
    } catch (e) {
      const errorDetail = e.response?.data?.detail || e.message;
      get().setPopupError(`리셋 실패: ${errorDetail}`);
    } finally {
      set({ loading: false });
    }
  },

  setActiveId: (id) => set({ activeId: id }),

  setTestSpeedInput: (value) => {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
      return;
    }
    const normalized = Math.max(0, Math.min(100, Math.round(parsed / 5) * 5));
    set({ testSpeedInput: normalized });
  },

  startTestRun: async () => {
    const { operationMode, isLocked, testSpeedInput } = get();
    if (isLocked) {
      get().setPopupError(
        "시스템이 잠금(LOCKED) 상태입니다. 리셋 후 다시 시도하세요.",
      );
      return;
    }
    if (operationMode !== "STOPPED") {
      get().setPopupError(
        "테스트 운행은 정지(STOPPED) 상태에서만 시작할 수 있습니다.",
      );
      return;
    }

    set({ loading: true });
    try {
      const speed = Math.max(0, Math.min(100, Number(testSpeedInput) || 30));
      await controlAPI.startTestRun(speed);
    } catch (e) {
      const errorDetail = e.response?.data?.detail || e.message;
      get().setPopupError(`테스트 운행 시작 실패: ${errorDetail}`);
    } finally {
      set({ loading: false });
    }
  },

  applyTestSpeed: async () => {
    const { operationMode, testSpeedInput } = get();
    if (operationMode !== "TEST") {
      get().setPopupError("테스트 모드(TEST)에서만 속도 변경이 가능합니다.");
      return;
    }

    set({ loading: true });
    try {
      const speed = Math.max(0, Math.min(100, Number(testSpeedInput) || 0));
      await controlAPI.setTestSpeed(speed);
    } catch (e) {
      const errorDetail = e.response?.data?.detail || e.message;
      get().setPopupError(`테스트 속도 변경 실패: ${errorDetail}`);
    } finally {
      set({ loading: false });
    }
  },

  stopTestRun: async () => {
    set({ loading: true });
    try {
      await controlAPI.stopTestRun();
    } catch (e) {
      const errorDetail = e.response?.data?.detail || e.message;
      get().setPopupError(`테스트 운행 종료 실패: ${errorDetail}`);
    } finally {
      set({ loading: false });
    }
  },

  setPopupError: (message) => {
    set({ popupError: message });
    setTimeout(() => set({ popupError: null }), 5000);
  },

  handleControl: async (controlType, confirmed = false) => {
    if (get().isLocked) {
      get().setPopupError(
        "시스템이 잠금(LOCKED) 상태입니다. 리셋이 필요합니다.",
      );
      return;
    }

    if (controlType === "start_automatic") {
      const { riskLevel } = get();
      if (riskLevel === "LOTO_RISK_DETECTED") {
        get().setPopupError(
          "LOTO 조건 위반: 정비 구역에 사람이 감지되어 시스템을 시작할 수 없습니다.",
        );
        return;
      }
    }

    set({ loading: true });
    try {
      let response;
      if (controlType === "start_automatic") {
        response = await controlAPI.startAutomaticMode(confirmed);
      } else if (controlType === "start_maintenance") {
        response = await controlAPI.startMaintenanceMode();
      } else if (controlType === "stop") {
        response = await controlAPI.stopSystem();
      }

      if (response && response.confirmation_required) {
        if (window.confirm(response.message)) {
          await get().handleControl(controlType, true);
        }
      }
    } catch (e) {
      const errorDetail = e.response?.data?.detail || e.message;
      get().setPopupError(`명령 실행 중 오류: ${errorDetail}`);
    } finally {
      set({ loading: false });
    }
  },

  enterDangerMode: () => set({ isDangerMode: true, configAction: "view" }),
  exitDangerMode: () =>
    set({
      isDangerMode: false,
      configAction: null,
      selectedZoneId: null,
      newZoneName: "",
    }),

  setConfigAction: (action) => {
    set((state) => {
      const newState = { ...state, configAction: action };

      switch (action) {
        case "create":
          newState.selectedZoneId = null;
          newState.newZoneName = "";
          break;
        case "update":
          if (state.selectedZoneId) {
            const selectedZone = state.zones.find(
              (z) => z.id === state.selectedZoneId,
            );
            newState.newZoneName = selectedZone ? selectedZone.name : "";
          }
          break;
        case "view":
          newState.selectedZoneId = null;
          break;
        default:
          break;
      }
      return newState;
    });
  },

  setSelectedZoneId: (id) => set({ selectedZoneId: id, configAction: "view" }),
  setNewZoneName: (name) => set({ newZoneName: name }),

  setImageSize: (size) => {
    set((state) => ({
      imageSize: size,
      zones: toRatioZones(state.zonesRaw, size),
    }));
  },

  handleCreateZone: async (ratioPoints) => {
    const { newZoneName, imageSize } = get();

    if (!imageSize?.naturalWidth || !imageSize?.naturalHeight) {
      get().setPopupError(
        "영상 해상도 정보를 아직 받지 못했습니다. 잠시 후 다시 시도하세요.",
      );
      return;
    }

    const name =
      newZoneName.trim() || `새 구역 ${new Date().toLocaleTimeString()}`;
    const newZoneId = `zone_${Date.now()}`;

    const points = ratioPoints.map((r) => ({
      x: Math.round(r.x * imageSize.naturalWidth),
      y: Math.round(r.y * imageSize.naturalHeight),
    }));

    try {
      await zoneAPI.createZone({
        id: newZoneId,
        name,
        points,
      });
      await get().fetchZones();
      get().exitDangerMode();
    } catch (err) {
      const errorDetail = err.response?.data?.detail || err.message;
      const errorMessage =
        typeof errorDetail === "object"
          ? JSON.stringify(errorDetail, null, 2)
          : errorDetail;
      get().setPopupError(`위험 구역 생성 실패:\n${errorMessage}`);
    }
  },

  handleUpdateZone: async (ratioPoints) => {
    const { selectedZoneId, imageSize, zones } = get();
    if (!selectedZoneId) return;

    if (!imageSize?.naturalWidth || !imageSize?.naturalHeight) {
      get().setPopupError(
        "영상 해상도 정보를 아직 받지 못했습니다. 잠시 후 다시 시도하세요.",
      );
      return;
    }

    const existingZone = zones.find((z) => z.id === selectedZoneId);
    if (!existingZone) return;

    const points = ratioPoints.map((r) => ({
      x: Math.round(r.x * imageSize.naturalWidth),
      y: Math.round(r.y * imageSize.naturalHeight),
    }));

    try {
      await zoneAPI.updateZone(selectedZoneId, {
        name: existingZone.name,
        points,
      });
      await get().fetchZones();
      get().exitDangerMode();
    } catch (err) {
      const errorDetail = err.response?.data?.detail || err.message;
      const errorMessage =
        typeof errorDetail === "object"
          ? JSON.stringify(errorDetail, null, 2)
          : errorDetail;
      get().setPopupError(`위험 구역 업데이트 실패:\n${errorMessage}`);
    }
  },

  handleDeleteZone: async () => {
    const { selectedZoneId, zones } = get();
    if (!selectedZoneId) return;

    const targetName =
      zones.find((z) => z.id === selectedZoneId)?.name || "선택된 구역";
    if (!window.confirm(`${targetName}을 삭제하시겠습니까?`)) return;

    try {
      await zoneAPI.deleteZone(selectedZoneId);
      await get().fetchZones();
      set({ configAction: "view", selectedZoneId: null });
    } catch (err) {
      const errorDetail = err.response?.data?.detail || err.message;
      const errorMessage =
        typeof errorDetail === "object"
          ? JSON.stringify(errorDetail, null, 2)
          : errorDetail;
      get().setPopupError(`위험 구역 삭제 실패: ${errorMessage}`);
    }
  },

  testLotoCondition: () => {
    set({
      operationMode: "MAINTENANCE",
      personDetectedInMaintenance: true,
      lotoSensorOn: false,
    });
  },

  runtimeConfig,
}));

export default useDashboardStore;
