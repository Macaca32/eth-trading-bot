import { create } from "zustand";
import type {
  TradingMode,
  Strategy,
  Trade,
  Position,
  TradingPair,
  Signal,
  RiskMetrics,
  PairRiskAllocation,
  OptimizationRun,
  NotificationSettings,
} from "./types";
import {
  mockStrategies,
  mockTrades,
  mockPositions,
  mockPairs,
  mockInitialSignals,
  mockRiskMetrics,
  mockPairRiskAllocations,
  mockOptimizationRuns,
  mockNotificationSettings,
} from "./mock-data";

export type ViewName =
  | "tutorial"
  | "overview"
  | "strategies"
  | "ai-optimizer"
  | "pair-screener"
  | "trade-log"
  | "risk-monitor"
  | "settings";

interface AppState {
  // Navigation
  activeView: ViewName;
  sidebarOpen: boolean;

  // Trading
  tradingMode: TradingMode;
  apiConnected: boolean;

  // Data
  strategies: Strategy[];
  trades: Trade[];
  positions: Position[];
  pairs: TradingPair[];
  signals: Signal[];
  riskMetrics: RiskMetrics;
  pairRiskAllocations: PairRiskAllocation[];
  optimizationRuns: OptimizationRun[];
  notifications: NotificationSettings;

  // Settings
  dailyLossLimit: number;
  maxPositions: number;
  maxExposure: number;

  // Actions
  setActiveView: (view: ViewName) => void;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setTradingMode: (mode: TradingMode) => void;
  setApiConnected: (connected: boolean) => void;
  toggleStrategy: (id: string) => void;
  updateStrategyParam: (strategyId: string, paramName: string, value: number) => void;
  addSignal: (signal: Signal) => void;
  removeSignal: (id: string) => void;
  togglePairBlacklist: (symbol: string) => void;
  setDailyLossLimit: (limit: number) => void;
  setMaxPositions: (max: number) => void;
  setMaxExposure: (max: number) => void;
  updateNotification: (key: keyof NotificationSettings, value: boolean) => void;
  updateRiskMetrics: (metrics: Partial<RiskMetrics>) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Navigation
  activeView: "overview",
  sidebarOpen: false,

  // Trading
  tradingMode: "paper",
  apiConnected: true,

  // Data
  strategies: mockStrategies,
  trades: mockTrades,
  positions: mockPositions,
  pairs: mockPairs,
  signals: mockInitialSignals,
  riskMetrics: mockRiskMetrics,
  pairRiskAllocations: mockPairRiskAllocations,
  optimizationRuns: mockOptimizationRuns,
  notifications: mockNotificationSettings,

  // Settings
  dailyLossLimit: 1.0,
  maxPositions: 8,
  maxExposure: 0.8,

  // Actions
  setActiveView: (view) =>
    set({ activeView: view, sidebarOpen: false }),

  setSidebarOpen: (open) =>
    set({ sidebarOpen: open }),

  toggleSidebar: () =>
    set((s) => ({ sidebarOpen: !s.sidebarOpen })),

  setTradingMode: (mode) =>
    set({ tradingMode: mode }),

  setApiConnected: (connected) =>
    set({ apiConnected: connected }),

  toggleStrategy: (id) =>
    set((s) => ({
      strategies: s.strategies.map((st) =>
        st.id === id ? { ...st, enabled: !st.enabled } : st
      ),
    })),

  updateStrategyParam: (strategyId, paramName, value) =>
    set((s) => ({
      strategies: s.strategies.map((st) =>
        st.id === strategyId
          ? {
              ...st,
              params: st.params.map((p) =>
                p.name === paramName ? { ...p, value } : p
              ),
            }
          : st
      ),
    })),

  addSignal: (signal) =>
    set((s) => ({
      signals: [signal, ...s.signals].slice(0, 20),
    })),

  removeSignal: (id) =>
    set((s) => ({
      signals: s.signals.filter((sig) => sig.id !== id),
    })),

  togglePairBlacklist: (symbol) =>
    set((s) => ({
      pairs: s.pairs.map((p) =>
        p.symbol === symbol ? { ...p, isBlacklisted: !p.isBlacklisted } : p
      ),
    })),

  setDailyLossLimit: (limit) =>
    set({ dailyLossLimit: limit }),

  setMaxPositions: (max) =>
    set({ maxPositions: max }),

  setMaxExposure: (max) =>
    set({ maxExposure: max }),

  updateNotification: (key, value) =>
    set((s) => ({
      notifications: { ...s.notifications, [key]: value },
    })),

  updateRiskMetrics: (metrics) =>
    set((s) => ({
      riskMetrics: { ...s.riskMetrics, ...metrics },
    })),
}));
