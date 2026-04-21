/**
 * API client for the ETH Trading Bot backend (port 3003).
 */

const API_BASE = "http://localhost:3003";

async function apiFetch<T>(endpoint: string): Promise<T> {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      signal: AbortSignal.timeout(8000),
    });
    if (!res.ok) throw new Error(`API ${res.status}`);
    return await res.json();
  } catch {
    return [] as unknown as T;
  }
}

async function apiPost(endpoint: string, body: unknown) {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(5000),
    });
    return await res.json();
  } catch {
    return { success: false, error: "API unreachable" };
  }
}

export const botApi = {
  getStatus: () => apiFetch<{ status: string; mode: string; connected: boolean; uptime: string; version: string }>("/api/status"),
  getBalance: () => apiFetch<{ total_equity: number; available_balance: number; margin_used: number; unrealized_pnl: number }>("/api/balance"),
  getPositions: () => apiFetch<ApiPosition[]>("/api/positions"),
  getTrades: () => apiFetch<ApiTrade[]>("/api/trades"),
  getSignals: () => apiFetch<ApiSignal[]>("/api/signals"),
  getStrategies: () => apiFetch<ApiStrategy[]>("/api/strategies"),
  getRisk: () => apiFetch<ApiRisk>("/api/risk"),
  getPairs: () => apiFetch<ApiPair[]>("/api/pairs"),
  getOptimizations: () => apiFetch<ApiOptimization[]>("/api/optimizations"),
  getEquity: () => apiFetch<ApiEquityPoint[]>("/api/equity"),
  getDailyPnl: () => apiFetch<ApiDailyPnl[]>("/api/daily-pnl"),

  toggleStrategy: (strategyId: string, enabled: boolean) =>
    apiPost("/api/strategies/toggle", { strategy_id: strategyId, enabled }),
  updateParam: (strategyId: string, paramName: string, value: number) =>
    apiPost("/api/strategies/param", { strategy_id: strategyId, param_name: paramName, value }),
  setMode: (mode: string) =>
    apiPost("/api/mode", { mode }),
  updateRisk: (settings: { daily_loss_limit?: number; max_positions?: number; max_exposure?: number }) =>
    apiPost("/api/risk", settings),
  startOptimization: () =>
    apiPost("/api/optimizations/start", {}),
};

// API response types (raw from backend)
export interface ApiPosition {
  id: string;
  pair: string;
  side: string;
  strategy: string;
  entry_price: number;
  current_price: number;
  quantity: number;
  unrealized_pnl: number;
  unrealized_pnl_percent: number;
  leverage: number;
  entry_date: string;
  stop_loss: number;
  take_profit: number;
}

export interface ApiTrade {
  id: string;
  pair: string;
  side: string;
  strategy: string;
  entry_price: number;
  exit_price?: number;
  quantity: number;
  pnl: number;
  pnl_percent: number;
  outcome: string;
  entry_date: string;
  exit_date?: string;
  status: string;
  fees: number;
}

export interface ApiSignal {
  id: string;
  pair: string;
  type: string;
  strategy: string;
  price: number;
  confidence: number;
  timestamp: string;
  reason: string;
}

export interface ApiStrategyParam {
  name: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit: string;
}

export interface ApiStrategy {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  winRate: number;
  totalTrades: number;
  avgProfit: number;
  totalPnl: number;
  timeframe: string;
  params: ApiStrategyParam[];
}

export interface ApiRisk {
  totalExposure: number;
  maxExposure: number;
  dailyPnl: number;
  weeklyPnl: number;
  monthlyPnl: number;
  sharpeRatio: number;
  sortinoRatio: number;
  maxDrawdown: number;
  currentDrawdown: number;
  winRate: number;
  profitFactor: number;
  avgWin: number;
  avgLoss: number;
  consecutiveWins: number;
  consecutiveLosses: number;
  circuitBreakerActive: boolean;
  circuitBreakerLevel: number;
  dailyLossLimit: number;
  maxPositions: number;
  usedPositions: number;
}

export interface ApiPair {
  symbol: string;
  baseAsset: string;
  quoteAsset: string;
  price: number;
  change24h: number;
  volume24h: number;
  trendScore: number;
  riskScore: number;
  spread: number;
  isBlacklisted: boolean;
  lastSignal: string;
  signalTime: string;
}

export interface ApiOptimization {
  id: string;
  strategy: string;
  startTime: string;
  endTime: string;
  status: string;
  iterations: number;
  bestSharpe: number;
  bestParams: Record<string, number>;
  improvement: number;
}

export interface ApiEquityPoint {
  date: string;
  equity: number;
  drawdown: number;
  benchmark: number;
}

export interface ApiDailyPnl {
  date: string;
  pnl: number;
  cumulative: number;
  trades: number;
}
