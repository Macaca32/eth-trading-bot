"""
FastAPI + WebSocket server for the ETH Trading Bot dashboard.

Provides:
  - REST endpoints for strategy control, trade history, risk metrics, etc.
  - WebSocket endpoint for real-time streaming of signals, positions, and prices.
  - CORS enabled for Next.js frontend on localhost:3000.

Usage:
    python api_server.py                    # Start API only (port 3003)
    python main.py --api                   # Start bot + API server together
"""

from __future__ import annotations

import asyncio
import json
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Models for API request/response
# ---------------------------------------------------------------------------

class StrategyToggle(BaseModel):
    strategy_id: str
    enabled: bool

class ParamUpdate(BaseModel):
    strategy_id: str
    param_name: str
    value: float

class TradingModeUpdate(BaseModel):
    mode: str  # "paper" or "live"

class RiskSettings(BaseModel):
    daily_loss_limit: Optional[float] = None
    max_positions: Optional[int] = None
    max_exposure: Optional[float] = None


# ---------------------------------------------------------------------------
# API Server
# ---------------------------------------------------------------------------

class BotAPIServer:
    """
    FastAPI server that bridges the trading bot with the Next.js dashboard.

    If the bot is running, it pulls live data from the bot components.
    If the bot is NOT running, it serves mock/demo data so the dashboard
    still works for UI development and testing.
    """

    def __init__(self, bot=None, config=None, db=None) -> None:
        self._bot = bot
        self._config = config
        self._db = db
        self._ws_clients: list[WebSocket] = []
        self._broadcast_queue: asyncio.Queue = asyncio.Queue()
        self._broadcast_task: Optional[asyncio.Task] = None

    # -- Lifecycle ---------------------------------------------------------

    def create_app(self) -> FastAPI:
        """Create and configure the FastAPI application."""
        app = FastAPI(
            title="ETH Trading Bot API",
            description="REST + WebSocket API for the Hyperliquid ETH Trading Bot",
            version="2.4.1",
        )

        # CORS for Next.js frontend
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "http://localhost:3000",
                "http://localhost:3001",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3001",
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # -- REST endpoints ------------------------------------------------
        app.get("/api/status")(self.get_status)
        app.get("/api/balance")(self.get_balance)
        app.get("/api/positions")(self.get_positions)
        app.get("/api/trades")(self.get_trades)
        app.get("/api/signals")(self.get_signals)
        app.get("/api/strategies")(self.get_strategies)
        app.get("/api/risk")(self.get_risk_metrics)
        app.get("/api/pairs")(self.get_pairs)
        app.get("/api/optimizations")(self.get_optimizations)
        app.get("/api/equity")(self.get_equity_curve)
        app.get("/api/daily-pnl")(self.get_daily_pnl)

        app.post("/api/strategies/toggle")(self.toggle_strategy)
        app.post("/api/strategies/param")(self.update_param)
        app.post("/api/mode")(self.update_trading_mode)
        app.post("/api/risk")(self.update_risk_settings)
        app.post("/api/optimizations/start")(self.start_optimization)

        # -- WebSocket endpoint --------------------------------------------
        app.websocket("/ws")(self.websocket_endpoint)

        # -- Startup / shutdown --------------------------------------------
        @app.on_event("startup")
        async def on_startup():
            self._broadcast_task = asyncio.create_task(self._broadcast_loop())
            logger.info("API server started on port 3003")

        @app.on_event("shutdown")
        async def on_shutdown():
            if self._broadcast_task:
                self._broadcast_task.cancel()
            logger.info("API server stopped")

        return app

    # -- REST handlers -----------------------------------------------------

    async def get_status(self) -> dict[str, Any]:
        """Get bot status."""
        is_live = False
        if self._config:
            from config import TradingMode
            is_live = self._config.exchange.trading_mode == TradingMode.LIVE

        return {
            "status": "running" if self._bot and self._bot._running else "stopped",
            "mode": "live" if is_live else "paper",
            "connected": True,
            "uptime": self._get_uptime(),
            "version": "2.4.1",
        }

    async def get_balance(self) -> dict[str, Any]:
        """Get account balance."""
        if self._bot and self._bot._client:
            try:
                balance = await self._bot._client.get_balance()
                return {
                    "total_equity": balance.total_equity,
                    "available_balance": balance.available_balance,
                    "margin_used": balance.margin_used,
                    "unrealized_pnl": balance.unrealized_pnl,
                }
            except Exception as exc:
                logger.error("Error fetching balance: {}", exc)

        return {
            "total_equity": 0.0,
            "available_balance": 0.0,
            "margin_used": 0.0,
            "unrealized_pnl": 0.0,
        }

    async def get_positions(self) -> list[dict[str, Any]]:
        """Get open positions."""
        if self._bot and self._bot._client:
            try:
                positions = await self._bot._client.get_positions()
                return [
                    {
                        "id": f"pos-{i}",
                        "pair": p.coin,
                        "side": p.side,
                        "strategy": "",
                        "entry_price": p.entry_price,
                        "current_price": p.entry_price,  # Would need midpoint for current
                        "quantity": p.size,
                        "unrealized_pnl": p.unrealized_pnl,
                        "unrealized_pnl_percent": (
                            (p.unrealized_pnl / (p.size * p.entry_price) * 100)
                            if p.size * p.entry_price > 0 else 0
                        ),
                        "leverage": p.leverage,
                        "entry_date": datetime.now(timezone.utc).isoformat(),
                        "stop_loss": 0,
                        "take_profit": 0,
                    }
                    for i, p in enumerate(positions)
                ]
            except Exception as exc:
                logger.error("Error fetching positions: {}", exc)
        return []

    async def get_trades(self) -> list[dict[str, Any]]:
        """Get trade history."""
        if self._db:
            trades = self._db.get_recent_trades(limit=100)
            open_trades = self._db.get_open_trades()
            all_trades = trades + open_trades
            return [
                {
                    "id": f"trade-{t['id']}",
                    "pair": t["pair"],
                    "side": t["direction"],
                    "strategy": t["strategy"],
                    "entry_price": t.get("entry_price", 0),
                    "exit_price": t.get("exit_price"),
                    "quantity": t.get("quantity", 0),
                    "pnl": t.get("pnl", 0),
                    "pnl_percent": (
                        (t["pnl"] / (t["quantity"] * t["entry_price"]) * 100)
                        if t.get("pnl") and t.get("quantity") and t.get("entry_price") and t["entry_price"] > 0
                        else 0
                    ),
                    "outcome": (
                        "win" if t.get("pnl", 0) > 0.001
                        else "loss" if t.get("pnl", 0) < -0.001
                        else "breakeven"
                    ),
                    "entry_date": (
                        datetime.fromtimestamp(t["entry_timestamp"] / 1000, tz=timezone.utc).isoformat()
                        if t.get("entry_timestamp") else ""
                    ),
                    "exit_date": (
                        datetime.fromtimestamp(t["exit_timestamp"] / 1000, tz=timezone.utc).isoformat()
                        if t.get("exit_timestamp") else ""
                    ),
                    "status": t.get("status", "open"),
                    "fees": t.get("fee", 0),
                }
                for t in all_trades
            ]
        return []

    async def get_signals(self) -> list[dict[str, Any]]:
        """Get recent signals."""
        if self._db:
            signals = self._db.get_recent_signals(limit=50)
            return [
                {
                    "id": f"sig-{s['id']}",
                    "pair": s["pair"],
                    "type": s["direction"],
                    "strategy": s["strategy"],
                    "price": s.get("entry_price", 0),
                    "confidence": s.get("confidence", 0) * 100,
                    "timestamp": (
                        datetime.fromtimestamp(s["timestamp"] / 1000, tz=timezone.utc).isoformat()
                        if s.get("timestamp") else ""
                    ),
                    "reason": f"{s['strategy']} signal on {s['pair']}",
                }
                for s in signals
            ]
        return []

    async def get_strategies(self) -> list[dict[str, Any]]:
        """Get strategy configurations and performance."""
        if self._bot and self._bot._strategies:
            strategies = []
            for s in self._bot._strategies:
                param_ranges = s.get_param_ranges()
                params = []
                for name, (min_val, max_val) in param_ranges.items():
                    default = s._params.get(name, min_val) if hasattr(s, "_params") else min_val
                    params.append({
                        "name": name.replace("_", " ").title(),
                        "value": default,
                        "min": min_val,
                        "max": max_val,
                        "step": 0.1 if isinstance(default, float) else 1,
                        "unit": "x" if "multiplier" in name.lower() else
                               "%" if "loss" in name.lower() or "profit" in name.lower() else "",
                    })
                strategies.append({
                    "id": f"strat-{s.name.lower().replace(' ', '-')[:20]}",
                    "name": s.name,
                    "description": getattr(s, "description", ""),
                    "enabled": True,
                    "winRate": 0,
                    "totalTrades": 0,
                    "avgProfit": 0,
                    "totalPnl": 0,
                    "timeframe": "1h",
                    "params": params,
                })
            return strategies
        return []

    async def get_risk_metrics(self) -> dict[str, Any]:
        """Get current risk metrics."""
        if self._bot and self._bot._risk_manager:
            rm = self._bot._risk_manager
            cb = rm.circuit_breaker
            return {
                "totalExposure": 0,
                "maxExposure": self._config.risk.max_capital_deployed_pct / 100 if self._config else 0.5,
                "dailyPnl": rm._get_daily_pnl() if hasattr(rm, "_get_daily_pnl") else 0,
                "weeklyPnl": 0,
                "monthlyPnl": 0,
                "sharpeRatio": 0,
                "sortinoRatio": 0,
                "maxDrawdown": 0,
                "currentDrawdown": 0,
                "winRate": 0,
                "profitFactor": 0,
                "avgWin": 0,
                "avgLoss": 0,
                "consecutiveWins": cb.wins if hasattr(cb, "wins") else 0,
                "consecutiveLosses": cb.losses if hasattr(cb, "losses") else 0,
                "circuitBreakerActive": cb.is_active() if hasattr(cb, "is_active") else False,
                "circuitBreakerLevel": cb.level if hasattr(cb, "level") else 0,
                "dailyLossLimit": self._config.risk.max_daily_risk_pct if self._config else 7.0,
                "maxPositions": self._config.risk.max_concurrent_positions if self._config else 5,
                "usedPositions": 0,
            }
        return {}

    async def get_pairs(self) -> list[dict[str, Any]]:
        """Get screened trading pairs."""
        if self._bot and hasattr(self._bot, "_approved_pairs"):
            pairs = []
            for pair in self._bot._approved_pairs:
                pairs.append({
                    "symbol": pair,
                    "baseAsset": pair.split("/")[0] if "/" in pair else pair,
                    "quoteAsset": pair.split("/")[1] if "/" in pair else "USDT",
                    "price": 0,
                    "change24h": 0,
                    "volume24h": 0,
                    "trendScore": 0,
                    "riskScore": 0,
                    "spread": 0,
                    "isBlacklisted": False,
                    "lastSignal": "",
                    "signalTime": "",
                })
            return pairs
        return []

    async def get_optimizations(self) -> list[dict[str, Any]]:
        """Get optimization history."""
        if self._db:
            # Query all optimization records
            from models.database import Database
            with self._db.connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM optimizations ORDER BY timestamp DESC LIMIT 20"
                ).fetchall()
                return [
                    {
                        "id": f"opt-{r['id']}",
                        "strategy": r["strategy"],
                        "startTime": datetime.fromtimestamp(
                            r["timestamp"] / 1000, tz=timezone.utc
                        ).isoformat() if r.get("timestamp") else "",
                        "endTime": "",
                        "status": "completed",
                        "iterations": r.get("n_trades", 0),
                        "bestSharpe": r.get("sharpe", 0),
                        "bestParams": json.loads(r["params_json"]) if r.get("params_json") else {},
                        "improvement": 0,
                    }
                    for r in rows
                ]
        return []

    async def get_equity_curve(self) -> list[dict[str, Any]]:
        """Get equity curve data points."""
        # Build from trade history
        if self._db:
            with self._db.connection() as conn:
                rows = conn.execute(
                    "SELECT entry_timestamp, pnl FROM trades "
                    "WHERE status='closed' AND pnl IS NOT NULL "
                    "ORDER BY entry_timestamp ASC"
                ).fetchall()
                if rows:
                    equity = 10.0  # Starting ETH
                    points = []
                    for r in rows:
                        equity += r["pnl"]
                        points.append({
                            "date": datetime.fromtimestamp(
                                r["entry_timestamp"] / 1000, tz=timezone.utc
                            ).strftime("%Y-%m-%d"),
                            "equity": round(equity, 4),
                            "drawdown": 0,
                            "benchmark": equity,
                        })
                    return points[-200:]  # Last 200 points
        return []

    async def get_daily_pnl(self) -> list[dict[str, Any]]:
        """Get daily P&L data."""
        if self._db:
            with self._db.connection() as conn:
                rows = conn.execute(
                    "SELECT exit_timestamp, pnl, fee FROM trades "
                    "WHERE status='closed' AND pnl IS NOT NULL AND exit_timestamp IS NOT NULL "
                    "ORDER BY exit_timestamp ASC"
                ).fetchall()
                if rows:
                    daily: dict[str, float] = {}
                    for r in rows:
                        day = datetime.fromtimestamp(
                            r["exit_timestamp"] / 1000, tz=timezone.utc
                        ).strftime("%Y-%m-%d")
                        daily[day] = daily.get(day, 0) + r["pnl"]

                    cumulative = 0
                    points = []
                    for day, pnl in sorted(daily.items()):
                        cumulative += pnl
                        points.append({
                            "date": day,
                            "pnl": round(pnl, 4),
                            "cumulative": round(cumulative, 4),
                            "trades": 1,
                        })
                    return points[-30:]  # Last 30 days
        return []

    # -- Mutation endpoints ------------------------------------------------

    async def toggle_strategy(self, body: StrategyToggle) -> dict[str, Any]:
        """Enable/disable a strategy."""
        if self._bot and self._bot._strategies:
            for s in self._bot._strategies:
                if s.name.lower().replace(" ", "-") in body.strategy_id.lower():
                    # Toggle via a simple enabled flag
                    if not hasattr(s, "_enabled"):
                        s._enabled = True
                    s._enabled = body.enabled
                    await self._broadcast({
                        "type": "strategy_toggle",
                        "strategy_id": body.strategy_id,
                        "enabled": body.enabled,
                    })
                    return {"success": True, "strategy": s.name, "enabled": body.enabled}
        return {"success": False, "error": "Strategy not found"}

    async def update_param(self, body: ParamUpdate) -> dict[str, Any]:
        """Update a strategy parameter."""
        if self._bot and self._bot._strategies:
            for s in self._bot._strategies:
                if s.name.lower().replace(" ", "-") in body.strategy_id.lower():
                    param_key = body.param_name.lower().replace(" ", "_")
                    if hasattr(s, "set_params"):
                        s.set_params({param_key: body.value})
                    await self._broadcast({
                        "type": "param_update",
                        "strategy_id": body.strategy_id,
                        "param_name": body.param_name,
                        "value": body.value,
                    })
                    return {"success": True, "strategy": s.name, "param": param_key, "value": body.value}
        return {"success": False, "error": "Strategy not found"}

    async def update_trading_mode(self, body: TradingModeUpdate) -> dict[str, Any]:
        """Switch between paper and live trading."""
        mode = body.mode.lower()
        if mode not in ("paper", "live"):
            return {"success": False, "error": "Mode must be 'paper' or 'live'"}

        if self._config:
            from config import TradingMode
            self._config.exchange.trading_mode = TradingMode.LIVE if mode == "live" else TradingMode.PAPER

        await self._broadcast({
            "type": "mode_change",
            "mode": mode,
        })
        return {"success": True, "mode": mode}

    async def update_risk_settings(self, body: RiskSettings) -> dict[str, Any]:
        """Update risk management settings."""
        if self._config:
            if body.daily_loss_limit is not None:
                self._config.risk.max_daily_risk_pct = body.daily_loss_limit
            if body.max_positions is not None:
                self._config.risk.max_concurrent_positions = body.max_positions
            if body.max_exposure is not None:
                self._config.risk.max_capital_deployed_pct = body.max_exposure * 100

        await self._broadcast({
            "type": "risk_settings_update",
            "settings": body.model_dump(exclude_none=True),
        })
        return {"success": True}

    async def start_optimization(self) -> dict[str, Any]:
        """Trigger a strategy optimization run."""
        if self._bot and hasattr(self._bot, "_run_optimization"):
            asyncio.create_task(self._bot._run_optimization())
            return {"success": True, "message": "Optimization started"}
        return {"success": False, "error": "Bot not running"}

    # -- WebSocket ---------------------------------------------------------

    async def websocket_endpoint(self, websocket: WebSocket) -> None:
        """Handle WebSocket connections from the dashboard."""
        await websocket.accept()
        self._ws_clients.append(websocket)
        logger.info("WebSocket client connected (total: {})", len(self._ws_clients))

        try:
            # Send initial status
            await websocket.send_json({
                "type": "connected",
                "data": await self.get_status(),
            })

            # Keep connection alive and handle client messages
            while True:
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)
                    await self._handle_ws_message(msg, websocket)
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "message": "Invalid JSON"})

        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
        except Exception as exc:
            logger.error("WebSocket error: {}", exc)
        finally:
            if websocket in self._ws_clients:
                self._ws_clients.remove(websocket)

    async def _handle_ws_message(self, msg: dict, ws: WebSocket) -> None:
        """Handle incoming WebSocket messages from the dashboard."""
        msg_type = msg.get("type", "")

        if msg_type == "ping":
            await ws.send_json({"type": "pong"})
        elif msg_type == "subscribe":
            channels = msg.get("channels", [])
            await ws.send_json({
                "type": "subscribed",
                "channels": channels,
            })
        elif msg_type == "get_status":
            await ws.send_json({"type": "status", "data": await self.get_status()})
        elif msg_type == "get_trades":
            trades = await self.get_trades()
            await ws.send_json({"type": "trades", "data": trades})
        elif msg_type == "get_signals":
            signals = await self.get_signals()
            await ws.send_json({"type": "signals", "data": signals})
        elif msg_type == "get_positions":
            positions = await self.get_positions()
            await ws.send_json({"type": "positions", "data": positions})

    # -- Broadcast ---------------------------------------------------------

    async def _broadcast(self, message: dict[str, Any]) -> None:
        """Queue a message for broadcast to all WebSocket clients."""
        await self._broadcast_queue.put(message)

    async def _broadcast_loop(self) -> None:
        """Process broadcast queue and send to all connected WebSocket clients."""
        while True:
            try:
                message = await self._broadcast_queue.get()
                disconnected = []
                for client in self._ws_clients:
                    try:
                        await client.send_json(message)
                    except Exception:
                        disconnected.append(client)
                for client in disconnected:
                    self._ws_clients.remove(client)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Broadcast error: {}", exc)

    # -- Helpers -----------------------------------------------------------

    def _get_uptime(self) -> str:
        """Get bot uptime as a human-readable string."""
        if self._bot and hasattr(self._bot, "_start_time"):
            elapsed = time.time() - self._bot._start_time
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            return f"{hours}h {minutes}m"
        return "0h 0m"


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

def run_api_server(host: str = "0.0.0.0", port: int = 3003, bot=None, config=None, db=None) -> None:
    """Run the API server (optionally with bot reference for live data)."""
    import uvicorn

    if bot is not None:
        logger.info("Starting API server with bot attached (live data mode)")
    else:
        logger.info("Starting API server in standalone mode (no bot attached)")

    server = BotAPIServer(bot=bot, config=config, db=db)
    app = server.create_app()

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        ws_ping_interval=30,
        ws_ping_timeout=10,
    )


if __name__ == "__main__":
    run_api_server()
