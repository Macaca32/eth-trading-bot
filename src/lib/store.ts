import { create } from "zustand";
import type {
  TradingMode,
  Strategy,
  Trade,
  Position,
  TradingPair,
  EquityPoint,
  Signal,
  RiskMetrics,
  PairRiskAllocation,
  OptimizationRun,
  DailyPnl,
  NotificationSettings,
} from "./types";
import {
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

const emptyRiskMetrics: RiskMetrics = {
  totalExposure: 0,
  maxExposure: 0.5,
  dailyPnl: 0,
  weeklyPnl: 0,
  monthlyPnl: 0,
  sharpeRatio: 0,
  sortinoRatio: 0,
  maxDrawdown: 0,
  currentDrawdown: 0,
  winRate: 0,
  profitFactor: 0,
  avgWin: 0,
  avgLoss: 0,
  consecutiveWins: 0,
  consecutiveLosses: 0,
  circuitBreakerActive: false,
  circuitBreakerLevel: 0,
  dailyLossLimit: 7.0,
  maxPositions: 5,
  usedPositions: 0,
};

interface AppState {
  // Navigation
  activeView: ViewName;
  sidebarOpen: boolean;

  // Trading
  tradingMode: TradingMode;
  apiConnected: boolean;

  // Data (populated from API, empty by default)
  equityCurve: EquityPoint[];
  dailyPnl: DailyPnl[];
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

  // Internal setters (used by useBotApi to replace data from API)
  _setPositions: (positions: Position[]) => void;
  _setTrades: (trades: Trade[]) => void;
  _setSignals: (signals: Signal[]) => void;
  _setStrategies: (strategies: Strategy[]) => void;
  _setRiskMetrics: (metrics: RiskMetrics) => void;
  _setPairs: (pairs: TradingPair[]) => void;
  _setOptimizations: (runs: OptimizationRun[]) => void;
  _setEquityCurve: (curve: EquityPoint[]) => void;
  _setDailyPnl: (pnl: DailyPnl[]) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Navigation
  activeView: "overview",
  sidebarOpen: false,

  // Trading
  tradingMode: "paper",
  apiConnected: false,

  // Data — empty by default, populated from API
  equityCurve: [],
  dailyPnl: [],
  strategies: [],
  trades: [],
  positions: [],
  pairs: [],
  signals: [],
  riskMetrics: emptyRiskMetrics,
  pairRiskAllocations: [],
  optimizationRuns: [],
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

  // Internal setters — called by useBotApi hook
  _setPositions: (positions) => set({ positions }),
  _setTrades: (trades) => set({ trades }),
  _setSignals: (signals) => set({ signals }),
  _setStrategies: (strategies) => set({ strategies }),
  _setRiskMetrics: (metrics) => set({ riskMetrics: metrics }),
  _setPairs: (pairs) => set({ pairs }),
  _setOptimizations: (runs) => set({ optimizationRuns: runs }),
  _setEquityCurve: (curve) => set({ equityCurve: curve }),
  _setDailyPnl: (pnl) => set({ dailyPnl: pnl }),
}));
