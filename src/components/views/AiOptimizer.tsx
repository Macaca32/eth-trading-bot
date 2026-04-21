"use client";

import { useState, useEffect, useCallback } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import {
  Brain,
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowUpRight,
  Loader2,
  Sparkles,
} from "lucide-react";
import { useAppStore } from "@/lib/store";
import { botApi } from "@/lib/api";
import type { OptimizationRun } from "@/lib/types";
import { ChartCard } from "@/components/ui/StatCard";
import { cn, formatDateTime } from "@/lib/utils";

const paramImportance = [
  { name: "ST Multiplier", importance: 28.5 },
  { name: "RSI Period", importance: 22.1 },
  { name: "Stop Loss %", importance: 18.7 },
  { name: "ATR Period", importance: 14.3 },
  { name: "Take Profit %", importance: 9.2 },
  { name: "Stoch K", importance: 4.8 },
  { name: "BB StdDev", importance: 2.4 },
];

export function AiOptimizer() {
  const { optimizationRuns, apiConnected } = useAppStore();
  const [isOptimizing, setIsOptimizing] = useState(false);

  const hasRunning = optimizationRuns.some((r) => r.status === "running");

  // Sync local state with API data
  useEffect(() => {
    if (hasRunning) {
      setIsOptimizing(true);
    } else {
      setIsOptimizing(false);
    }
  }, [hasRunning]);

  const handleStartOptimization = useCallback(async () => {
    setIsOptimizing(true);
    const success = await botApi.startOptimization();
    if (!success) {
      setIsOptimizing(false);
    }
  }, []);

  const latestRun = optimizationRuns[0];
  const bestRun = optimizationRuns
    .filter((r) => r.status === "completed")
    .sort((a, b) => b.bestSharpe - a.bestSharpe)[0];

  const paramColors = ["#10b981", "#34d399", "#6ee7b7", "#a7f3d0", "#d1fae5", "#ecfdf5", "#f0fdf4"];

  const bestParams = bestRun
    ? Object.entries(bestRun.bestParams).map(([key, value]) => ({
        param: key,
        best: value,
        current: latestRun?.bestParams[key] ?? 0,
      }))
    : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-50">AI Optimizer</h1>
          <p className="text-sm text-zinc-500 mt-1">
            Machine learning-powered parameter optimization
          </p>
        </div>
        <button
          onClick={handleStartOptimization}
          disabled={isOptimizing}
          className={cn(
            "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors",
            isOptimizing
              ? "bg-zinc-700 text-zinc-400 cursor-not-allowed"
              : "bg-emerald-500 text-white hover:bg-emerald-600"
          )}
        >
          {isOptimizing ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Optimizing...
            </>
          ) : (
            <>
              <Play className="h-4 w-4" />
              Start Optimization
            </>
          )}
        </button>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="h-4 w-4 text-emerald-400" />
            <span className="text-sm font-medium text-zinc-300">
              Current Best Sharpe
            </span>
          </div>
          <p className="text-2xl font-bold text-emerald-400">
            {bestRun?.bestSharpe.toFixed(2) ?? "—"}
          </p>
          {bestRun && (
            <p className="text-xs text-zinc-500 mt-1">
              {bestRun.strategy} · {bestRun.iterations} iterations
            </p>
          )}
        </div>

        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Brain className="h-4 w-4 text-amber-400" />
            <span className="text-sm font-medium text-zinc-300">
              Total Runs
            </span>
          </div>
          <p className="text-2xl font-bold text-zinc-100">
            {optimizationRuns.length}
          </p>
          <p className="text-xs text-zinc-500 mt-1">
            {optimizationRuns.filter((r) => r.status === "completed").length}{" "}
            completed
          </p>
        </div>

        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
          <div className="flex items-center gap-2 mb-2">
            <ArrowUpRight className="h-4 w-4 text-emerald-400" />
            <span className="text-sm font-medium text-zinc-300">
              Best Improvement
            </span>
          </div>
          <p className="text-2xl font-bold text-emerald-400">
            {optimizationRuns.length > 0
              ? `+${Math.max(...optimizationRuns.map((r) => r.improvement)).toFixed(1)}%`
              : "—"}
          </p>
          <p className="text-xs text-zinc-500 mt-1">Sharpe ratio gain</p>
        </div>
      </div>

      {/* Running indicator */}
      {isOptimizing && (
        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
          <div className="flex items-center gap-3">
            <Loader2 className="h-5 w-5 animate-spin text-emerald-400" />
            <div>
              <p className="text-sm font-medium text-emerald-400">
                Optimization in Progress...
              </p>
              <p className="text-xs text-zinc-500 mt-0.5">
                The bot is running parameter optimization. Results will appear here when complete.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Parameter Importance + Best vs Current */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <ChartCard
          title="Parameter Importance"
          subtitle="Impact on Sharpe ratio"
        >
          <div className="h-64">
            <ResponsiveContainer width="100%" height={240} minWidth={300}>
              <BarChart
                data={paramImportance}
                layout="vertical"
                margin={{ left: 10 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#27272a"
                  horizontal={false}
                />
                <XAxis
                  type="number"
                  tick={{ fill: "#71717a", fontSize: 11 }}
                  axisLine={{ stroke: "#27272a" }}
                  tickLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fill: "#a1a1aa", fontSize: 11 }}
                  axisLine={{ stroke: "#27272a" }}
                  tickLine={false}
                  width={100}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#18181b",
                    border: "1px solid #27272a",
                    borderRadius: "8px",
                    color: "#fafafa",
                    fontSize: "12px",
                  }}
                  formatter={(value) => [
                    `${value}%`,
                    "Importance",
                  ]}
                />
                <Bar dataKey="importance" radius={[0, 4, 4, 0]} barSize={16}>
                  {paramImportance.map((_, index) => (
                    <Cell key={index} fill={paramColors[index % paramColors.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <ChartCard
          title="Best vs Current Parameters"
          subtitle={bestRun ? `From: ${bestRun.strategy}` : ""}
        >
          {bestParams.length > 0 ? (
            <div className="space-y-3">
              {bestParams.map((bp) => (
                <div key={bp.param} className="rounded-lg bg-zinc-800/50 p-3">
                  <p className="text-xs font-medium text-zinc-400 mb-2">
                    {bp.param}
                  </p>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <p className="text-[10px] uppercase text-zinc-600 mb-0.5">
                        Best
                      </p>
                      <p className="text-sm font-bold text-emerald-400">
                        {bp.best}
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] uppercase text-zinc-600 mb-0.5">
                        Current
                      </p>
                      <p className="text-sm font-bold text-zinc-300">
                        {bp.current || "—"}
                      </p>
                    </div>
                  </div>
                  {bp.current !== 0 && bp.best !== bp.current && (
                    <div className="mt-2 h-1 bg-zinc-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-500/50 rounded-full"
                        style={{
                          width: `${Math.min(
                            100,
                            (bp.best / Math.max(bp.best, bp.current)) * 100
                          )}%`,
                        }}
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-48 text-zinc-500 text-sm">
              No completed optimization runs yet
            </div>
          )}
        </ChartCard>
      </div>

      {/* Optimization History */}
      <ChartCard title="Optimization History" subtitle="Past optimization runs">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800">
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Strategy
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Iterations
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Best Sharpe
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Improvement
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Completed
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {optimizationRuns.length === 0 ? (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-12 text-center text-sm text-zinc-500"
                  >
                    No optimization runs yet
                  </td>
                </tr>
              ) : (
                optimizationRuns.map((run) => (
                  <tr
                    key={run.id}
                    className="hover:bg-zinc-800/30 transition-colors"
                  >
                    <td className="px-4 py-3 text-zinc-200 font-medium">
                      {run.strategy}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={run.status} />
                    </td>
                    <td className="px-4 py-3 text-zinc-400">
                      {run.iterations}
                    </td>
                    <td className="px-4 py-3 text-emerald-400 font-medium">
                      {run.bestSharpe.toFixed(2)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          "font-medium",
                          run.improvement > 0 ? "text-emerald-400" : "text-zinc-500"
                        )}
                      >
                        {run.improvement > 0
                          ? `+${run.improvement.toFixed(1)}%`
                          : "—"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-zinc-500 text-xs">
                      {run.endTime
                        ? formatDateTime(run.endTime)
                        : "In progress..."}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </ChartCard>
    </div>
  );
}

function StatusBadge({ status }: { status: OptimizationRun["status"] }) {
  switch (status) {
    case "completed":
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-400">
          <CheckCircle2 className="h-3 w-3" />
          Completed
        </span>
      );
    case "running":
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-400">
          <Loader2 className="h-3 w-3 animate-spin" />
          Running
        </span>
      );
    case "failed":
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-red-500/10 px-2 py-0.5 text-[10px] font-medium text-red-400">
          <XCircle className="h-3 w-3" />
          Failed
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-zinc-500/10 px-2 py-0.5 text-[10px] font-medium text-zinc-400">
          <Clock className="h-3 w-3" />
          Idle
        </span>
      );
  }
}
