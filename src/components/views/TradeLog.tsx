"use client";

import { useState, useMemo } from "react";
import {
  Download,
  Filter,
  Trophy,
  TrendingUp,
  Calendar,
  BarChart3,
} from "lucide-react";
import { useAppStore } from "@/lib/store";
import { cn, formatEth, formatPercent, formatDateTime } from "@/lib/utils";
import type { TradeSide, TradeOutcome } from "@/lib/types";

export function TradeLog() {
  const { trades } = useAppStore();
  const [filterPair, setFilterPair] = useState("all");
  const [filterStrategy, setFilterStrategy] = useState("all");
  const [filterSide, setFilterSide] = useState<"all" | TradeSide>("all");
  const [filterOutcome, setFilterOutcome] = useState<"all" | TradeOutcome>("all");
  const [showFilters, setShowFilters] = useState(false);

  const allPairs = useMemo(() => [...new Set(trades.map((t) => t.pair))], [trades]);
  const allStrategies = useMemo(() => [...new Set(trades.map((t) => t.strategy))], [trades]);

  const filteredTrades = useMemo(() => {
    return trades.filter((t) => {
      if (filterPair !== "all" && t.pair !== filterPair) return false;
      if (filterStrategy !== "all" && t.strategy !== filterStrategy) return false;
      if (filterSide !== "all" && t.side !== filterSide) return false;
      if (filterOutcome !== "all" && t.outcome !== filterOutcome) return false;
      return true;
    });
  }, [trades, filterPair, filterStrategy, filterSide, filterOutcome]);

  // Summary stats
  const wins = filteredTrades.filter((t) => t.outcome === "win");
  const losses = filteredTrades.filter((t) => t.outcome === "loss");
  const totalPnl = filteredTrades.reduce((sum, t) => sum + t.pnl, 0);
  const totalFees = filteredTrades.reduce((sum, t) => sum + t.fees, 0);
  const winRate =
    filteredTrades.length > 0
      ? ((wins.length / filteredTrades.length) * 100).toFixed(1)
      : "0.0";

  const handleExport = () => {
    const headers = [
      "Pair",
      "Side",
      "Strategy",
      "Entry Price",
      "Exit Price",
      "Quantity",
      "P&L (ETH)",
      "P&L %",
      "Outcome",
      "Entry Date",
      "Exit Date",
      "Duration",
      "Fees",
    ];
    const rows = filteredTrades.map((t) => [
      t.pair,
      t.side,
      t.strategy,
      t.entryPrice,
      t.exitPrice,
      t.quantity,
      t.pnl,
      t.pnlPercent,
      t.outcome,
      new Date(t.entryDate).toISOString(),
      new Date(t.exitDate).toISOString(),
      t.duration,
      t.fees,
    ]);
    const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `trade-log-${new Date().toISOString().split("T")[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-50">Trade Log</h1>
          <p className="text-sm text-zinc-500 mt-1">
            {filteredTrades.length} trades shown of {trades.length} total
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={cn(
              "flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium transition-colors",
              showFilters
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                : "border-zinc-800 bg-zinc-900 text-zinc-400 hover:bg-zinc-800"
            )}
          >
            <Filter className="h-3.5 w-3.5" />
            Filters
          </button>
          <button
            onClick={handleExport}
            className="flex items-center gap-2 rounded-lg bg-zinc-800 px-3 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-700 transition-colors"
          >
            <Download className="h-3.5 w-3.5" />
            Export CSV
          </button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-3">
          <div className="flex items-center gap-2 mb-1">
            <Trophy className="h-3.5 w-3.5 text-emerald-400" />
            <span className="text-[10px] font-medium uppercase text-zinc-500">
              Win Rate
            </span>
          </div>
          <p className="text-lg font-bold text-zinc-100">{winRate}%</p>
          <p className="text-[10px] text-zinc-500">
            {wins.length}W / {losses.length}L
          </p>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-3">
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
            <span className="text-[10px] font-medium uppercase text-zinc-500">
              Total P&L
            </span>
          </div>
          <p
            className={cn(
              "text-lg font-bold",
              totalPnl >= 0 ? "text-emerald-400" : "text-red-400"
            )}
          >
            {formatEth(totalPnl)}
          </p>
          <p className="text-[10px] text-zinc-500">
            Fees: {totalFees.toFixed(6)} ETH
          </p>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-3">
          <div className="flex items-center gap-2 mb-1">
            <BarChart3 className="h-3.5 w-3.5 text-amber-400" />
            <span className="text-[10px] font-medium uppercase text-zinc-500">
              Avg Win
            </span>
          </div>
          <p className="text-lg font-bold text-emerald-400">
            {wins.length > 0
              ? formatEth(wins.reduce((s, t) => s + t.pnl, 0) / wins.length)
              : "—"}
          </p>
          <p className="text-[10px] text-zinc-500">
            Avg Loss:{" "}
            {losses.length > 0
              ? formatEth(losses.reduce((s, t) => s + t.pnl, 0) / losses.length)
              : "—"}
          </p>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-3">
          <div className="flex items-center gap-2 mb-1">
            <Calendar className="h-3.5 w-3.5 text-zinc-400" />
            <span className="text-[10px] font-medium uppercase text-zinc-500">
              Best Trade
            </span>
          </div>
          <p className="text-lg font-bold text-emerald-400">
            {wins.length > 0
              ? formatEth(Math.max(...wins.map((t) => t.pnl)))
              : "—"}
          </p>
          <p className="text-[10px] text-zinc-500">
            Worst:{" "}
            {losses.length > 0
              ? formatEth(Math.min(...losses.map((t) => t.pnl)))
              : "—"}
          </p>
        </div>
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div>
              <label className="block text-xs font-medium text-zinc-500 mb-1">
                Pair
              </label>
              <select
                value={filterPair}
                onChange={(e) => setFilterPair(e.target.value)}
                className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 outline-none focus:border-zinc-700"
              >
                <option value="all">All Pairs</option>
                {allPairs.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-500 mb-1">
                Strategy
              </label>
              <select
                value={filterStrategy}
                onChange={(e) => setFilterStrategy(e.target.value)}
                className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 outline-none focus:border-zinc-700"
              >
                <option value="all">All Strategies</option>
                {allStrategies.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-500 mb-1">
                Side
              </label>
              <select
                value={filterSide}
                onChange={(e) =>
                  setFilterSide(e.target.value as "all" | TradeSide)
                }
                className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 outline-none focus:border-zinc-700"
              >
                <option value="all">All Sides</option>
                <option value="long">Long</option>
                <option value="short">Short</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-500 mb-1">
                Outcome
              </label>
              <select
                value={filterOutcome}
                onChange={(e) =>
                  setFilterOutcome(e.target.value as "all" | TradeOutcome)
                }
                className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 outline-none focus:border-zinc-700"
              >
                <option value="all">All Outcomes</option>
                <option value="win">Win</option>
                <option value="loss">Loss</option>
                <option value="breakeven">Breakeven</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Trade Table */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 overflow-hidden">
        <div className="overflow-x-auto max-h-96 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 z-10">
              <tr className="border-b border-zinc-800 bg-zinc-900">
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Date
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Pair
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Strategy
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Side
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Entry
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Exit
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Qty
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-zinc-500">
                  P&L
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-zinc-500">
                  P&L %
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Outcome
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Duration
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {filteredTrades.map((trade) => (
                <tr
                  key={trade.id}
                  className="hover:bg-zinc-800/30 transition-colors"
                >
                  <td className="px-4 py-3 text-xs text-zinc-400 whitespace-nowrap">
                    {formatDateTime(trade.exitDate)}
                  </td>
                  <td className="px-4 py-3 font-medium text-zinc-200">
                    {trade.pair}
                  </td>
                  <td className="px-4 py-3 text-zinc-400 text-xs">
                    {trade.strategy}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        "rounded px-1.5 py-0.5 text-[10px] font-bold uppercase",
                        trade.side === "long"
                          ? "bg-emerald-500/15 text-emerald-400"
                          : "bg-red-500/15 text-red-400"
                      )}
                    >
                      {trade.side}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-zinc-400">
                    {trade.entryPrice.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-zinc-400">
                    {trade.exitPrice.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-zinc-400">
                    {trade.quantity.toFixed(4)}
                  </td>
                  <td
                    className={cn(
                      "px-4 py-3 text-right font-medium",
                      trade.pnl >= 0 ? "text-emerald-400" : "text-red-400"
                    )}
                  >
                    {formatEth(trade.pnl)}
                  </td>
                  <td
                    className={cn(
                      "px-4 py-3 text-right font-medium",
                      trade.pnlPercent >= 0 ? "text-emerald-400" : "text-red-400"
                    )}
                  >
                    {formatPercent(trade.pnlPercent)}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-[10px] font-medium",
                        trade.outcome === "win" &&
                          "bg-emerald-500/15 text-emerald-400",
                        trade.outcome === "loss" &&
                          "bg-red-500/15 text-red-400",
                        trade.outcome === "breakeven" &&
                          "bg-zinc-500/15 text-zinc-400"
                      )}
                    >
                      {trade.outcome === "win"
                        ? "✓ Win"
                        : trade.outcome === "loss"
                        ? "✗ Loss"
                        : "— Tie"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-zinc-500">
                    {trade.duration}
                  </td>
                </tr>
              ))}
              {filteredTrades.length === 0 && (
                <tr>
                  <td
                    colSpan={11}
                    className="px-4 py-8 text-center text-sm text-zinc-500"
                  >
                    No trades match the selected filters
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
