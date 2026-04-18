"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";
import {
  Shield,
  AlertTriangle,
  Activity,
  TrendingDown,
  Flame,
  Gauge,
  Lock,
  CheckCircle2,
} from "lucide-react";
import { useAppStore } from "@/lib/store";
import { mockDailyPnl } from "@/lib/mock-data";
import { ChartCard } from "@/components/ui/StatCard";
import { cn, formatEth } from "@/lib/utils";

export function RiskMonitor() {
  const { riskMetrics, pairRiskAllocations } = useAppStore();
  const exposurePercent = (riskMetrics.totalExposure / riskMetrics.maxExposure) * 100;

  const dailyPnlData = mockDailyPnl.map((d) => ({
    ...d,
    label: d.date.slice(5),
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-50">Risk Monitor</h1>
          <p className="text-sm text-zinc-500 mt-1">
            Portfolio risk metrics and circuit breaker status
          </p>
        </div>
        <div className="flex items-center gap-2">
          {riskMetrics.circuitBreakerActive ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-red-500/10 border border-red-500/20 px-3 py-1.5 text-xs font-medium text-red-400">
              <Flame className="h-3.5 w-3.5" />
              Circuit Breaker Active
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 text-xs font-medium text-emerald-400">
              <CheckCircle2 className="h-3.5 w-3.5" />
              All Systems Normal
            </span>
          )}
        </div>
      </div>

      {/* Key Risk Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-3">
          <div className="flex items-center gap-2 mb-1">
            <Gauge className="h-3.5 w-3.5 text-emerald-400" />
            <span className="text-[10px] font-medium uppercase text-zinc-500">
              Sharpe Ratio
            </span>
          </div>
          <p className="text-lg font-bold text-emerald-400">
            {riskMetrics.sharpeRatio.toFixed(2)}
          </p>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-3">
          <div className="flex items-center gap-2 mb-1">
            <Activity className="h-3.5 w-3.5 text-zinc-400" />
            <span className="text-[10px] font-medium uppercase text-zinc-500">
              Sortino Ratio
            </span>
          </div>
          <p className="text-lg font-bold text-zinc-100">
            {riskMetrics.sortinoRatio.toFixed(2)}
          </p>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-3">
          <div className="flex items-center gap-2 mb-1">
            <TrendingDown className="h-3.5 w-3.5 text-red-400" />
            <span className="text-[10px] font-medium uppercase text-zinc-500">
              Max Drawdown
            </span>
          </div>
          <p className="text-lg font-bold text-red-400">
            -{riskMetrics.maxDrawdown.toFixed(2)}%
          </p>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-3">
          <div className="flex items-center gap-2 mb-1">
            <Shield className="h-3.5 w-3.5 text-amber-400" />
            <span className="text-[10px] font-medium uppercase text-zinc-500">
              Profit Factor
            </span>
          </div>
          <p className="text-lg font-bold text-zinc-100">
            {riskMetrics.profitFactor.toFixed(2)}
          </p>
        </div>
      </div>

      {/* Exposure + Circuit Breaker + Win/Loss Streak */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Current Exposure */}
        <ChartCard title="Current Exposure" subtitle="Total portfolio utilization">
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-zinc-400">Utilization</span>
                <span className="text-sm font-bold text-zinc-100">
                  {(riskMetrics.totalExposure * 100).toFixed(1)}% /{" "}
                  {(riskMetrics.maxExposure * 100).toFixed(0)}%
                </span>
              </div>
              <div className="h-3 bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className={cn(
                    "h-full rounded-full transition-all duration-500",
                    exposurePercent >= 80
                      ? "bg-red-500"
                      : exposurePercent >= 60
                      ? "bg-amber-500"
                      : "bg-emerald-500"
                  )}
                  style={{ width: `${Math.min(100, exposurePercent)}%` }}
                />
              </div>
            </div>

            <div className="rounded-lg bg-zinc-800/50 p-3 space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-zinc-500">Open Positions</span>
                <span className="text-zinc-200 font-medium">
                  {riskMetrics.usedPositions} / {riskMetrics.maxPositions}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-zinc-500">Daily P&L</span>
                <span
                  className={cn(
                    "font-medium",
                    riskMetrics.dailyPnl >= 0
                      ? "text-emerald-400"
                      : "text-red-400"
                  )}
                >
                  {formatEth(riskMetrics.dailyPnl)}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-zinc-500">Weekly P&L</span>
                <span
                  className={cn(
                    "font-medium",
                    riskMetrics.weeklyPnl >= 0
                      ? "text-emerald-400"
                      : "text-red-400"
                  )}
                >
                  {formatEth(riskMetrics.weeklyPnl)}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-zinc-500">Monthly P&L</span>
                <span
                  className={cn(
                    "font-medium",
                    riskMetrics.monthlyPnl >= 0
                      ? "text-emerald-400"
                      : "text-red-400"
                  )}
                >
                  {formatEth(riskMetrics.monthlyPnl)}
                </span>
              </div>
            </div>
          </div>
        </ChartCard>

        {/* Circuit Breaker */}
        <ChartCard title="Circuit Breaker" subtitle="Risk protection system">
          <div className="space-y-3">
            {/* Status */}
            <div
              className={cn(
                "rounded-lg p-4 text-center",
                riskMetrics.circuitBreakerActive
                  ? "bg-red-500/10 border border-red-500/20"
                  : "bg-emerald-500/5 border border-emerald-500/10"
              )}
            >
              {riskMetrics.circuitBreakerActive ? (
                <>
                  <AlertTriangle className="h-8 w-8 text-red-400 mx-auto mb-2" />
                  <p className="text-sm font-bold text-red-400">
                    CIRCUIT BREAKER ACTIVE
                  </p>
                  <p className="text-xs text-red-400/60 mt-1">
                    All new trades blocked until conditions improve
                  </p>
                </>
              ) : (
                <>
                  <Lock className="h-8 w-8 text-emerald-400 mx-auto mb-2" />
                  <p className="text-sm font-bold text-emerald-400">
                    SYSTEMS NORMAL
                  </p>
                  <p className="text-xs text-zinc-500 mt-1">
                    All risk parameters within limits
                  </p>
                </>
              )}
            </div>

            {/* Breaker Levels */}
            <div className="space-y-2">
              {[1, 2, 3].map((level) => {
                const lossLimit = riskMetrics.dailyLossLimit * level;
                const isActive =
                  riskMetrics.circuitBreakerActive &&
                  riskMetrics.circuitBreakerLevel >= level;
                return (
                  <div
                    key={level}
                    className={cn(
                      "flex items-center justify-between rounded-lg p-2.5 border",
                      isActive
                        ? "bg-red-500/10 border-red-500/20"
                        : level <= riskMetrics.circuitBreakerLevel
                        ? "bg-amber-500/5 border-amber-500/10"
                        : "bg-zinc-800/50 border-zinc-800"
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <div
                        className={cn(
                          "h-2 w-2 rounded-full",
                          isActive
                            ? "bg-red-500"
                            : level <= riskMetrics.circuitBreakerLevel
                            ? "bg-amber-500"
                            : "bg-zinc-600"
                        )}
                      />
                      <span className="text-xs font-medium text-zinc-300">
                        Level {level}
                      </span>
                    </div>
                    <span className="text-xs text-zinc-500">
                      Daily loss &gt; {lossLimit} ETH
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Loss Limits */}
            <div className="rounded-lg bg-zinc-800/50 p-3 space-y-1.5">
              <p className="text-[10px] uppercase text-zinc-600 font-medium">
                Current Drawdown
              </p>
              <p className="text-lg font-bold text-zinc-100">
                -{riskMetrics.currentDrawdown.toFixed(2)}%
              </p>
              <p className="text-[10px] text-zinc-500">
                Max allowed: -{riskMetrics.maxDrawdown.toFixed(2)}%
              </p>
            </div>
          </div>
        </ChartCard>

        {/* Win/Loss Stats */}
        <ChartCard title="Streak Analysis" subtitle="Consecutive trade performance">
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg bg-emerald-500/5 border border-emerald-500/10 p-3 text-center">
                <p className="text-2xl font-bold text-emerald-400">
                  {riskMetrics.consecutiveWins}
                </p>
                <p className="text-[10px] uppercase text-emerald-400/60 font-medium mt-0.5">
                  Win Streak
                </p>
              </div>
              <div className="rounded-lg bg-red-500/5 border border-red-500/10 p-3 text-center">
                <p className="text-2xl font-bold text-red-400">
                  {riskMetrics.consecutiveLosses}
                </p>
                <p className="text-[10px] uppercase text-red-400/60 font-medium mt-0.5">
                  Loss Streak
                </p>
              </div>
            </div>

            <div className="rounded-lg bg-zinc-800/50 p-3 space-y-2.5">
              <div className="flex justify-between text-xs">
                <span className="text-zinc-500">Win Rate</span>
                <span className="text-zinc-200 font-medium">
                  {riskMetrics.winRate}%
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-zinc-500">Avg Win</span>
                <span className="text-emerald-400 font-medium">
                  {formatEth(riskMetrics.avgWin)}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-zinc-500">Avg Loss</span>
                <span className="text-red-400 font-medium">
                  {formatEth(riskMetrics.avgLoss)}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-zinc-500">Profit Factor</span>
                <span className="text-zinc-200 font-medium">
                  {riskMetrics.profitFactor.toFixed(2)}
                </span>
              </div>
            </div>
          </div>
        </ChartCard>
      </div>

      {/* Daily P&L Chart */}
      <ChartCard
        title="Daily P&L Tracker"
        subtitle="Last 30 days performance"
      >
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={dailyPnlData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
              <XAxis
                dataKey="label"
                tick={{ fill: "#71717a", fontSize: 10 }}
                axisLine={{ stroke: "#27272a" }}
                tickLine={false}
                interval={4}
              />
              <YAxis
                tick={{ fill: "#71717a", fontSize: 11 }}
                axisLine={{ stroke: "#27272a" }}
                tickLine={false}
                tickFormatter={(v) => `${v >= 0 ? "+" : ""}${v.toFixed(2)}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#18181b",
                  border: "1px solid #27272a",
                  borderRadius: "8px",
                  color: "#fafafa",
                  fontSize: "12px",
                }}
                formatter={(value, name) => {
                  if (name === "pnl")
                    return [
                      `${Number(value) >= 0 ? "+" : ""}${Number(value).toFixed(4)} ETH`,
                      "Daily P&L",
                    ];
                  return [value, name];
                }}
              />
              <ReferenceLine y={0} stroke="#3f3f46" />
              <Bar dataKey="pnl" radius={[2, 2, 0, 0]} barSize={8}>
                {dailyPnlData.map((entry, index) => (
                  <Cell
                    key={index}
                    fill={entry.pnl >= 0 ? "#10b981" : "#ef4444"}
                    opacity={0.8}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>

      {/* Per-Pair Risk Allocation */}
      <ChartCard
        title="Per-Pair Risk Allocation"
        subtitle="Risk budget distribution across pairs"
      >
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800">
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Pair
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Allocation
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Used
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Max Loss
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Usage
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {pairRiskAllocations.map((alloc) => {
                const usagePercent = (alloc.used / alloc.allocated) * 100;
                return (
                  <tr
                    key={alloc.pair}
                    className="hover:bg-zinc-800/30 transition-colors"
                  >
                    <td className="px-4 py-3 font-medium text-zinc-200">
                      {alloc.pair}
                    </td>
                    <td className="px-4 py-3 text-zinc-400">
                      {alloc.allocated}%
                    </td>
                    <td className="px-4 py-3 text-zinc-300">
                      {alloc.used}%
                    </td>
                    <td className="px-4 py-3 text-amber-400">
                      {alloc.maxLoss} ETH
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-24 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                          <div
                            className={cn(
                              "h-full rounded-full",
                              usagePercent >= 80
                                ? "bg-red-500"
                                : usagePercent >= 60
                                ? "bg-amber-500"
                                : "bg-emerald-500"
                            )}
                            style={{ width: `${usagePercent}%` }}
                          />
                        </div>
                        <span className="text-xs text-zinc-500">
                          {usagePercent.toFixed(0)}%
                        </span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </ChartCard>
    </div>
  );
}
