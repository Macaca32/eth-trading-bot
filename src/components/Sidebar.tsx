"use client";

import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import type { ViewName } from "@/lib/store";
import {
  BookOpen,
  LayoutDashboard,
  Bot,
  Sparkles,
  Search,
  FileText,
  Shield,
  Settings,
  X,
  TrendingUp,
} from "lucide-react";

const navItems: { id: ViewName; label: string; icon: React.ElementType }[] = [
  { id: "tutorial", label: "Tutorial", icon: BookOpen },
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "strategies", label: "Strategies", icon: Bot },
  { id: "ai-optimizer", label: "AI Optimizer", icon: Sparkles },
  { id: "pair-screener", label: "Pair Screener", icon: Search },
  { id: "trade-log", label: "Trade Log", icon: FileText },
  { id: "risk-monitor", label: "Risk Monitor", icon: Shield },
  { id: "settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const { activeView, setActiveView, sidebarOpen, setSidebarOpen, tradingMode } =
    useAppStore();

  return (
    <>
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed top-0 left-0 z-50 h-full w-[260px] border-r border-zinc-800 bg-zinc-900 flex flex-col transition-transform duration-300 lg:translate-x-0 lg:static lg:z-auto",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Logo */}
        <div className="flex items-center justify-between px-5 py-5 border-b border-zinc-800">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/15">
              <TrendingUp className="h-4.5 w-4.5 text-emerald-400" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-zinc-100 tracking-tight">
                ETH Trading Bot
              </h1>
              <p className="text-[10px] text-zinc-500">v2.4.1</p>
            </div>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="rounded-lg p-1 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300 lg:hidden"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Mode Badge */}
        <div className="px-5 py-3">
          <div
            className={cn(
              "flex items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium",
              tradingMode === "paper"
                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
            )}
          >
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                tradingMode === "paper" ? "bg-emerald-500" : "bg-amber-500"
              )}
            />
            {tradingMode === "paper" ? "Paper Trading" : "Live Trading"}
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-2 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = activeView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveView(item.id)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-emerald-500/10 text-emerald-400"
                    : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
                )}
              >
                <item.icon
                  className={cn(
                    "h-4.5 w-4.5 shrink-0",
                    isActive ? "text-emerald-400" : "text-zinc-500"
                  )}
                />
                {item.label}
                {isActive && (
                  <div className="ml-auto h-1.5 w-1.5 rounded-full bg-emerald-500" />
                )}
              </button>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="border-t border-zinc-800 px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-zinc-800 text-xs font-bold text-zinc-300">
              TB
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-zinc-300 truncate">
                Trader Bot
              </p>
              <p className="text-[10px] text-zinc-600">Binance · Main</p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
