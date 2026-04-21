"""
Hyperliquid exchange client wrapper.

Provides a clean, unified interface for:
  - Placing / cancelling orders
  - Querying account balance, positions, open orders
  - Fetching historical OHLCV candles
  - WebSocket subscription for real-time candle data

Supports both testnet (paper) and mainnet (live) via config.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

import aiohttp
import websockets
from loguru import logger

from config import ExchangeConfig, TradingMode
from utils.helpers import retry


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(str, Enum):
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class OrderResult:
    """Result returned after placing an order."""
    success: bool = False
    order_id: str = ""
    status: str = ""
    error: str = ""
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class Position:
    """Current open position."""
    coin: str = ""
    side: str = ""        # "long" or "short"
    size: float = 0.0
    entry_price: float = 0.0
    unrealized_pnl: float = 0.0
    leverage: int = 1
    liquidation_price: Optional[float] = None


@dataclass
class AccountBalance:
    """Account equity / balance information."""
    total_equity: float = 0.0
    available_balance: float = 0.0
    margin_used: float = 0.0
    unrealized_pnl: float = 0.0


@dataclass
class Candle:
    """OHLCV candle."""
    timestamp: int    # ms
    open: float
    high: float
    low: float
    close: float
    volume: float


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class HyperliquidClient:
    """
    Async wrapper around the Hyperliquid SDK / REST API.

    Uses aiohttp for REST calls and websockets for streaming.
    """

    def __init__(self, config: ExchangeConfig) -> None:
        self._config = config
        self._base_url = config.base_url
        self._ws_url = config.ws_url
        self._session: Optional[aiohttp.ClientSession] = None
        self._private_key = config.wallet_private_key
        self._is_testnet = config.trading_mode == TradingMode.PAPER

        # SDK client (lazy import to avoid issues when key is not set)
        self._sdk_info: Any = None
        self._sdk_exchange: Any = None

    # -- Session management ----------------------------------------------

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                base_url=self._base_url,
                timeout=aiohttp.ClientTimeout(total=30),
            )
        return self._session

    async def close(self) -> None:
        """Close the aiohttp session and SDK connections."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        logger.debug("Hyperliquid client closed")

    # -- REST helpers ----------------------------------------------------

    async def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST to the Hyperliquid API."""
        session = await self._get_session()
        url = f"{self._base_url}{endpoint}"
        try:
            async with session.post(url, json=payload) as resp:
                content_type = resp.headers.get("Content-Type", "")
                if resp.status != 200:
                    # Testnet sometimes returns non-JSON responses (text/plain)
                    if "text/plain" in content_type:
                        logger.warning("API {} returned {} (non-JSON), skipping", endpoint, resp.status)
                        return {}
                    text = await resp.text()
                    logger.error("API error {} on {}: {}", resp.status, endpoint, text)
                    return {}
                data = await resp.json()
                return data
        except aiohttp.ContentTypeError:
            logger.warning("API {} returned non-JSON response, skipping", endpoint)
            return {}
        except aiohttp.ClientError as exc:
            logger.error("HTTP error on {}: {}", endpoint, exc)
            raise

    async def _get(self, endpoint: str, params: Optional[dict] = None) -> dict[str, Any]:
        """GET from the Hyperliquid API."""
        session = await self._get_session()
        url = f"{self._base_url}{endpoint}"
        try:
            async with session.get(url, params=params) as resp:
                content_type = resp.headers.get("Content-Type", "")
                if resp.status != 200:
                    if "text/plain" in content_type:
                        logger.warning("API {} returned {} (non-JSON), skipping", endpoint, resp.status)
                        return {}
                    text = await resp.text()
                    logger.error("API error {} on {}: {}", resp.status, endpoint, text)
                    return {}
                data = await resp.json()
                return data
        except aiohttp.ContentTypeError:
            logger.warning("API {} returned non-JSON response, skipping", endpoint)
            return {}
        except aiohttp.ClientError as exc:
            logger.error("HTTP error on {}: {}", endpoint, exc)
            raise

    # -- SDK initialization (private key required for orders) ------------

    def _init_sdk(self) -> None:
        """Lazily initialize the hyperliquid-python-sdk."""
        if self._sdk_info is not None:
            return
        try:
            from hyperliquid.info import Info as HlInfo
            from hyperliquid.exchange import Exchange as HlExchange
            from hyperliquid.utils import constants as hl_c

            if self._is_testnet:
                base_url = self._config.testnet_base_url
            else:
                base_url = self._config.mainnet_base_url

            self._sdk_info = HlInfo(base_url, skip_ws=True)

            if self._private_key:
                self._sdk_exchange = HlExchange(
                    self._private_key,
                    base_url,
                    hl_c.TESTNET_API_URL if self._is_testnet else hl_c.MAINNET_API_URL,
                )
                logger.info("Hyperliquid SDK initialised ({} mode)", self._config.trading_mode.value)
            else:
                logger.warning("No private key set — order functions will be limited")
        except ImportError:
            logger.error("hyperliquid-python-sdk not installed. Install it with: pip install hyperliquid-python-sdk")
            raise

    # -- Order management ------------------------------------------------

    async def place_order(
        self,
        coin: str,
        side: OrderSide,
        size: float,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        reduce_only: bool = False,
    ) -> OrderResult:
        """
        Place an order on Hyperliquid.

        Args:
            coin: Trading pair (e.g. "BTC", "ETH").
            side: BUY or SELL.
            size: Position size (in coin units).
            order_type: market or limit.
            price: Limit price (required for limit orders).
            stop_loss: Stop-loss price (placed as a trigger order).
            take_profit: Take-profit price (placed as a trigger order).
            reduce_only: Whether this order reduces an existing position.

        Returns:
            OrderResult with status details.
        """
        self._init_sdk()

        if self._sdk_exchange is None:
            return OrderResult(success=False, error="No private key configured")

        try:
            # Build order
            is_buy = side == OrderSide.BUY
            order_params: dict[str, Any] = {
                "coin": coin,
                "is_buy": is_buy,
                "sz": str(size),
                "reduce_only": reduce_only,
                "order_type": {"limit": {"tps": "ioc"} if order_type == OrderType.MARKET else {"limit": {"px": str(price)}}},
            }

            # Place main order via SDK
            result = await asyncio.to_thread(
                self._sdk_exchange.order,
                order_params["coin"],
                order_params["is_buy"],
                order_params["sz"],
                order_params["order_type"],
                order_params["reduce_only"],
            )

            # Parse SDK response
            if isinstance(result, dict) and result.get("status") == "ok":
                order_id = ""
                if "response" in result and "data" in result["response"]:
                    order_info = result["response"]["data"]
                    if "statuses" in order_info:
                        order_id = str(order_info["statuses"][0])
                logger.info(
                    "Order placed: {} {} {} {} (id={})",
                    side.value, size, coin, order_type.value, order_id,
                )

                # Place SL/TP if specified
                if stop_loss is not None:
                    await self._place_trigger_order(coin, not is_buy, size, stop_loss, "stop")
                if take_profit is not None:
                    await self._place_trigger_order(coin, not is_buy, size, take_profit, "take_profit")

                return OrderResult(success=True, order_id=order_id, status="placed", raw_response=result)
            else:
                error_msg = str(result) if result else "Unknown error"
                logger.error("Order failed: {}", error_msg)
                return OrderResult(success=False, error=error_msg, raw_response=result)

        except Exception as exc:
            logger.error("Exception placing order: {}", exc)
            return OrderResult(success=False, error=str(exc))

    async def _place_trigger_order(
        self, coin: str, is_buy: bool, size: float, trigger_price: float, trigger_type: str
    ) -> None:
        """Place a trigger (SL/TP) order via the SDK."""
        if self._sdk_exchange is None:
            return
        try:
            order_type = {
                "trigger": {"triggerPx": str(trigger_price), "isMarket": True, "tpSl": trigger_type}
            }
            await asyncio.to_thread(
                self._sdk_exchange.order, coin, is_buy, str(size), order_type, False
            )
            logger.debug("Trigger order placed: {} {} at {} ({})", coin, size, trigger_price, trigger_type)
        except Exception as exc:
            logger.error("Failed to place trigger order: {}", exc)

    async def cancel_order(self, coin: str, order_id: str) -> bool:
        """
        Cancel an open order.

        Returns:
            True if cancellation was successful.
        """
        self._init_sdk()
        if self._sdk_exchange is None:
            return False
        try:
            result = await asyncio.to_thread(self._sdk_exchange.cancel, coin, order_id)
            success = isinstance(result, dict) and result.get("status") == "ok"
            if success:
                logger.info("Order cancelled: {} id={}", coin, order_id)
            else:
                logger.error("Cancel failed: {} id={} → {}", coin, order_id, result)
            return success
        except Exception as exc:
            logger.error("Exception cancelling order: {}", exc)
            return False

    async def cancel_all_orders(self, coin: str) -> bool:
        """Cancel all open orders for a coin."""
        self._init_sdk()
        if self._sdk_exchange is None:
            return False
        try:
            result = await asyncio.to_thread(self._sdk_exchange.cancel_all, coin)
            success = isinstance(result, dict) and result.get("status") == "ok"
            logger.info("All orders cancelled for {}: {}", coin, "ok" if success else "failed")
            return success
        except Exception as exc:
            logger.error("Exception cancelling all orders for {}: {}", coin, exc)
            return False

    # -- Account queries -------------------------------------------------

    async def get_balance(self) -> AccountBalance:
        """
        Get account equity and available balance.

        Returns AccountBalance with values in USD.
        """
        self._init_sdk()
        try:
            # Use REST info endpoint
            data = await self._post("/info", {"type": "clearinghouseState"})
            if "value" in data and len(data["value"]) > 0:
                state = data["value"][0]
                return AccountBalance(
                    total_equity=float(state.get("totalNtlPos", 0) + state.get("totalRawUsd", 0)),
                    available_balance=float(state.get("withdrawable", 0)),
                    margin_used=float(state.get("totalNtlPos", 0)),
                    unrealized_pnl=float(state.get("totalUnrealizedPnl", 0)),
                )

            # Fallback: use SDK user state
            if self._sdk_info:
                state = await asyncio.to_thread(self._sdk_info.user_state, self._config.wallet_address)
                if state:
                    return AccountBalance(
                        total_equity=float(state.get("accountValue", 0)),
                        available_balance=float(state.get("withdrawable", 0)),
                        margin_used=float(state.get("marginUsed", 0)),
                        unrealized_pnl=float(state.get("unrealizedPnl", 0)),
                    )
        except Exception as exc:
            logger.error("Error fetching balance: {}", exc)

        return AccountBalance()

    async def get_positions(self) -> list[Position]:
        """Get all open positions."""
        self._init_sdk()
        positions: list[Position] = []
        try:
            data = await self._post("/info", {"type": "clearinghouseState"})
            if "value" in data and len(data["value"]) > 0:
                asset_positions = data["value"][0].get("assetPositions", [])
                for ap in asset_positions:
                    position = ap.get("position", {})
                    coin = position.get("coin", "")
                    size = float(position.get("szi", 0))
                    if size == 0:
                        continue
                    positions.append(Position(
                        coin=coin,
                        side="long" if size > 0 else "short",
                        size=abs(size),
                        entry_price=float(position.get("entryPx", 0)),
                        unrealized_pnl=float(position.get("unrealizedPnl", 0)),
                        leverage=int(position.get("leverage", 1)),
                        liquidation_price=float(position.get("liquidationPx", 0)) if position.get("liquidationPx") else None,
                    ))
        except Exception as exc:
            logger.error("Error fetching positions: {}", exc)
        return positions

    async def get_open_orders(self, coin: Optional[str] = None) -> list[dict[str, Any]]:
        """
        Get open orders, optionally filtered by coin.

        Returns list of raw order dicts.
        """
        self._init_sdk()
        try:
            payload: dict[str, Any] = {"type": "openOrders"}
            if coin:
                payload["coin"] = coin
            data = await self._post("/info", payload)
            return data if isinstance(data, list) else []
        except Exception as exc:
            logger.error("Error fetching open orders: {}", exc)
            return []

    # -- Market data -----------------------------------------------------

    async def get_ohlcv(
        self,
        coin: str,
        timeframe: str = "1h",
        limit: int = 500,
        end_time: Optional[int] = None,
    ) -> list[Candle]:
        """
        Fetch historical OHLCV candles.

        Args:
            coin: Trading pair (e.g. "BTC").
            timeframe: Candle interval (e.g. "1m", "5m", "15m", "1h", "4h", "1d").
            limit: Number of candles to fetch.
            end_time: End timestamp in ms (defaults to now).

        Returns:
            List of Candle objects, oldest first.
        """
        self._init_sdk()
        try:
            # Map timeframe to Hyperliquid bar name
            bar_map = {
                "1m": "1m", "5m": "5m", "15m": "15m",
                "1h": "1h", "4h": "4h", "1d": "1d",
            }
            bar = bar_map.get(timeframe, "1h")

            # Use SDK historical OHLCV
            if self._sdk_info:
                hist_candles = await asyncio.to_thread(
                    self._sdk_info.candles_snapshot, coin, bar, limit, end_time
                )
                if hist_candles:
                    result = []
                    for c in hist_candles:
                        result.append(Candle(
                            timestamp=int(c.get("t", 0)),
                            open=float(c.get("o", 0)),
                            high=float(c.get("h", 0)),
                            low=float(c.get("l", 0)),
                            close=float(c.get("c", 0)),
                            volume=float(c.get("v", 0)),
                        ))
                    result.sort(key=lambda x: x.timestamp)
                    return result

            # Fallback: REST approach
            payload = {
                "type": "candleSnapshot",
                "req": {"coin": coin, "interval": bar, "startTime": end_time or int(time.time() * 1000)},
            }
            data = await self._post("/info", payload)
            candles: list[Candle] = []
            for c in data if isinstance(data, list) else []:
                candles.append(Candle(
                    timestamp=int(c.get("t", 0)),
                    open=float(c.get("o", 0)),
                    high=float(c.get("h", 0)),
                    low=float(c.get("l", 0)),
                    close=float(c.get("c", 0)),
                    volume=float(c.get("v", 0)),
                ))
            candles.sort(key=lambda x: x.timestamp)
            return candles

        except Exception as exc:
            logger.error("Error fetching OHLCV for {}: {}", coin, exc)
            return []

    async def get_midpoint(self, coin: str) -> Optional[float]:
        """Get the current mid-price for a coin."""
        try:
            data = await self._post("/info", {"type": "allMids"})
            if isinstance(data, dict) and coin in data:
                return float(data[coin])
        except Exception as exc:
            logger.error("Error fetching midpoint for {}: {}", coin, exc)
        return None

    async def get_funding_rate(self, coin: str) -> Optional[float]:
        """Get the current funding rate for a coin."""
        try:
            data = await self._post("/info", {"type": "fundingHistory", "coin": coin})
            if isinstance(data, list) and len(data) > 0:
                return float(data[0].get("fundingRate", 0))
        except Exception as exc:
            logger.error("Error fetching funding rate for {}: {}", coin, exc)
        return None

    # -- WebSocket subscription ------------------------------------------

    async def subscribe_candles(
        self,
        coin: str,
        timeframe: str,
        callback: Callable[[Candle], None],
    ) -> None:
        """
        Subscribe to real-time OHLCV candles via WebSocket.

        Args:
            coin: Trading pair (e.g. "BTC").
            timeframe: Candle interval.
            callback: Function called with each new candle.
        """
        bar_map = {
            "1m": "1m", "5m": "5m", "15m": "15m",
            "1h": "1h", "4h": "4h", "1d": "1d",
        }
        bar = bar_map.get(timeframe, "1h")
        subscription_msg = {
            "method": "subscribe",
            "subscription": {
                "type": "candle",
                "coin": coin,
                "interval": bar,
            },
        }

        ws_url = self._ws_url
        reconnect_delay = self._config.ws_reconnect_delay_sec if hasattr(self._config, "ws_reconnect_delay_sec") else 5.0

        while True:
            try:
                async with websockets.connect(ws_url, ping_interval=30) as ws:
                    await ws.send(json.dumps(subscription_msg))
                    logger.info("WS subscribed to {} {} candles", coin, timeframe)

                    async for message in ws:
                        data = json.loads(message)
                        if data.get("channel") == "candle":
                            candle_data = data.get("data", [{}])[0] if isinstance(data.get("data"), list) else data.get("data", {})
                            if candle_data:
                                candle = Candle(
                                    timestamp=int(candle_data.get("t", 0)),
                                    open=float(candle_data.get("o", 0)),
                                    high=float(candle_data.get("h", 0)),
                                    low=float(candle_data.get("l", 0)),
                                    close=float(candle_data.get("c", 0)),
                                    volume=float(candle_data.get("v", 0)),
                                )
                                callback(candle)

            except websockets.exceptions.ConnectionClosed:
                logger.warning("WS disconnected, reconnecting in {}s...", reconnect_delay)
                await asyncio.sleep(reconnect_delay)
            except Exception as exc:
                logger.error("WS error for {} {}: {}", coin, timeframe, exc)
                await asyncio.sleep(reconnect_delay)
