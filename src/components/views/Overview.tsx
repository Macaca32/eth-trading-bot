"use client";

import { useEffect, useRef } from "react";
import {
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from "recharts";
import {
  TrendingUp,
  Target,
  Activity,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
  Radio,
  Zap,
  WifiOff,
} from "lucide-react";
import { useAppStore } from "@/lib/store";
import { StatCard, ChartCard } from "@/components/ui/StatCard";
import { cn, formatEth, timeAgo } from "@/lib/utils";
import type { Signal } from "@/lib/types";

export function Overview() {
  const { positions, signals, riskMetrics, equityCurve, apiConnected } = useAppStore();
  const feedRef = useRef<HTMLDivElement>(null);

  // Auto-scroll signal feed
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = 0;
    }
  }, [signals.length]);

  const totalUnrealized = positions.reduce((sum, p) => sum + p.unrealizedPnl, 0);

  const equityData = equityCurve.map((p) => ({
    ...p,
    label: p.date.slice(5),
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-50">Dashboard Overview</h1>
          <p className="text-sm text-zinc-500 mt-1">
            Real-time trading bot performance and activity
          </p>
        </div>
        {!apiConnected ? (
          <div className="flex items-center gap-2 rounded-full bg-red-500/10 border border-red-500/20 px-3 py-1.5">
            <WifiOff className="h-3.5 w-3.5 text-red-400" />
            <span className="text-xs font-medium text-red-400">Connecting to bot...</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
            </span>
            <span className="text-xs font-medium text-emerald-400">Bot Active</span>
          </div>
        )}
      </div>

      {/* Stat Cards — trends computed from real API data */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total P&L"
          value={formatEth(riskMetrics.monthlyPnl)}
          subtitle="Last 30 days"
          icon={TrendingUp}
          {...computePnlTrend(riskMetrics.monthlyPnl, riskMetrics.weeklyPnl)}
        />
        <StatCard
          title="Win Rate"
          value={`${riskMetrics.winRate.toFixed(1)}%`}
          subtitle={riskMetrics.consecutiveWins > 0 ? `${riskMetrics.consecutiveWins} wins streak` : "No streak"}
          icon={Target}
          {...(riskMetrics.winRate > 0 ? { trend: "up" as const, trendValue: `${riskMetrics.winRate.toFixed(1)}%` } : {})}
        />
        <StatCard
          title="Sharpe Ratio"
          value={riskMetrics.sharpeRatio.toFixed(2)}
          subtitle="Risk-adjusted return"
          icon={Activity}
          {...computeSharpeTrend(riskMetrics.sharpeRatio)}
        />
        <StatCard
          title="Max Drawdown"
          value={riskMetrics.maxDrawdown > 0 ? `-${riskMetrics.maxDrawdown.toFixed(2)}%` : "0.00%"}
          subtitle={`Current: ${riskMetrics.currentDrawdown > 0 ? `-${riskMetrics.currentDrawdown.toFixed(2)}%` : "0.00%"}`}
          icon={AlertTriangle}
          {...computeDrawdownTrend(riskMetrics.maxDrawdown, riskMetrics.currentDrawdown)}
        />
      </div>

      {/* Equity Curve + Active Positions */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Equity Curve */}
        <ChartCard
          title="Equity Curve"
          subtitle="Portfolio value over time (ETH)"
          className="xl:col-span-2"
        >
          {equityData.length > 0 ? (
            <>
              <div className="h-72">
                <ResponsiveContainer width="100%" height={240} minWidth={300}>
                  <AreaChart data={equityData}>
                    <defs>
                      <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                    <XAxis
                      dataKey="label"
                      tick={{ fill: "#71717a", fontSize: 11 }}
                      axisLine={{ stroke: "#27272a" }}
                      tickLine={false}
                      interval={14}
                    />
                    <YAxis
                      tick={{ fill: "#71717a", fontSize: 11 }}
                      axisLine={{ stroke: "#27272a" }}
                      tickLine={false}
                      domain={["auto", "auto"]}
                      tickFormatter={(v) => v.toFixed(1)}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#18181b",
                        border: "1px solid #27272a",
                        borderRadius: "8px",
                        color: "#fafafa",
                        fontSize: "12px",
                      }}
                      formatter={(value) => [`${Number(value).toFixed(4)} ETH`, "Equity"]}
                    />
                    <Area
                      type="monotone"
                      dataKey="equity"
                      stroke="#10b981"
                      strokeWidth={2}
                      fill="url(#equityGradient)"
                    />
                    <Line
                      type="monotone"
                      dataKey="benchmark"
                      stroke="#71717a"
                      strokeWidth={1}
                      strokeDasharray="4 4"
                      dot={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-3 flex items-center gap-4 text-xs text-zinc-500">
                <div className="flex items-center gap-1.5">
                  <div className="h-0.5 w-4 rounded bg-emerald-500" />
                  <span>Portfolio</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="h-0.5 w-4 rounded bg-zinc-600 border-dashed" />
                  <span>Benchmark (Buy & Hold)</span>
                </div>
              </div>
            </>
          ) : (
            <div className="h-72 flex items-center justify-center text-zinc-500 text-sm">
              {apiConnected ? "No equity data available yet" : "Waiting for bot connection..."}
            </div>
          )}
        </ChartCard>

        {/* Active Positions */}
        <ChartCard
          title="Active Positions"
          subtitle={`${positions.length} open · ${formatEth(totalUnrealized)} unrealized`}
        >
          <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
            {positions.length === 0 ? (
              <div className="flex items-center justify-center h-48 text-zinc-500 text-sm">
                {apiConnected ? "No positions yet" : "Waiting for bot connection..."}
              </div>
            ) : (
              positions.map((pos) => (
                <div
                  key={pos.id}
                  className="rounded-lg border border-zinc-800 bg-zinc-850 p-3 hover:border-zinc-700 transition-colors"
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-zinc-100">
                        {pos.pair}
                      </span>
                      <span
                        className={cn(
                          "rounded px-1.5 py-0.5 text-[10px] font-bold uppercase",
                          pos.side === "long"
                            ? "bg-emerald-500/15 text-emerald-400"
                            : "bg-red-500/15 text-red-400"
                        )}
                      >
                        {pos.side}
                      </span>
                    </div>
                    <span
                      className={cn(
                        "text-sm font-semibold",
                        pos.unrealizedPnl >= 0 ? "text-emerald-400" : "text-red-400"
                      )}
                    >
                      {formatEth(pos.unrealizedPnl)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-zinc-500">
                    <span>
                      Entry: {pos.entryPrice.toFixed(2)} → {pos.currentPrice.toFixed(2)}
                    </span>
                    <span
                      className={cn(
                        pos.unrealizedPnlPercent >= 0 ? "text-emerald-500" : "text-red-500"
                      )}
                    >
                      {pos.unrealizedPnlPercent >= 0 ? "+" : ""}
                      {pos.unrealizedPnlPercent.toFixed(2)}%
                    </span>
                  </div>
                  <div className="mt-1.5 text-[10px] text-zinc-600">
                    {pos.strategy} · {timeAgo(pos.entryDate)}
                  </div>
                </div>
              ))
            )}
          </div>
        </ChartCard>
      </div>

      {/* Live Signal Feed */}
      <ChartCard
        title="Live Signal Feed"
        subtitle="Real-time bot signals"
        action={
          <div className="flex items-center gap-1.5 text-xs text-emerald-500">
            <Radio className="h-3 w-3" />
            <span>Live</span>
          </div>
        }
      >
        <div ref={feedRef} className="max-h-64 overflow-y-auto space-y-2 pr-1">
          {signals.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-zinc-500 text-sm">
              {apiConnected ? "Waiting for signals..." : "Waiting for bot connection..."}
            </div>
          ) : (
            signals.map((signal: Signal) => (
              <SignalItem key={signal.id} signal={signal} />
            ))
          )}
        </div>
      </ChartCard>
    </div>
  );
}

// --- Trend computation helpers (derived from real API data) ---

function computePnlTrend(monthlyPnl: number, weeklyPnl: number) {
  if (monthlyPnl === 0 && weeklyPnl === 0) return {};
  if (weeklyPnl > 0) return { trend: "up" as const, trendValue: `+${weeklyPnl.toFixed(4)} this week` };
  if (weeklyPnl < 0) return { trend: "down" as const, trendValue: `${weeklyPnl.toFixed(4)} this week` };
  return { trend: "neutral" as const, trendValue: "Flat this week" };
}

function computeSharpeTrend(sharpeRatio: number) {
  if (sharpeRatio === 0) return {};
  if (sharpeRatio >= 2) return { trend: "up" as const, trendValue: "Excellent" };
  if (sharpeRatio >= 1) return { trend: "up" as const, trendValue: "Good" };
  if (sharpeRatio >= 0.5) return { trend: "neutral" as const, trendValue: "Moderate" };
  return { trend: "down" as const, trendValue: "Low" };
}

function computeDrawdownTrend(maxDrawdown: number, currentDrawdown: number) {
  if (maxDrawdown === 0 && currentDrawdown === 0) return {};
  if (maxDrawdown > 0 && currentDrawdown > 0) {
    const pctOfMax = (currentDrawdown / maxDrawdown) * 100;
    if (pctOfMax < 30) return { trend: "neutral" as const, trendValue: "Recovering" };
    return { trend: "down" as const, trendValue: `${pctOfMax.toFixed(0)}% of max` };
  }
  if (maxDrawdown > 0 && currentDrawdown === 0) return { trend: "neutral" as const, trendValue: "Recovered" };
  return {};
}

function SignalItem({ signal }: { signal: Signal }) {
  const isBuy = signal.type === "buy";
  const isSell = signal.type === "sell";
  const isClose = signal.type === "close";

  return (
    <div className="flex items-start gap-3 rounded-lg border border-zinc-800/50 bg-zinc-900/50 p-3 hover:bg-zinc-800/30 transition-colors">
      <div
        className={cn(
          "mt-0.5 rounded-lg p-1.5",
          isBuy && "bg-emerald-500/15",
          isSell && "bg-red-500/15",
          isClose && "bg-amber-500/15"
        )}
      >
        <Zap
          className={cn(
            "h-3.5 w-3.5",
            isBuy && "text-emerald-400",
            isSell && "text-red-400",
            isClose && "text-amber-400"
          )}
        />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-semibold text-zinc-100">
            {signal.pair}
          </span>
          <span
            className={cn(
              "rounded px-1.5 py-0.5 text-[10px] font-bold uppercase",
              isBuy && "bg-emerald-500/15 text-emerald-400",
              isSell && "bg-red-500/15 text-red-400",
              isClose && "bg-amber-500/15 text-amber-400"
            )}
          >
            {signal.type}
          </span>
          <span className="text-xs text-zinc-500">{signal.strategy}</span>
        </div>
        <p className="text-xs text-zinc-400 leading-relaxed">{signal.reason}</p>
        <div className="mt-1.5 flex items-center gap-3 text-[10px] text-zinc-600">
          <span className="inline-flex items-center gap-1">
            {isBuy && <ArrowUpRight className="h-3 w-3" />}
            {isSell && <ArrowDownRight className="h-3 w-3" />}
            {!isBuy && !isSell && <span className="text-xs">x</span>}
            {" "}${signal.price.toLocaleString()}
          </span>
          <span>Confidence: {signal.confidence}%</span>
          <span>{timeAgo(signal.timestamp)}</span>
        </div>
      </div>
    </div>
  );
}
