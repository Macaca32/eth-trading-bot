"use client";

import {
  Settings,
  Wifi,
  WifiOff,
  Shield,
  Bell,
  ToggleLeft,
  ToggleRight,
  ExternalLink,
  AlertTriangle,
  Zap,
} from "lucide-react";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";

export function Settings() {
  const {
    tradingMode,
    apiConnected,
    setTradingMode,
    setApiConnected,
    dailyLossLimit,
    maxPositions,
    maxExposure,
    setDailyLossLimit,
    setMaxPositions,
    setMaxExposure,
    notifications,
    updateNotification,
  } = useAppStore();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-zinc-50">Settings</h1>
        <p className="text-sm text-zinc-500 mt-1">
          Configure trading bot behavior and risk parameters
        </p>
      </div>

      {/* Trading Mode */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="rounded-lg bg-zinc-800 p-2">
            <Zap
              className={cn(
                "h-5 w-5",
                tradingMode === "live" ? "text-emerald-400" : "text-zinc-400"
              )}
            />
          </div>
          <div>
            <h2 className="text-base font-semibold text-zinc-100">
              Trading Mode
            </h2>
            <p className="text-xs text-zinc-500">
              Switch between paper and live trading
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <button
            onClick={() => setTradingMode("paper")}
            className={cn(
              "rounded-lg border-2 p-4 text-left transition-all",
              tradingMode === "paper"
                ? "border-emerald-500 bg-emerald-500/5"
                : "border-zinc-800 bg-zinc-800/30 hover:border-zinc-700"
            )}
          >
            <div className="flex items-center gap-2 mb-2">
              <div
                className={cn(
                  "h-3 w-3 rounded-full",
                  tradingMode === "paper" ? "bg-emerald-500" : "bg-zinc-600"
                )}
              />
              <span
                className={cn(
                  "text-sm font-semibold",
                  tradingMode === "paper" ? "text-eminc-400" : "text-zinc-300"
                )}
              >
                Paper Trade
              </span>
            </div>
            <p className="text-xs text-zinc-500">
              Simulated trading with virtual funds. No real money at risk.
              Recommended for strategy testing.
            </p>
          </button>

          <button
            onClick={() => setTradingMode("live")}
            className={cn(
              "rounded-lg border-2 p-4 text-left transition-all",
              tradingMode === "live"
                ? "border-emerald-500 bg-emerald-500/5"
                : "border-zinc-800 bg-zinc-800/30 hover:border-zinc-700"
            )}
          >
            <div className="flex items-center gap-2 mb-2">
              <div
                className={cn(
                  "h-3 w-3 rounded-full",
                  tradingMode === "live" ? "bg-emerald-500" : "bg-zinc-600"
                )}
              />
              <div className="flex items-center gap-1.5">
                <span
                  className={cn(
                    "text-sm font-semibold",
                    tradingMode === "live" ? "text-emerald-400" : "text-zinc-300"
                  )}
                >
                  Live Trading
                </span>
                {tradingMode === "live" && (
                  <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
                )}
              </div>
            </div>
            <p className="text-xs text-zinc-500">
              Real trading with actual funds. Full market execution. Ensure
              strategies are thoroughly tested first.
            </p>
          </button>
        </div>

        {tradingMode === "live" && (
          <div className="mt-3 rounded-lg bg-amber-500/5 border border-amber-500/20 p-3 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />
            <p className="text-xs text-amber-400/80">
              <strong>Warning:</strong> Live trading mode uses real funds. Make
              sure all strategies and risk parameters are properly configured.
            </p>
          </div>
        )}
      </div>

      {/* API Connection */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-zinc-800 p-2">
              <Wifi
                className={cn(
                  "h-5 w-5",
                  apiConnected ? "text-emerald-400" : "text-red-400"
                )}
              />
            </div>
            <div>
              <h2 className="text-base font-semibold text-zinc-100">
                API Connection
              </h2>
              <p className="text-xs text-zinc-500">
                Exchange API status and configuration
              </p>
            </div>
          </div>
          <button
            onClick={() => setApiConnected(!apiConnected)}
            className={cn(
              "flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-medium transition-colors",
              apiConnected
                ? "bg-red-500/10 text-red-400 hover:bg-red-500/20"
                : "bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"
            )}
          >
            {apiConnected ? (
              <>
                <WifiOff className="h-3.5 w-3.5" />
                Disconnect
              </>
            ) : (
              <>
                <Wifi className="h-3.5 w-3.5" />
                Connect
              </>
            )}
          </button>
        </div>

        <div className="space-y-2.5 rounded-lg bg-zinc-800/30 p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-500">Status</span>
            <span
              className={cn(
                "inline-flex items-center gap-1.5 text-xs font-medium",
                apiConnected ? "text-emerald-400" : "text-red-400"
              )}
            >
              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  apiConnected ? "bg-emerald-500" : "bg-red-500"
                )}
              />
              {apiConnected ? "Connected" : "Disconnected"}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-500">Exchange</span>
            <span className="text-xs text-zinc-300 font-medium">Binance</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-500">API Key</span>
            <span className="text-xs text-zinc-300 font-mono">
              ••••••••••••a4f2
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-500">Latency</span>
            <span className="text-xs text-zinc-300">
              {apiConnected ? "12ms" : "—"}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-500">Rate Limit</span>
            <span className="text-xs text-zinc-300">
              {apiConnected ? "847 / 1200 (1m)" : "—"}
            </span>
          </div>
        </div>
      </div>

      {/* Risk Limits */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="rounded-lg bg-zinc-800 p-2">
            <Shield className="h-5 w-5 text-amber-400" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-zinc-100">
              Risk Limits
            </h2>
            <p className="text-xs text-zinc-500">
              Configure maximum risk exposure parameters
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="rounded-lg border border-zinc-800 bg-zinc-950/30 p-4">
            <label className="block text-xs font-medium text-zinc-400 mb-2">
              Daily Loss Limit (ETH)
            </label>
            <input
              type="number"
              step="0.1"
              min="0.1"
              max="10"
              value={dailyLossLimit}
              onChange={(e) =>
                setDailyLossLimit(parseFloat(e.target.value) || 0.1)
              }
              className="w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm font-mono text-zinc-200 outline-none focus:border-emerald-500/50 transition-colors"
            />
            <p className="text-[10px] text-zinc-600 mt-1.5">
              Circuit breaker triggers at this daily loss
            </p>
          </div>

          <div className="rounded-lg border border-zinc-800 bg-zinc-950/30 p-4">
            <label className="block text-xs font-medium text-zinc-400 mb-2">
              Max Open Positions
            </label>
            <input
              type="number"
              step="1"
              min="1"
              max="20"
              value={maxPositions}
              onChange={(e) =>
                setMaxPositions(parseInt(e.target.value) || 1)
              }
              className="w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm font-mono text-zinc-200 outline-none focus:border-emerald-500/50 transition-colors"
            />
            <p className="text-[10px] text-zinc-600 mt-1.5">
              Maximum concurrent open trades
            </p>
          </div>

          <div className="rounded-lg border border-zinc-800 bg-zinc-950/30 p-4">
            <label className="block text-xs font-medium text-zinc-400 mb-2">
              Max Portfolio Exposure
            </label>
            <div className="relative">
              <input
                type="number"
                step="0.05"
                min="0.1"
                max="1"
                value={maxExposure}
                onChange={(e) =>
                  setMaxExposure(parseFloat(e.target.value) || 0.1)
                }
                className="w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 pr-8 text-sm font-mono text-zinc-200 outline-none focus:border-emerald-500/50 transition-colors"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-zinc-500">
                {(maxExposure * 100).toFixed(0)}%
              </span>
            </div>
            <p className="text-[10px] text-zinc-600 mt-1.5">
              Maximum capital allocation as fraction
            </p>
          </div>
        </div>
      </div>

      {/* Notifications */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="rounded-lg bg-zinc-800 p-2">
            <Bell className="h-5 w-5 text-emerald-400" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-zinc-100">
              Notifications
            </h2>
            <p className="text-xs text-zinc-500">
              Configure alert preferences and channels
            </p>
          </div>
        </div>

        <div className="space-y-1">
          <NotificationRow
            label="Trade Executed"
            description="Receive alert when a new trade is opened"
            enabled={notifications.tradeExecuted}
            onToggle={() =>
              updateNotification("tradeExecuted", !notifications.tradeExecuted)
            }
          />
          <NotificationRow
            label="Trade Closed"
            description="Receive alert when a trade is closed (P&L update)"
            enabled={notifications.tradeClosed}
            onToggle={() =>
              updateNotification("tradeClosed", !notifications.tradeClosed)
            }
          />
          <NotificationRow
            label="Strategy Alerts"
            description="Strategy enable/disable and parameter changes"
            enabled={notifications.strategyAlert}
            onToggle={() =>
              updateNotification("strategyAlert", !notifications.strategyAlert)
            }
          />
          <NotificationRow
            label="Risk Alerts"
            description="Circuit breaker, drawdown, and exposure warnings"
            enabled={notifications.riskAlert}
            onToggle={() =>
              updateNotification("riskAlert", !notifications.riskAlert)
            }
          />
          <NotificationRow
            label="Daily Report"
            description="End-of-day performance summary"
            enabled={notifications.dailyReport}
            onToggle={() =>
              updateNotification("dailyReport", !notifications.dailyReport)
            }
          />
          <NotificationRow
            label="Weekly Report"
            description="Weekly performance and analytics report"
            enabled={notifications.weeklyReport}
            onToggle={() =>
              updateNotification("weeklyReport", !notifications.weeklyReport)
            }
          />
        </div>

        {/* Notification Channels */}
        <div className="mt-6 pt-6 border-t border-zinc-800">
          <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-4">
            Notification Channels
          </h3>
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={() =>
                updateNotification("telegramEnabled", !notifications.telegramEnabled)
              }
              className={cn(
                "flex items-center gap-2 rounded-lg border px-4 py-3 transition-colors",
                notifications.telegramEnabled
                  ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-400"
                  : "border-zinc-800 bg-zinc-800/30 text-zinc-400 hover:bg-zinc-800"
              )}
            >
              <ExternalLink className="h-4 w-4" />
              <div className="text-left">
                <p className="text-sm font-medium">Telegram</p>
                <p className="text-[10px] text-zinc-500">
                  {notifications.telegramEnabled ? "Connected" : "Not connected"}
                </p>
              </div>
            </button>
            <button
              onClick={() =>
                updateNotification("emailEnabled", !notifications.emailEnabled)
              }
              className={cn(
                "flex items-center gap-2 rounded-lg border px-4 py-3 transition-colors",
                notifications.emailEnabled
                  ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-400"
                  : "border-zinc-800 bg-zinc-800/30 text-zinc-400 hover:bg-zinc-800"
              )}
            >
              <Bell className="h-4 w-4" />
              <div className="text-left">
                <p className="text-sm font-medium">Email</p>
                <p className="text-[10px] text-zinc-500">
                  {notifications.emailEnabled ? "Enabled" : "Disabled"}
                </p>
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function NotificationRow({
  label,
  description,
  enabled,
  onToggle,
}: {
  label: string;
  description: string;
  enabled: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="flex items-center justify-between py-3 px-2 rounded-lg hover:bg-zinc-800/30 transition-colors">
      <div>
        <p className="text-sm font-medium text-zinc-200">{label}</p>
        <p className="text-xs text-zinc-500">{description}</p>
      </div>
      <button
        onClick={onToggle}
        className="shrink-0 ml-4"
        aria-label={`Toggle ${label}`}
      >
        {enabled ? (
          <ToggleRight className="h-8 w-8 text-emerald-400 transition-colors" />
        ) : (
          <ToggleLeft className="h-8 w-8 text-zinc-600 transition-colors" />
        )}
      </button>
    </div>
  );
}
