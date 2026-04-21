"use client";

import { useState, useCallback } from "react";
import {
  Settings2,
  ChevronDown,
  ChevronUp,
  Zap,
} from "lucide-react";
import { useAppStore } from "@/lib/store";
import { botApi } from "@/lib/api";
import { cn, formatEth } from "@/lib/utils";
import type { Strategy } from "@/lib/types";

export function Strategies() {
  const { strategies, toggleStrategy, updateStrategyParam } = useAppStore();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const enabledCount = strategies.filter((s) => s.enabled).length;

  const handleToggleEnabled = useCallback(
    async (id: string, currentEnabled: boolean) => {
      // Optimistic update
      toggleStrategy(id);
      // Send to API
      await botApi.toggleStrategy(id, !currentEnabled);
    },
    [toggleStrategy]
  );

  const handleUpdateParam = useCallback(
    async (strategyId: string, paramName: string, value: number) => {
      // Optimistic update
      updateStrategyParam(strategyId, paramName, value);
      // Send to API
      await botApi.updateParam(strategyId, paramName, value);
    },
    [updateStrategyParam]
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-50">Strategies</h1>
          <p className="text-sm text-zinc-500 mt-1">
            {enabledCount} of {strategies.length} strategies active
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-full bg-zinc-800 px-3 py-1.5">
          <Zap className="h-3.5 w-3.5 text-emerald-400" />
          <span className="text-xs font-medium text-zinc-300">
            {strategies.reduce((s, st) => s + st.totalTrades, 0)} total trades
          </span>
        </div>
      </div>

      {/* Strategy Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {strategies.length === 0 ? (
          <div className="col-span-full flex items-center justify-center h-48 text-zinc-500 text-sm rounded-xl border border-zinc-800 bg-zinc-900/60">
            No strategies configured
          </div>
        ) : (
          strategies.map((strategy) => (
            <StrategyCard
              key={strategy.id}
              strategy={strategy}
              isExpanded={expandedId === strategy.id}
              onToggleExpand={() =>
                setExpandedId(expandedId === strategy.id ? null : strategy.id)
              }
              onToggleEnabled={() => handleToggleEnabled(strategy.id, strategy.enabled)}
              onUpdateParam={(name, value) =>
                handleUpdateParam(strategy.id, name, value)
              }
            />
          ))
        )}
      </div>
    </div>
  );
}

function StrategyCard({
  strategy,
  isExpanded,
  onToggleExpand,
  onToggleEnabled,
  onUpdateParam,
}: {
  strategy: Strategy;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onToggleEnabled: () => void;
  onUpdateParam: (name: string, value: number) => void;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border transition-all duration-200",
        strategy.enabled
          ? "border-emerald-500/30 bg-zinc-900"
          : "border-zinc-800 bg-zinc-900/60"
      )}
    >
      {/* Card Header */}
      <div className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <Settings2
                className={cn(
                  "h-4 w-4",
                  strategy.enabled ? "text-emerald-400" : "text-zinc-600"
                )}
              />
              <h3 className="text-sm font-bold text-zinc-100">
                {strategy.name}
              </h3>
              <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] font-medium text-zinc-500">
                {strategy.timeframe}
              </span>
            </div>
            <p className="text-xs text-zinc-500 leading-relaxed line-clamp-2">
              {strategy.description}
            </p>
          </div>

          {/* Toggle Switch */}
          <button
            onClick={onToggleEnabled}
            className={cn(
              "relative ml-4 inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full transition-colors",
              strategy.enabled ? "bg-emerald-500" : "bg-zinc-700"
            )}
          >
            <span
              className={cn(
                "pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform",
                strategy.enabled ? "translate-x-6" : "translate-x-1"
              )}
            />
          </button>
        </div>

        {/* Key Stats */}
        <div className="grid grid-cols-3 gap-3 mb-3">
          <div className="rounded-lg bg-zinc-800/50 px-3 py-2">
            <p className="text-[10px] font-medium text-zinc-500 uppercase">
              Win Rate
            </p>
            <p className="text-sm font-bold text-zinc-100 mt-0.5">
              {strategy.winRate}%
            </p>
          </div>
          <div className="rounded-lg bg-zinc-800/50 px-3 py-2">
            <p className="text-[10px] font-medium text-zinc-500 uppercase">
              Total Trades
            </p>
            <p className="text-sm font-bold text-zinc-100 mt-0.5">
              {strategy.totalTrades}
            </p>
          </div>
          <div className="rounded-lg bg-zinc-800/50 px-3 py-2">
            <p className="text-[10px] font-medium text-zinc-500 uppercase">
              Total P&L
            </p>
            <p
              className={cn(
                "text-sm font-bold mt-0.5",
                strategy.totalPnl >= 0 ? "text-emerald-400" : "text-red-400"
              )}
            >
              {formatEth(strategy.totalPnl)}
            </p>
          </div>
        </div>

        {/* Mini bar for avg profit */}
        <div className="flex items-center gap-2 text-xs">
          <span className="text-zinc-500">Avg Profit:</span>
          <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full bg-emerald-500/70"
              style={{
                width: `${Math.min(
                  100,
                  Math.abs(strategy.avgProfit) * 100
                )}%`,
              }}
            />
          </div>
          <span className="text-zinc-300 font-medium">
            {strategy.avgProfit > 0 ? "+" : ""}
            {strategy.avgProfit.toFixed(4)} ETH
          </span>
        </div>

        {/* Expand/Collapse Button */}
        <button
          onClick={onToggleExpand}
          className="mt-3 flex w-full items-center justify-center gap-1 rounded-lg bg-zinc-800/50 py-2 text-xs text-zinc-400 hover:bg-zinc-800 hover:text-zinc-300 transition-colors"
        >
          {isExpanded ? (
            <>
              <ChevronUp className="h-3.5 w-3.5" />
              Hide Parameters
            </>
          ) : (
            <>
              <ChevronDown className="h-3.5 w-3.5" />
              Show Parameters ({strategy.params.length})
            </>
          )}
        </button>
      </div>

      {/* Expanded Parameters */}
      {isExpanded && (
        <div className="border-t border-zinc-800 p-4 space-y-4 bg-zinc-950/30 rounded-b-xl">
          {strategy.params.map((param) => (
            <div key={param.name}>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-medium text-zinc-300">
                  {param.name}
                </label>
                <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded">
                  {param.value}
                  {param.unit}
                </span>
              </div>
              <input
                type="range"
                min={param.min}
                max={param.max}
                step={param.step}
                value={param.value}
                onChange={(e) =>
                  onUpdateParam(param.name, parseFloat(e.target.value))
                }
                className="w-full h-1.5 bg-zinc-800 rounded-full appearance-none cursor-pointer
                  [&::-webkit-slider-thumb]:appearance-none
                  [&::-webkit-slider-thumb]:h-3.5
                  [&::-webkit-slider-thumb]:w-3.5
                  [&::-webkit-slider-thumb]:rounded-full
                  [&::-webkit-slider-thumb]:bg-emerald-500
                  [&::-webkit-slider-thumb]:shadow-lg
                  [&::-webkit-slider-thumb]:shadow-emerald-500/30
                  [&::-moz-range-thumb]:h-3.5
                  [&::-moz-range-thumb]:w-3.5
                  [&::-moz-range-thumb]:rounded-full
                  [&::-moz-range-thumb]:bg-emerald-500
                  [&::-moz-range-thumb]:border-0"
                disabled={!strategy.enabled}
              />
              <div className="flex justify-between text-[10px] text-zinc-600 mt-0.5">
                <span>
                  {param.min}
                  {param.unit}
                </span>
                <span>
                  {param.max}
                  {param.unit}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
