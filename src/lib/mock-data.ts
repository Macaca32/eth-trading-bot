import type {
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

// ─── Strategies ────────────────────────────────────────────────────────
export const mockStrategies: Strategy[] = [
  {
    id: "strat-1",
    name: "StochRSI + Supertrend",
    description: "Combines Stochastic RSI for overbought/oversold signals with Supertrend for trend direction filtering. Works best on 15m-1h timeframes.",
    enabled: true,
    winRate: 62.4,
    totalTrades: 156,
    avgProfit: 0.0234,
    totalPnl: 3.6508,
    timeframe: "15m",
    params: [
      { name: "RSI Period", value: 14, min: 2, max: 50, step: 1, unit: "" },
      { name: "Stoch K", value: 14, min: 2, max: 30, step: 1, unit: "" },
      { name: "Stoch D", value: 3, min: 1, max: 10, step: 1, unit: "" },
      { name: "Overbought", value: 80, min: 70, max: 95, step: 1, unit: "" },
      { name: "Oversold", value: 20, min: 5, max: 30, step: 1, unit: "" },
      { name: "ATR Period", value: 10, min: 5, max: 30, step: 1, unit: "" },
      { name: "ST Multiplier", value: 3.0, min: 1.0, max: 6.0, step: 0.1, unit: "x" },
      { name: "Stop Loss %", value: 1.5, min: 0.5, max: 5.0, step: 0.1, unit: "%" },
      { name: "Take Profit %", value: 3.0, min: 1.0, max: 10.0, step: 0.1, unit: "%" },
    ],
  },
  {
    id: "strat-2",
    name: "MACD + BB + RSI",
    description: "Triple confirmation strategy using MACD crossovers within Bollinger Bands with RSI divergence filter. High confidence, lower frequency signals.",
    enabled: true,
    winRate: 58.7,
    totalTrades: 98,
    avgProfit: 0.0312,
    totalPnl: 3.0576,
    timeframe: "1h",
    params: [
      { name: "MACD Fast", value: 12, min: 5, max: 20, step: 1, unit: "" },
      { name: "MACD Slow", value: 26, min: 15, max: 50, step: 1, unit: "" },
      { name: "MACD Signal", value: 9, min: 3, max: 15, step: 1, unit: "" },
      { name: "BB Period", value: 20, min: 10, max: 40, step: 1, unit: "" },
      { name: "BB StdDev", value: 2.0, min: 1.0, max: 3.5, step: 0.1, unit: "" },
      { name: "RSI Period", value: 14, min: 5, max: 30, step: 1, unit: "" },
      { name: "RSI Threshold", value: 50, min: 30, max: 70, step: 1, unit: "" },
      { name: "Stop Loss %", value: 2.0, min: 0.5, max: 5.0, step: 0.1, unit: "%" },
      { name: "Take Profit %", value: 4.0, min: 1.0, max: 12.0, step: 0.1, unit: "%" },
    ],
  },
  {
    id: "strat-3",
    name: "BB Winner PRO",
    description: "Mean reversion strategy trading Bollinger Band touches and squeezes with volume confirmation. Excels in ranging markets.",
    enabled: false,
    winRate: 55.2,
    totalTrades: 203,
    avgProfit: 0.0156,
    totalPnl: 3.1668,
    timeframe: "5m",
    params: [
      { name: "BB Period", value: 20, min: 10, max: 40, step: 1, unit: "" },
      { name: "BB StdDev", value: 2.0, min: 1.5, max: 3.5, step: 0.1, unit: "" },
      { name: "Squeeze Threshold", value: 0.5, min: 0.2, max: 1.5, step: 0.1, unit: "" },
      { name: "Volume MA", value: 20, min: 5, max: 50, step: 1, unit: "" },
      { name: "Vol Multiplier", value: 1.5, min: 1.0, max: 3.0, step: 0.1, unit: "x" },
      { name: "Min Band Width", value: 0.8, min: 0.3, max: 2.0, step: 0.1, unit: "%" },
      { name: "Stop Loss %", value: 1.0, min: 0.3, max: 3.0, step: 0.1, unit: "%" },
      { name: "Take Profit %", value: 1.8, min: 0.5, max: 5.0, step: 0.1, unit: "%" },
    ],
  },
  {
    id: "strat-4",
    name: "Supertrend + RSI",
    description: "Trend-following strategy using Supertrend for directional bias and RSI for entry timing. Adaptive position sizing based on ATR.",
    enabled: true,
    winRate: 60.1,
    totalTrades: 74,
    avgProfit: 0.0421,
    totalPnl: 3.1154,
    timeframe: "4h",
    params: [
      { name: "ATR Period", value: 12, min: 5, max: 30, step: 1, unit: "" },
      { name: "ST Multiplier", value: 2.5, min: 1.0, max: 6.0, step: 0.1, unit: "x" },
      { name: "RSI Period", value: 14, min: 5, max: 30, step: 1, unit: "" },
      { name: "RSI Overbought", value: 70, min: 60, max: 85, step: 1, unit: "" },
      { name: "RSI Oversold", value: 30, min: 15, max: 40, step: 1, unit: "" },
      { name: "Position Size ATR", value: 1.0, min: 0.5, max: 3.0, step: 0.1, unit: "x" },
      { name: "Trailing Stop %", value: 1.5, min: 0.5, max: 4.0, step: 0.1, unit: "%" },
      { name: "Max Position %", value: 5.0, min: 1.0, max: 15.0, step: 0.5, unit: "%" },
    ],
  },
];

// ─── Historical Trades (50) ───────────────────────────────────────────
const pairs = ["ETH/USDT", "ETH/BTC", "ETH/USDC", "ETH/DAI", "ETH/WBTC"];
const strategyNames = ["StochRSI+Supertrend", "MACD+BB+RSI", "BB Winner PRO", "Supertrend+RSI"];
const sides: ("long" | "short")[] = ["long", "short"];

function randomBetween(min: number, max: number): number {
  return min + Math.random() * (max - min);
}

function generateTrades(): Trade[] {
  const trades: Trade[] = [];
  const now = Date.now();

  for (let i = 0; i < 50; i++) {
    const pair = pairs[Math.floor(Math.random() * pairs.length)];
    const strategy = strategyNames[Math.floor(Math.random() * strategyNames.length)];
    const side = sides[Math.floor(Math.random() * sides.length)];
    const basePrice = pair.includes("BTC") ? randomBetween(0.04, 0.08) : randomBetween(2800, 4200);
    const isWin = Math.random() < 0.58;
    const pnlPercent = isWin ? randomBetween(0.3, 8.5) : -randomBetween(0.2, 4.2);
    const entryDate = new Date(now - randomBetween(1 * 60 * 60 * 1000, 30 * 24 * 60 * 60 * 1000));
    const durationMin = randomBetween(5, 1440);
    const exitDate = new Date(entryDate.getTime() + durationMin * 60 * 1000);
    const quantity = randomBetween(0.01, 2.5);
    const entryPrice = basePrice;
    const exitPrice = side === "long"
      ? entryPrice * (1 + pnlPercent / 100)
      : entryPrice * (1 - pnlPercent / 100);
    const pnl = side === "long"
      ? (exitPrice - entryPrice) * quantity
      : (entryPrice - exitPrice) * quantity;

    const duration =
      durationMin < 60 ? `${Math.floor(durationMin)}m` :
      durationMin < 1440 ? `${Math.floor(durationMin / 60)}h ${Math.floor(durationMin % 60)}m` :
      `${Math.floor(durationMin / 1440)}d ${Math.floor((durationMin % 1440) / 60)}h`;

    trades.push({
      id: `trade-${i + 1}`,
      pair,
      side,
      strategy,
      entryPrice: parseFloat(entryPrice.toFixed(2)),
      exitPrice: parseFloat(exitPrice.toFixed(2)),
      quantity: parseFloat(quantity.toFixed(4)),
      pnl: parseFloat(pnl.toFixed(4)),
      pnlPercent: parseFloat(pnlPercent.toFixed(2)),
      outcome: pnlPercent > 0.05 ? "win" : pnlPercent < -0.05 ? "loss" : "breakeven",
      entryDate: entryDate.toISOString(),
      exitDate: exitDate.toISOString(),
      duration,
      fees: parseFloat((Math.abs(pnl) * 0.001).toFixed(6)),
    });
  }

  return trades.sort((a, b) => new Date(b.exitDate).getTime() - new Date(a.exitDate).getTime());
}

export const mockTrades: Trade[] = generateTrades();

// ─── Active Positions (5) ─────────────────────────────────────────────
export const mockPositions: Position[] = [
  {
    id: "pos-1",
    pair: "ETH/USDT",
    side: "long",
    strategy: "StochRSI+Supertrend",
    entryPrice: 3521.45,
    currentPrice: 3567.82,
    quantity: 0.85,
    unrealizedPnl: 0.0394,
    unrealizedPnlPercent: 1.32,
    leverage: 1,
    entryDate: new Date(Date.now() - 2.5 * 60 * 60 * 1000).toISOString(),
    stopLoss: 3478.0,
    takeProfit: 3620.0,
  },
  {
    id: "pos-2",
    pair: "ETH/BTC",
    side: "long",
    strategy: "Supertrend+RSI",
    entryPrice: 0.0612,
    currentPrice: 0.0634,
    quantity: 12.5,
    unrealizedPnl: 0.0275,
    unrealizedPnlPercent: 3.60,
    leverage: 1,
    entryDate: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    stopLoss: 0.0598,
    takeProfit: 0.0655,
  },
  {
    id: "pos-3",
    pair: "ETH/USDC",
    side: "short",
    strategy: "MACD+BB+RSI",
    entryPrice: 3645.20,
    currentPrice: 3612.85,
    quantity: 0.62,
    unrealizedPnl: 0.0200,
    unrealizedPnlPercent: 0.89,
    leverage: 1,
    entryDate: new Date(Date.now() - 1.2 * 60 * 60 * 1000).toISOString(),
    stopLoss: 3680.0,
    takeProfit: 3580.0,
  },
  {
    id: "pos-4",
    pair: "ETH/USDT",
    side: "long",
    strategy: "BB Winner PRO",
    entryPrice: 3489.10,
    currentPrice: 3567.82,
    quantity: 0.45,
    unrealizedPnl: 0.0355,
    unrealizedPnlPercent: 2.26,
    leverage: 1,
    entryDate: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(),
    stopLoss: 3455.0,
    takeProfit: 3570.0,
  },
  {
    id: "pos-5",
    pair: "ETH/DAI",
    side: "short",
    strategy: "StochRSI+Supertrend",
    entryPrice: 3601.55,
    currentPrice: 3563.20,
    quantity: 0.78,
    unrealizedPnl: 0.0299,
    unrealizedPnlPercent: 1.07,
    leverage: 1,
    entryDate: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
    stopLoss: 3645.0,
    takeProfit: 3520.0,
  },
];

// ─── Trading Pairs (10) ───────────────────────────────────────────────
export const mockPairs: TradingPair[] = [
  {
    symbol: "ETH/USDT",
    baseAsset: "ETH",
    quoteAsset: "USDT",
    price: 3567.82,
    change24h: 2.34,
    volume24h: 1845200000,
    trendScore: 82,
    riskScore: 35,
    spread: 0.012,
    isBlacklisted: false,
    lastSignal: "buy",
    signalTime: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
  },
  {
    symbol: "ETH/BTC",
    baseAsset: "ETH",
    quoteAsset: "BTC",
    price: 0.0634,
    change24h: 1.12,
    volume24h: 456000000,
    trendScore: 71,
    riskScore: 42,
    spread: 0.018,
    isBlacklisted: false,
    lastSignal: "buy",
    signalTime: new Date(Date.now() - 32 * 60 * 1000).toISOString(),
  },
  {
    symbol: "ETH/USDC",
    baseAsset: "ETH",
    quoteAsset: "USDC",
    price: 3568.15,
    change24h: 2.28,
    volume24h: 987000000,
    trendScore: 80,
    riskScore: 33,
    spread: 0.010,
    isBlacklisted: false,
    lastSignal: "buy",
    signalTime: new Date(Date.now() - 8 * 60 * 1000).toISOString(),
  },
  {
    symbol: "ETH/DAI",
    baseAsset: "ETH",
    quoteAsset: "DAI",
    price: 3563.20,
    change24h: 2.15,
    volume24h: 234000000,
    trendScore: 76,
    riskScore: 38,
    spread: 0.015,
    isBlacklisted: false,
    lastSignal: "sell",
    signalTime: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
  },
  {
    symbol: "ETH/WBTC",
    baseAsset: "ETH",
    quoteAsset: "WBTC",
    price: 0.0633,
    change24h: 0.95,
    volume24h: 178000000,
    trendScore: 65,
    riskScore: 48,
    spread: 0.022,
    isBlacklisted: false,
    lastSignal: "buy",
    signalTime: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
  },
  {
    symbol: "ETH/BNB",
    baseAsset: "ETH",
    quoteAsset: "BNB",
    price: 6.82,
    change24h: -0.45,
    volume24h: 89000000,
    trendScore: 48,
    riskScore: 62,
    spread: 0.035,
    isBlacklisted: false,
    lastSignal: "sell",
    signalTime: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
  },
  {
    symbol: "ETH/ARB",
    baseAsset: "ETH",
    quoteAsset: "ARB",
    price: 3245.6,
    change24h: 3.12,
    volume24h: 67000000,
    trendScore: 85,
    riskScore: 55,
    spread: 0.042,
    isBlacklisted: true,
    lastSignal: "buy",
    signalTime: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
  },
  {
    symbol: "ETH/OP",
    baseAsset: "ETH",
    quoteAsset: "OP",
    price: 5621.3,
    change24h: -1.23,
    volume24h: 42000000,
    trendScore: 42,
    riskScore: 70,
    spread: 0.058,
    isBlacklisted: false,
    lastSignal: "sell",
    signalTime: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
  },
  {
    symbol: "ETH/MATIC",
    baseAsset: "ETH",
    quoteAsset: "MATIC",
    price: 2156.7,
    change24h: 1.87,
    volume24h: 55000000,
    trendScore: 68,
    riskScore: 52,
    spread: 0.048,
    isBlacklisted: false,
    lastSignal: "buy",
    signalTime: new Date(Date.now() - 90 * 60 * 1000).toISOString(),
  },
  {
    symbol: "ETH/LINK",
    baseAsset: "ETH",
    quoteAsset: "LINK",
    price: 42.85,
    change24h: 4.56,
    volume24h: 38000000,
    trendScore: 78,
    riskScore: 45,
    spread: 0.052,
    isBlacklisted: false,
    lastSignal: "buy",
    signalTime: new Date(Date.now() - 20 * 60 * 1000).toISOString(),
  },
];

// ─── Equity Curve (100 data points) ──────────────────────────────────
export function generateEquityCurve(): EquityPoint[] {
  const points: EquityPoint[] = [];
  let equity = 10.0; // Start at 10 ETH
  const now = Date.now();

  for (let i = 0; i < 100; i++) {
    const date = new Date(now - (100 - i) * 6 * 60 * 60 * 1000);
    const change = (Math.random() - 0.42) * 0.15;
    equity = Math.max(5, equity + change);
    const benchmark = 10.0 * (1 + i * 0.0025 + (Math.random() - 0.5) * 0.02);
    const peak = Math.max(...points.map(p => p.equity), equity);
    const drawdown = ((peak - equity) / peak) * 100;

    points.push({
      date: date.toISOString().split("T")[0],
      equity: parseFloat(equity.toFixed(4)),
      drawdown: parseFloat(drawdown.toFixed(2)),
      benchmark: parseFloat(benchmark.toFixed(4)),
    });
  }

  return points;
}

export const mockEquityCurve: EquityPoint[] = generateEquityCurve();

// ─── Live Signals ─────────────────────────────────────────────────────
export const signalReasons = [
  "StochRSI crossed above 20 in oversold zone, Supertrend flipped bullish",
  "MACD bullish crossover above signal line within lower Bollinger Band",
  "Price touched lower BB with RSI divergence confirmed by volume spike",
  "Supertrend buy signal confirmed by RSI recovering from oversold (28)",
  "MACD histogram turning positive with BB squeeze breakout imminent",
  "StochRSI overbought cross below 80 with bearish Supertrend flip",
  "Price rejected upper BB at RSI 75 with declining volume confirmation",
  "Supertrend sell signal with RSI bearish divergence on 1h timeframe",
  "BB width expanding with price breaking above upper band on volume",
  "StochRSI oversold bounce with Supertrend support holding at key level",
];

export function generateSignal(): Signal {
  return {
    id: `sig-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    pair: pairs[Math.floor(Math.random() * pairs.length)],
    type: (["buy", "sell", "close"] as const)[Math.floor(Math.random() * 3)],
    strategy: strategyNames[Math.floor(Math.random() * strategyNames.length)],
    price: parseFloat(randomBetween(3400, 3700).toFixed(2)),
    confidence: parseFloat(randomBetween(60, 98).toFixed(1)),
    timestamp: new Date().toISOString(),
    reason: signalReasons[Math.floor(Math.random() * signalReasons.length)],
  };
}

export const mockInitialSignals: Signal[] = Array.from({ length: 8 }, () => {
  const signal = generateSignal();
  signal.timestamp = new Date(Date.now() - Math.random() * 3600000).toISOString();
  return signal;
}).sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

// ─── Risk Metrics ─────────────────────────────────────────────────────
export const mockRiskMetrics: RiskMetrics = {
  totalExposure: 0.342,
  maxExposure: 0.80,
  dailyPnl: 0.1523,
  weeklyPnl: 0.8934,
  monthlyPnl: 3.6508,
  sharpeRatio: 2.34,
  sortinoRatio: 3.12,
  maxDrawdown: 8.45,
  currentDrawdown: 1.23,
  winRate: 58.4,
  profitFactor: 1.87,
  avgWin: 0.0523,
  avgLoss: -0.0281,
  consecutiveWins: 5,
  consecutiveLosses: 2,
  circuitBreakerActive: false,
  circuitBreakerLevel: 1,
  dailyLossLimit: 1.0,
  maxPositions: 8,
  usedPositions: 5,
};

// ─── Pair Risk Allocations ────────────────────────────────────────────
export const mockPairRiskAllocations: PairRiskAllocation[] = [
  { pair: "ETH/USDT", allocated: 25, used: 18.5, maxLoss: 0.25, currentLoss: 0.0 },
  { pair: "ETH/BTC", allocated: 20, used: 12.3, maxLoss: 0.20, currentLoss: 0.0 },
  { pair: "ETH/USDC", allocated: 20, used: 8.7, maxLoss: 0.20, currentLoss: 0.0 },
  { pair: "ETH/DAI", allocated: 15, used: 10.2, maxLoss: 0.15, currentLoss: 0.0 },
  { pair: "ETH/WBTC", allocated: 10, used: 0, maxLoss: 0.10, currentLoss: 0.0 },
  { pair: "ETH/BNB", allocated: 5, used: 0, maxLoss: 0.05, currentLoss: 0.0 },
  { pair: "ETH/LINK", allocated: 5, used: 0, maxLoss: 0.05, currentLoss: 0.0 },
];

// ─── Optimization Runs ────────────────────────────────────────────────
export const mockOptimizationRuns: OptimizationRun[] = [
  {
    id: "opt-1",
    strategy: "StochRSI + Supertrend",
    startTime: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    endTime: new Date(Date.now() - 1.5 * 60 * 60 * 1000).toISOString(),
    status: "completed",
    iterations: 500,
    bestSharpe: 2.67,
    bestParams: { "RSI Period": 12, "Stoch K": 14, "ST Multiplier": 2.8, "Stop Loss %": 1.3 },
    improvement: 14.1,
  },
  {
    id: "opt-2",
    strategy: "MACD + BB + RSI",
    startTime: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
    endTime: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    status: "completed",
    iterations: 750,
    bestSharpe: 2.45,
    bestParams: { "MACD Fast": 10, "MACD Slow": 24, "BB StdDev": 2.2, "Take Profit %": 3.5 },
    improvement: 8.3,
  },
  {
    id: "opt-3",
    strategy: "Supertrend + RSI",
    startTime: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    endTime: new Date(Date.now() - 22 * 60 * 60 * 1000).toISOString(),
    status: "completed",
    iterations: 1000,
    bestSharpe: 2.89,
    bestParams: { "ATR Period": 10, "ST Multiplier": 2.3, "Trailing Stop %": 1.2 },
    improvement: 21.5,
  },
  {
    id: "opt-4",
    strategy: "StochRSI + Supertrend",
    startTime: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString(),
    endTime: new Date(Date.now() - 46 * 60 * 60 * 1000).toISOString(),
    status: "failed",
    iterations: 120,
    bestSharpe: 1.89,
    bestParams: {},
    improvement: 0,
  },
  {
    id: "opt-5",
    strategy: "BB Winner PRO",
    startTime: new Date(Date.now() - 72 * 60 * 60 * 1000).toISOString(),
    endTime: new Date(Date.now() - 70 * 60 * 60 * 1000).toISOString(),
    status: "completed",
    iterations: 600,
    bestSharpe: 1.95,
    bestParams: { "BB Period": 18, "BB StdDev": 2.1, "Vol Multiplier": 1.8 },
    improvement: 12.7,
  },
];

// ─── Daily P&L Tracker (30 days) ──────────────────────────────────────
export function generateDailyPnl(): DailyPnl[] {
  const days: DailyPnl[] = [];
  let cumulative = 0;
  const now = Date.now();

  for (let i = 29; i >= 0; i--) {
    const date = new Date(now - i * 24 * 60 * 60 * 1000);
    const pnl = parseFloat(((Math.random() - 0.38) * 0.5).toFixed(4));
    cumulative += pnl;
    days.push({
      date: date.toISOString().split("T")[0],
      pnl,
      cumulative: parseFloat(cumulative.toFixed(4)),
      trades: Math.floor(randomBetween(1, 12)),
    });
  }

  return days;
}

export const mockDailyPnl: DailyPnl[] = generateDailyPnl();

// ─── Parameter Importance Data ────────────────────────────────────────
export const mockParamImportance = [
  { name: "ST Multiplier", importance: 28.5 },
  { name: "RSI Period", importance: 22.1 },
  { name: "Stop Loss %", importance: 18.7 },
  { name: "ATR Period", importance: 14.3 },
  { name: "Take Profit %", importance: 9.2 },
  { name: "Stoch K", importance: 4.8 },
  { name: "BB StdDev", importance: 2.4 },
];

// ─── Notification Settings ────────────────────────────────────────────
export const mockNotificationSettings: NotificationSettings = {
  tradeExecuted: true,
  tradeClosed: true,
  strategyAlert: true,
  riskAlert: true,
  dailyReport: true,
  weeklyReport: false,
  telegramEnabled: true,
  emailEnabled: false,
};
