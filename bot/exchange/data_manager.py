"""
OHLCV data pipeline manager.

Combines REST historical fetching, WebSocket real-time streaming, and
SQLite storage to provide strategies with up-to-date candle data.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import pandas as pd
from loguru import logger

from config import DataConfig
from exchange.hyperliquid_client import Candle, HyperliquidClient
from models.database import Database
from utils.helpers import timestamp_ms


class DataManager:
    """
    Manages OHLCV data fetching, storage, and retrieval.

    - Fetches historical candles from Hyperliquid REST API
    - Stores candles in SQLite for persistence and backtesting
    - Subscribes to real-time candle updates via WebSocket
    - Provides candles as pandas DataFrames for strategy consumption
    """

    def __init__(
        self,
        client: HyperliquidClient,
        db: Database,
        config: DataConfig,
    ) -> None:
        self._client = client
        self._db = db
        self._config = config
        self._ws_tasks: list[asyncio.Task] = []
        self._callbacks: dict[str, list[Callable[[Candle], None]]] = {}
        self._subscribed_pairs: set[str] = set()

    # -- Public API ------------------------------------------------------

    async def start(self) -> None:
        """Start the data pipeline (WebSocket subscriptions)."""
        logger.info("Data manager started")

    async def stop(self) -> None:
        """Stop all WebSocket subscriptions."""
        for task in self._ws_tasks:
            task.cancel()
        self._ws_tasks.clear()
        logger.info("Data manager stopped")

    async def fetch_and_store(
        self,
        pair: str,
        timeframe: str = "1h",
        limit: int = 500,
    ) -> int:
        """
        Fetch historical candles from the exchange and store them in the database.

        Returns the number of new candles stored.
        """
        logger.debug("Fetching {} {} candles (limit={})", pair, timeframe, limit)
        candles = await self._client.get_ohlcv(pair, timeframe, limit)
        if not candles:
            logger.warning("No candles returned for {} {}", pair, timeframe)
            return 0

        # Convert to dict format for DB insertion
        candle_dicts = [
            {
                "pair": pair,
                "timeframe": timeframe,
                "timestamp": c.timestamp,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in candles
        ]

        count = self._db.insert_candles(candle_dicts)
        logger.info(
            "Stored {} new candles for {} {} (total fetched: {})",
            count, pair, timeframe, len(candles),
        )
        return count

    def get_candles_df(
        self,
        pair: str,
        timeframe: str = "1h",
        limit: int = 500,
    ) -> pd.DataFrame:
        """
        Get candles as a pandas DataFrame for strategy consumption.

        Returns a DataFrame sorted by timestamp (ascending) with columns:
        open, high, low, close, volume, timestamp.
        """
        rows = self._db.get_candles(pair, timeframe, limit)
        if not rows:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "timestamp"])

        df = pd.DataFrame(rows)
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Ensure numeric types
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    def on_candle(self, pair: str, callback: Callable[[Candle], None]) -> None:
        """Register a callback for real-time candle updates."""
        if pair not in self._callbacks:
            self._callbacks[pair] = []
        self._callbacks[pair].append(callback)

    async def subscribe(
        self,
        pair: str,
        timeframe: str = "1h",
    ) -> None:
        """
        Subscribe to real-time candle updates for a pair via WebSocket.

        New candles are automatically stored in the database and
        dispatched to registered callbacks.
        """
        key = f"{pair}:{timeframe}"
        if key in self._subscribed_pairs:
            logger.debug("Already subscribed to {}", key)
            return

        async def _ws_handler(candle: Candle) -> None:
            # Store in DB
            self._db.insert_candles([{
                "pair": pair,
                "timeframe": timeframe,
                "timestamp": candle.timestamp,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
            }])
            # Dispatch to callbacks
            for cb in self._callbacks.get(pair, []):
                try:
                    cb(candle)
                except Exception as exc:
                    logger.error("Candle callback error: {}", exc)

        task = asyncio.create_task(
            self._client.subscribe_candles(pair, timeframe, _ws_handler),
            name=f"ws-{pair}-{timeframe}",
        )
        self._ws_tasks.append(task)
        self._subscribed_pairs.add(key)
        logger.info("Subscribed to real-time {} {} candles", pair, timeframe)

    def unsubscribe(self, pair: str, timeframe: str = "1h") -> None:
        """Unsubscribe from real-time candle updates (cancels the WS task)."""
        key = f"{pair}:{timeframe}"
        for task in self._ws_tasks:
            if task.get_name() == f"ws-{pair}-{timeframe}":
                task.cancel()
                self._ws_tasks.remove(task)
                break
        self._subscribed_pairs.discard(key)
        logger.info("Unsubscribed from {} {}", pair, timeframe)

    # -- Maintenance -----------------------------------------------------

    def purge_old_candles(self) -> int:
        """Remove candles older than the configured retention period."""
        count = self._db.purge_old_candles(self._config.candles_retention_days)
        if count > 0:
            logger.info("Purged {} old candles", count)
        return count
