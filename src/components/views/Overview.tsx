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
} from "lucide-react";
import { useAppStore } from "@/lib/store";
import { mockEquityCurve, generateSignal } from "@/lib/mock-data";
import { StatCard, ChartCard } from "@/components/ui/StatCard";
import { cn, formatEth, timeAgo } from "@/lib/utils";
import type { Signal } from "@/lib/types";

export function Overview() {
  const { positions, signals, addSignal, riskMetrics } = useAppStore();
  const feedRef = useRef<HTMLDivElement>(null);

  // Auto-update signals every 8 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      const newSignal = generateSignal();
      addSignal(newSignal);
    }, 8000);
    return () => clearInterval(interval);
  }, [addSignal]);

  // Auto-scroll signal feed
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = 0;
    }
  }, [signals.length]);

  const totalUnrealized = positions.reduce((sum, p) => sum + p.unrealizedPnl, 0);

  const equityData = mockEquityCurve.map((p) => ({
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
        <div className="flex items-center gap-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
          </span>
          <span className="text-xs font-medium text-emerald-400">Bot Active</span>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total P&L"
          value={formatEth(riskMetrics.monthlyPnl)}
          subtitle="Last 30 days"
          icon={TrendingUp}
          trend="up"
          trendValue="+12.4%"
        />
        <StatCard
          title="Win Rate"
          value={`${riskMetrics.winRate.toFixed(1)}%`}
          subtitle={`${riskMetrics.consecutiveWins} wins streak`}
          icon={Target}
          trend="up"
          trendValue="+2.1%"
        />
        <StatCard
          title="Sharpe Ratio"
          value={riskMetrics.sharpeRatio.toFixed(2)}
          subtitle="Risk-adjusted return"
          icon={Activity}
          trend="up"
          trendValue="+0.18"
        />
        <StatCard
          title="Max Drawdown"
          value={`-${riskMetrics.maxDrawdown.toFixed(2)}%`}
          subtitle="Current: -{riskMetrics.currentDrawdown.toFixed(2)}%"
          icon={AlertTriangle}
          trend="down"
          trendValue="Controlling"
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
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
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
        </ChartCard>

        {/* Active Positions */}
        <ChartCard
          title="Active Positions"
          subtitle={`${positions.length} open · ${formatEth(totalUnrealized)} unrealized`}
        >
          <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
            {positions.map((pos) => (
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
            ))}
          </div>
        </ChartCard>
      </div>

      {/* Live Signal Feed */}
      <ChartCard
        title="Live Signal Feed"
        subtitle="Auto-updating every 8s"
        action={
          <div className="flex items-center gap-1.5 text-xs text-emerald-500">
            <Radio className="h-3 w-3" />
            <span>Live</span>
          </div>
        }
      >
        <div ref={feedRef} className="max-h-64 overflow-y-auto space-y-2 pr-1">
          {signals.map((signal: Signal) => (
            <SignalItem key={signal.id} signal={signal} />
          ))}
        </div>
      </ChartCard>
    </div>
  );
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
