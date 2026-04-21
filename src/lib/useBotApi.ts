"use client";

import { useEffect, useRef } from "react";
import { useAppStore } from "./store";
import { botApi, type ApiPosition, type ApiTrade, type ApiSignal, type ApiStrategy, type ApiRisk, type ApiPair, type ApiOptimization, type ApiEquityPoint, type ApiDailyPnl } from "./api";
import type { Position, Trade, Signal, Strategy, TradingPair, EquityPoint, DailyPnl, OptimizationRun, RiskMetrics } from "./types";

function mapPosition(p: ApiPosition): Position {
  return {
    id: p.id,
    pair: p.pair,
    side: p.side as "long" | "short",
    strategy: p.strategy || "Unknown",
    entryPrice: p.entry_price,
    currentPrice: p.current_price,
    quantity: p.quantity,
    unrealizedPnl: p.unrealized_pnl,
    unrealizedPnlPercent: p.unrealized_pnl_percent,
    leverage: p.leverage,
    entryDate: p.entry_date,
    stopLoss: p.stop_loss,
    takeProfit: p.take_profit,
  };
}

function mapTrade(t: ApiTrade): Trade {
  // Compute human-readable duration from entry/exit dates
  let duration = "";
  if (t.entry_date && t.exit_date) {
    const entryMs = new Date(t.entry_date).getTime();
    const exitMs = new Date(t.exit_date).getTime();
    const diffMin = Math.max(0, Math.floor((exitMs - entryMs) / 60000));
    if (diffMin < 60) {
      duration = `${diffMin}m`;
    } else if (diffMin < 1440) {
      duration = `${Math.floor(diffMin / 60)}h ${diffMin % 60}m`;
    } else {
      duration = `${Math.floor(diffMin / 1440)}d ${Math.floor((diffMin % 1440) / 60)}h`;
    }
  }

  return {
    id: t.id,
    pair: t.pair,
    side: t.side as "long" | "short",
    strategy: t.strategy,
    entryPrice: t.entry_price,
    exitPrice: t.exit_price ?? t.entry_price,
    quantity: t.quantity,
    pnl: t.pnl,
    pnlPercent: t.pnl_percent,
    outcome: t.outcome as "win" | "loss" | "breakeven",
    entryDate: t.entry_date,
    exitDate: t.exit_date ?? "",
    duration,
    fees: t.fees,
  };
}

function mapSignal(s: ApiSignal): Signal {
  return {
    id: s.id,
    pair: s.pair,
    type: s.type as "buy" | "sell" | "close",
    strategy: s.strategy,
    price: s.price,
    confidence: s.confidence,
    timestamp: s.timestamp,
    reason: s.reason,
  };
}

function mapStrategy(s: ApiStrategy): Strategy {
  return {
    id: s.id,
    name: s.name,
    description: s.description,
    enabled: s.enabled,
    winRate: s.winRate,
    totalTrades: s.totalTrades,
    avgProfit: s.avgProfit,
    totalPnl: s.totalPnl,
    timeframe: s.timeframe,
    params: s.params.map((p) => ({
      name: p.name,
      value: p.value,
      min: p.min,
      max: p.max,
      step: p.step,
      unit: p.unit,
    })),
  };
}

function mapRisk(r: ApiRisk): RiskMetrics {
  return {
    totalExposure: r.totalExposure,
    maxExposure: r.maxExposure,
    dailyPnl: r.dailyPnl,
    weeklyPnl: r.weeklyPnl,
    monthlyPnl: r.monthlyPnl,
    sharpeRatio: r.sharpeRatio,
    sortinoRatio: r.sortinoRatio,
    maxDrawdown: r.maxDrawdown,
    currentDrawdown: r.currentDrawdown,
    winRate: r.winRate,
    profitFactor: r.profitFactor,
    avgWin: r.avgWin,
    avgLoss: r.avgLoss,
    consecutiveWins: r.consecutiveWins,
    consecutiveLosses: r.consecutiveLosses,
    circuitBreakerActive: r.circuitBreakerActive,
    circuitBreakerLevel: r.circuitBreakerLevel,
    dailyLossLimit: r.dailyLossLimit,
    maxPositions: r.maxPositions,
    usedPositions: r.usedPositions,
  };
}

function mapPair(p: ApiPair): TradingPair {
  return {
    symbol: p.symbol,
    baseAsset: p.baseAsset,
    quoteAsset: p.quoteAsset,
    price: p.price,
    change24h: p.change24h,
    volume24h: p.volume24h,
    trendScore: p.trendScore,
    riskScore: p.riskScore,
    spread: p.spread,
    isBlacklisted: p.isBlacklisted,
    lastSignal: (p.lastSignal || "none") as "buy" | "sell" | "close",
    signalTime: p.signalTime,
  };
}

function mapOptimization(o: ApiOptimization): OptimizationRun {
  return {
    id: o.id,
    strategy: o.strategy,
    startTime: o.startTime,
    endTime: o.endTime,
    status: o.status as "idle" | "running" | "completed" | "failed",
    iterations: o.iterations,
    bestSharpe: o.bestSharpe,
    bestParams: o.bestParams,
    improvement: o.improvement,
  };
}

/**
 * Fetch all data from the Bot API and update the Zustand store.
 *
 * Uses useAppStore.getState() instead of useAppStore() to avoid
 * subscribing to store changes — this prevents the infinite re-render
 * loop that was causing CPU spikes and rapid API polling.
 */
