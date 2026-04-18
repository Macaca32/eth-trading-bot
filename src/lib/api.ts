/**
 * API client for the ETH Trading Bot backend.
 *
 * Connects to the FastAPI server (default: http://localhost:3003).
 * Falls back to mock data when the API is unreachable.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3003";

// ─── Generic fetch wrapper ───────────────────────────────────────────

async function apiFetch<T>(path: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) throw new Error(`API ${res.status}`);
    return await res.json();
  } catch {
    console.warn(`[API] Failed to fetch ${path}, using fallback`);
    return fallback;
  }
}

// ─── WebSocket connection ────────────────────────────────────────────

type WsMessageHandler = (data: any) => void;

let ws: WebSocket | null = null;
let wsReconnectTimer: ReturnType<typeof setTimeout> | null = null;
let wsHandlers: Map<string, WsMessageHandler[]> = new Map();

function connectWebSocket() {
  if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) {
    return;
  }

  const wsUrl = API_BASE.replace(/^http/, "ws");
  try {
    ws = new WebSocket(wsUrl + "/ws");

    ws.onopen = () => {
      console.log("[WS] Connected to bot API");
      if (wsReconnectTimer) {
        clearTimeout(wsReconnectTimer);
        wsReconnectTimer = null;
      }
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        const handlers = wsHandlers.get(msg.type) || [];
        handlers.forEach((handler) => handler(msg.data));
        // Also notify wildcard handlers
        const wildcards = wsHandlers.get("*") || [];
        wildcards.forEach((handler) => handler(msg));
      } catch {
        // Ignore parse errors
      }
    };

    ws.onclose = () => {
      console.log("[WS] Disconnected, reconnecting in 3s...");
      ws = null;
      wsReconnectTimer = setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = () => {
      ws?.close();
    };
  } catch {
    wsReconnectTimer = setTimeout(connectWebSocket, 3000);
  }
}

function onWsMessage(type: string, handler: WsMessageHandler) {
  if (!wsHandlers.has(type)) wsHandlers.set(type, []);
  wsHandlers.get(type)!.push(handler);
}

function offWsMessage(type: string, handler: WsMessageHandler) {
  const handlers = wsHandlers.get(type);
  if (handlers) {
    const idx = handlers.indexOf(handler);
    if (idx >= 0) handlers.splice(idx, 1);
  }
}

// ─── REST API methods ────────────────────────────────────────────────

export const api = {
  /** Get bot status (mode, connected, uptime) */
  getStatus: () => apiFetch("/api/status", { status: "stopped", mode: "paper", connected: false }),

  /** Get account balance */
  getBalance: () =>
    apiFetch("/api/balance", {
      total_equity: 0, available_balance: 0, margin_used: 0, unrealized_pnl: 0,
    }),

  /** Get open positions */
  getPositions: () => apiFetch("/api/positions", []),

  /** Get trade history */
  getTrades: () => apiFetch("/api/trades", []),

  /** Get recent signals */
  getSignals: () => apiFetch("/api/signals", []),

  /** Get strategy configs */
  getStrategies: () => apiFetch("/api/strategies", []),

  /** Get risk metrics */
  getRiskMetrics: () =>
    apiFetch("/api/risk", {
      totalExposure: 0, maxExposure: 0.5, dailyPnl: 0, weeklyPnl: 0, monthlyPnl: 0,
      sharpeRatio: 0, sortinoRatio: 0, maxDrawdown: 0, currentDrawdown: 0,
      winRate: 0, profitFactor: 0, avgWin: 0, avgLoss: 0,
      consecutiveWins: 0, consecutiveLosses: 0,
      circuitBreakerActive: false, circuitBreakerLevel: 0,
      dailyLossLimit: 7, maxPositions: 5, usedPositions: 0,
    }),

  /** Get screened pairs */
  getPairs: () => apiFetch("/api/pairs", []),

  /** Get optimization history */
  getOptimizations: () => apiFetch("/api/optimizations", []),

  /** Get equity curve */
  getEquity: () =>
    apiFetch("/api/equity", []),

  /** Get daily P&L */
  getDailyPnl: () => apiFetch("/api/daily-pnl", []),

  // ─── Mutations ──────────────────────────────────────────────────

  /** Toggle strategy enabled/disabled */
  toggleStrategy: async (strategyId: string, enabled: boolean) => {
    try {
      const res = await fetch(`${API_BASE}/api/strategies/toggle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ strategy_id: strategyId, enabled }),
      });
      return await res.json();
    } catch {
      return { success: false };
    }
  },

  /** Update a strategy parameter */
  updateParam: async (strategyId: string, paramName: string, value: number) => {
    try {
      const res = await fetch(`${API_BASE}/api/strategies/param`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ strategy_id: strategyId, param_name: paramName, value }),
      });
      return await res.json();
    } catch {
      return { success: false };
    }
  },

  /** Switch trading mode */
  setTradingMode: async (mode: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/mode`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });
      return await res.json();
    } catch {
      return { success: false };
    }
  },

  /** Update risk settings */
  updateRiskSettings: async (settings: {
    daily_loss_limit?: number;
    max_positions?: number;
    max_exposure?: number;
  }) => {
    try {
      const res = await fetch(`${API_BASE}/api/risk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
      return await res.json();
    } catch {
      return { success: false };
    }
  },

  /** Start optimization */
  startOptimization: async () => {
    try {
      const res = await fetch(`${API_BASE}/api/optimizations/start`, {
        method: "POST",
      });
      return await res.json();
    } catch {
      return { success: false };
    }
  },

  // ─── WebSocket ─────────────────────────────────────────────────

  /** Connect to the WebSocket server */
  connectWs: connectWebSocket,

  /** Subscribe to a WebSocket message type */
  onWsMessage,

  /** Unsubscribe from a WebSocket message type */
  offWsMessage,
};
