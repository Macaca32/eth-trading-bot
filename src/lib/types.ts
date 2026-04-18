export type TradingMode = "paper" | "live";
export type TradeSide = "long" | "short";
export type TradeOutcome = "win" | "loss" | "breakeven";
export type SignalType = "buy" | "sell" | "close";
export type OptimizationStatus = "idle" | "running" | "completed" | "failed";

export interface Strategy {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  winRate: number;
  totalTrades: number;
  avgProfit: number;
  totalPnl: number;
  params: StrategyParam[];
  timeframe: string;
}

export interface StrategyParam {
  name: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit: string;
}

export interface Trade {
  id: string;
  pair: string;
  side: TradeSide;
  strategy: string;
  entryPrice: number;
  exitPrice: number;
  quantity: number;
  pnl: number;
  pnlPercent: number;
  outcome: TradeOutcome;
  entryDate: string;
  exitDate: string;
  duration: string;
  fees: number;
}

export interface Position {
  id: string;
  pair: string;
  side: TradeSide;
  strategy: string;
  entryPrice: number;
  currentPrice: number;
  quantity: number;
  unrealizedPnl: number;
  unrealizedPnlPercent: number;
  leverage: number;
  entryDate: string;
  stopLoss: number;
  takeProfit: number;
}

export interface TradingPair {
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
  lastSignal: SignalType;
  signalTime: string;
}

export interface EquityPoint {
  date: string;
  equity: number;
  drawdown: number;
  benchmark: number;
}

export interface Signal {
  id: string;
  pair: string;
  type: SignalType;
  strategy: string;
  price: number;
  confidence: number;
  timestamp: string;
  reason: string;
}

export interface RiskMetrics {
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

export interface PairRiskAllocation {
  pair: string;
  allocated: number;
  used: number;
  maxLoss: number;
  currentLoss: number;
}

export interface OptimizationRun {
  id: string;
  strategy: string;
  startTime: string;
  endTime: string | null;
  status: OptimizationStatus;
  iterations: number;
  bestSharpe: number;
  bestParams: Record<string, number>;
  improvement: number;
}

export interface DailyPnl {
  date: string;
  pnl: number;
  cumulative: number;
  trades: number;
}

export interface NotificationSettings {
  tradeExecuted: boolean;
  tradeClosed: boolean;
  strategyAlert: boolean;
  riskAlert: boolean;
  dailyReport: boolean;
  weeklyReport: boolean;
  telegramEnabled: boolean;
  emailEnabled: boolean;
}
