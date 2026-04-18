"use client";

import { useAppStore } from "@/lib/store";
import { Sidebar } from "./Sidebar";
import { Overview } from "./views/Overview";
import { Strategies } from "./views/Strategies";
import { AiOptimizer } from "./views/AiOptimizer";
import { PairScreener } from "./views/PairScreener";
import { TradeLog } from "./views/TradeLog";
import { RiskMonitor } from "./views/RiskMonitor";
import { Settings } from "./views/Settings";
import { Menu, TrendingUp } from "lucide-react";
import type { ViewName } from "@/lib/store";

const viewComponents: Record<ViewName, React.ComponentType> = {
  overview: Overview,
  strategies: Strategies,
  "ai-optimizer": AiOptimizer,
  "pair-screener": PairScreener,
  "trade-log": TradeLog,
  "risk-monitor": RiskMonitor,
  settings: Settings,
};


export function Dashboard() {
  const { activeView, setSidebarOpen, tradingMode } = useAppStore();
  const ActiveView = viewComponents[activeView];

  return (
    <div className="flex h-screen bg-zinc-950 overflow-hidden">
      <Sidebar />

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Bar (Mobile) */}
        <header className="flex items-center justify-between border-b border-zinc-800 bg-zinc-900 px-4 py-3 lg:hidden">
          <button
            onClick={() => setSidebarOpen(true)}
            className="rounded-lg p-2 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-emerald-400" />
            <span className="text-sm font-semibold text-zinc-100">
              ETH Trading Bot
            </span>
          </div>
          <div
            className={`rounded-full px-2 py-1 text-[10px] font-medium ${
              tradingMode === "paper"
                ? "bg-emerald-500/10 text-emerald-400"
                : "bg-amber-500/10 text-amber-400"
            }`}
          >
            {tradingMode === "paper" ? "Paper" : "Live"}
          </div>
        </header>

        {/* Scrollable content area */}
        <div className="flex-1 overflow-y-auto">
          <div className="p-4 lg:p-6 max-w-[1600px] mx-auto">
            <ActiveView />
          </div>
        </div>
      </main>
    </div>
  );
}
