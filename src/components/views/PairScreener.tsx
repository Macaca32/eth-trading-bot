"use client";

import { useState } from "react";
import {
  RefreshCw,
  Ban,
  ArrowUpRight,
  ArrowDownRight,
  Eye,
  EyeOff,
  Search,
} from "lucide-react";
import { useAppStore } from "@/lib/store";
import { cn, formatUsd, timeAgo } from "@/lib/utils";
import type { TradingPair } from "@/lib/types";

export function PairScreener() {
  const { pairs } = useAppStore();
  const [searchQuery, setSearchQuery] = useState("");
  const [showBlacklisted, setShowBlacklisted] = useState(false);

  const filteredPairs = pairs.filter((p) => {
    const matchesSearch =
      p.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.quoteAsset.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = showBlacklisted || !p.isBlacklisted;
    return matchesSearch && matchesFilter;
  });

  const sortedPairs = [...filteredPairs].sort((a, b) => b.trendScore - a.trendScore);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-50">Pair Screener</h1>
          <p className="text-sm text-zinc-500 mt-1">
            {pairs.filter((p) => !p.isBlacklisted).length} active pairs ·{" "}
            {pairs.filter((p) => p.isBlacklisted).length} blacklisted
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
          <input
            type="text"
            placeholder="Search pairs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-zinc-800 bg-zinc-900 pl-10 pr-4 py-2 text-sm text-zinc-200 placeholder-zinc-600 outline-none focus:border-zinc-700 transition-colors"
          />
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowBlacklisted(!showBlacklisted)}
            className={cn(
              "flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium transition-colors",
              showBlacklisted
                ? "border-amber-500/30 bg-amber-500/10 text-amber-400"
                : "border-zinc-800 bg-zinc-900 text-zinc-400 hover:bg-zinc-800"
            )}
          >
            {showBlacklisted ? (
              <Eye className="h-3.5 w-3.5" />
            ) : (
              <EyeOff className="h-3.5 w-3.5" />
            )}
            {showBlacklisted ? "Showing All" : "Hide Blacklisted"}
          </button>
        </div>
      </div>

      {/* Pairs Table */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 bg-zinc-950/50">
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Pair
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Price
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  24h Change
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Volume
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Trend
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Risk
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Spread
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Signal
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {sortedPairs.length === 0 ? (
                <tr>
                  <td
                    colSpan={8}
                    className="px-4 py-12 text-center text-sm text-zinc-500"
                  >
                    {pairs.length === 0
                      ? "No pairs available yet"
                      : "No pairs match the search criteria"}
                  </td>
                </tr>
              ) : (
                sortedPairs.map((pair) => (
                  <PairRow key={pair.symbol} pair={pair} />
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Score Legend */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
        <h3 className="text-xs font-semibold text-zinc-400 mb-3 uppercase tracking-wider">
          Score Guide
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-zinc-500 mb-2">Trend Score</p>
            <div className="flex items-center gap-1">
              {[0, 1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="h-3 flex-1 rounded-sm"
                  style={{
                    backgroundColor:
                      i < 1
                        ? "#ef4444"
                        : i < 2
                        ? "#f97316"
                        : i < 3
                        ? "#eab308"
                        : i < 4
                        ? "#22c55e"
                        : "#10b981",
                  }}
                />
              ))}
              <div className="flex justify-between w-full mt-0.5">
                <span className="text-[10px] text-zinc-600">0 Bearish</span>
                <span className="text-[10px] text-zinc-600">100 Bullish</span>
              </div>
            </div>
          </div>
          <div>
            <p className="text-xs text-zinc-500 mb-2">Risk Score</p>
            <div className="flex items-center gap-1">
              {[0, 1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="h-3 flex-1 rounded-sm"
                  style={{
                    backgroundColor:
                      i < 1
                        ? "#10b981"
                        : i < 2
                        ? "#22c55e"
                        : i < 3
                        ? "#eab308"
                        : i < 4
                        ? "#f97316"
                        : "#ef4444",
                  }}
                />
              ))}
              <div className="flex justify-between w-full mt-0.5">
                <span className="text-[10px] text-zinc-600">0 Safe</span>
                <span className="text-[10px] text-zinc-600">100 Risky</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function PairRow({
  pair,
}: {
  pair: TradingPair;
}) {
  const trendColor =
    pair.trendScore >= 70
      ? "text-emerald-400 bg-emerald-500/10"
      : pair.trendScore >= 50
      ? "text-yellow-400 bg-yellow-500/10"
      : "text-red-400 bg-red-500/10";

  const riskColor =
    pair.riskScore <= 30
      ? "text-emerald-400 bg-emerald-500/10"
      : pair.riskScore <= 50
      ? "text-yellow-400 bg-yellow-500/10"
      : "text-orange-400 bg-orange-500/10";

  return (
    <tr
      className={cn(
        "transition-colors hover:bg-zinc-800/30",
        pair.isBlacklisted && "opacity-50"
      )}
    >
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-zinc-100">
            {pair.symbol}
          </span>
          {pair.isBlacklisted && (
            <span className="rounded bg-zinc-700 px-1.5 py-0.5 text-[10px] font-medium text-zinc-400">
              Banned
            </span>
          )}
        </div>
      </td>
      <td className="px-4 py-3 font-mono text-zinc-200">
        $
        {pair.price > 100
          ? pair.price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
          : pair.price.toFixed(4)}
      </td>
      <td className="px-4 py-3">
        <span
          className={cn(
            "flex items-center gap-1 font-medium",
            pair.change24h >= 0 ? "text-emerald-400" : "text-red-400"
          )}
        >
          {pair.change24h >= 0 ? (
            <ArrowUpRight className="h-3 w-3" />
          ) : (
            <ArrowDownRight className="h-3 w-3" />
          )}
          {Math.abs(pair.change24h).toFixed(2)}%
        </span>
      </td>
      <td className="px-4 py-3 text-zinc-400">
        {formatUsd(pair.volume24h)}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="w-16 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full bg-emerald-500"
              style={{ width: `${pair.trendScore}%` }}
            />
          </div>
          <span className={cn("text-xs font-bold rounded px-1.5 py-0.5", trendColor)}>
            {pair.trendScore}
          </span>
        </div>
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="w-16 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full",
                pair.riskScore <= 30
                  ? "bg-emerald-500"
                  : pair.riskScore <= 50
                  ? "bg-yellow-500"
                  : "bg-red-500"
              )}
              style={{ width: `${pair.riskScore}%` }}
            />
          </div>
          <span className={cn("text-xs font-bold rounded px-1.5 py-0.5", riskColor)}>
            {pair.riskScore}
          </span>
        </div>
      </td>
      <td className="px-4 py-3 font-mono text-xs text-zinc-400">
        {pair.spread.toFixed(3)}%
      </td>
      <td className="px-4 py-3">
        <span
          className={cn(
            "rounded px-2 py-0.5 text-[10px] font-bold uppercase",
            pair.lastSignal === "buy" && "bg-emerald-500/15 text-emerald-400",
            pair.lastSignal === "sell" && "bg-red-500/15 text-red-400",
            pair.lastSignal === "close" && "bg-amber-500/15 text-amber-400"
          )}
        >
          {pair.lastSignal}
        </span>
        <span className="ml-1 text-[10px] text-zinc-600">
          {timeAgo(pair.signalTime)}
        </span>
      </td>
    </tr>
  );
}