async function fetchAllData() {
  const store = useAppStore.getState();

  try {
    // Fetch status first to check connection
    const status = await botApi.getStatus();
    if (status && "status" in status && (status as Record<string, unknown>).status !== undefined) {
      store.setApiConnected(true);
      if ("mode" in status) {
        store.setTradingMode((status as { mode: "paper" | "live" }).mode);
      }
    }
  } catch {
    store.setApiConnected(false);
  }

  // Fetch all data in parallel
  const [positions, trades, signals, strategies, risk, pairs, optimizations, equity, dailyPnl] = await Promise.all([
    botApi.getPositions(),
    botApi.getTrades(),
    botApi.getSignals(),
    botApi.getStrategies(),
    botApi.getRisk(),
    botApi.getPairs(),
    botApi.getOptimizations(),
    botApi.getEquity(),
    botApi.getDailyPnl(),
  ]);

  // Update store with real data (only if we got valid data back)
  if (Array.isArray(positions) && positions.length > 0) {
    store._setPositions((positions as ApiPosition[]).map(mapPosition));
  } else if (Array.isArray(positions) && positions.length === 0) {
    store._setPositions([]);
  }

  if (Array.isArray(trades) && trades.length > 0) {
    store._setTrades((trades as ApiTrade[]).map(mapTrade));
  } else if (Array.isArray(trades) && trades.length === 0) {
    store._setTrades([]);
  }

  if (Array.isArray(signals) && signals.length > 0) {
    store._setSignals((signals as ApiSignal[]).map(mapSignal));
  } else if (Array.isArray(signals) && signals.length === 0) {
    store._setSignals([]);
  }

  if (Array.isArray(strategies) && strategies.length > 0) {
    store._setStrategies((strategies as ApiStrategy[]).map(mapStrategy));
  }

  if (risk && typeof risk === "object" && "dailyPnl" in (risk as object)) {
    store._setRiskMetrics(mapRisk(risk as ApiRisk));
  }

  if (Array.isArray(pairs) && pairs.length > 0) {
    store._setPairs((pairs as ApiPair[]).map(mapPair));
  } else if (Array.isArray(pairs) && pairs.length === 0) {
    store._setPairs([]);
  }

  if (Array.isArray(optimizations) && optimizations.length > 0) {
    store._setOptimizations((optimizations as ApiOptimization[]).map(mapOptimization));
  } else if (Array.isArray(optimizations) && optimizations.length === 0) {
    store._setOptimizations([]);
  }

  if (Array.isArray(equity) && equity.length > 0) {
    store._setEquityCurve((equity as ApiEquityPoint[]).map((e: ApiEquityPoint) => ({
      date: e.date,
      equity: e.equity,
      drawdown: e.drawdown,
      benchmark: e.benchmark,
    })));
  } else if (Array.isArray(equity) && equity.length === 0) {
    store._setEquityCurve([]);
  }

  if (Array.isArray(dailyPnl) && dailyPnl.length > 0) {
    store._setDailyPnl((dailyPnl as ApiDailyPnl[]).map((d: ApiDailyPnl) => ({
      date: d.date,
      pnl: d.pnl,
      cumulative: d.cumulative,
      trades: d.trades,
    })));
  } else if (Array.isArray(dailyPnl) && dailyPnl.length === 0) {
    store._setDailyPnl([]);
  }
}

export function useBotApi() {
  const wsRef = useRef<WebSocket | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  // Subscribe only to apiConnected for the return value (stable selector)
  const apiConnected = useAppStore((s) => s.apiConnected);

  useEffect(() => {
    mountedRef.current = true;

    // Initial fetch
    fetchAllData();

    // Poll every 10 seconds — stable reference, no re-render loop
    pollRef.current = setInterval(fetchAllData, 10000);

    // WebSocket for real-time updates
    const store = useAppStore.getState();
    try {
      const ws = new WebSocket("ws://localhost:3003/ws");
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        store.setApiConnected(true);
        ws.send(JSON.stringify({ type: "subscribe", channels: ["trades", "signals", "positions"] }));
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "trades" && Array.isArray(msg.data)) {
            store._setTrades(msg.data.map(mapTrade));
          } else if (msg.type === "signals" && Array.isArray(msg.data)) {
            store._setSignals(msg.data.map(mapSignal));
          } else if (msg.type === "positions" && Array.isArray(msg.data)) {
            store._setPositions(msg.data.map(mapPosition));
          }
        } catch {
          // Ignore parse errors
        }
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        store.setApiConnected(false);
        // Reconnect after 5 seconds
        setTimeout(() => {
          if (!mountedRef.current) return;
          if (wsRef.current === ws) {
            const newWs = new WebSocket("ws://localhost:3003/ws");
            wsRef.current = newWs;
            newWs.onopen = ws.onopen;
            newWs.onmessage = ws.onmessage;
            newWs.onclose = ws.onclose;
          }
        }, 5000);
      };
    } catch {
      // WebSocket not available — polling will handle updates
    }

    return () => {
      mountedRef.current = false;
      if (pollRef.current) clearInterval(pollRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null; // Prevent reconnect
        wsRef.current.close();
      }
    };
  }, []); // Empty deps — runs ONCE on mount, never recreates

  return { fetchAll: fetchAllData, refetch: fetchAllData, apiConnected };
}
