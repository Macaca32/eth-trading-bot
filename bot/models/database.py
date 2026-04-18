"""
SQLite database models for the trading bot.

Tables:
  - candles   : OHLCV data for backtesting and indicators
  - trades    : Executed trade records
  - signals   : Generated strategy signals
  - optimizations: Optuna optimization results

Uses raw sqlite3 (stdlib) to avoid additional dependencies.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, Optional

from loguru import logger

# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS candles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pair        TEXT    NOT NULL,
    timeframe   TEXT    NOT NULL,
    timestamp   INTEGER NOT NULL,
    open        REAL    NOT NULL,
    high        REAL    NOT NULL,
    low         REAL    NOT NULL,
    close       REAL    NOT NULL,
    volume      REAL    NOT NULL,
    UNIQUE(pair, timeframe, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_candles_pair_tf_ts
    ON candles(pair, timeframe, timestamp);

CREATE TABLE IF NOT EXISTS trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pair            TEXT    NOT NULL,
    strategy        TEXT    NOT NULL,
    direction       TEXT    NOT NULL,  -- 'long' or 'short'
    entry_price     REAL    NOT NULL,
    exit_price      REAL,
    pnl             REAL,
    fee             REAL    DEFAULT 0.0,
    quantity        REAL,
    status          TEXT    DEFAULT 'open',  -- 'open', 'closed'
    entry_timestamp INTEGER,
    exit_timestamp  INTEGER
);

CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);

CREATE TABLE IF NOT EXISTS signals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pair            TEXT    NOT NULL,
    strategy        TEXT    NOT NULL,
    direction       TEXT    NOT NULL,
    confidence      REAL,
    entry_price     REAL,
    stop_loss       REAL,
    take_profit     REAL,
    timestamp       INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_signals_pair_ts
    ON signals(pair, timestamp);

CREATE TABLE IF NOT EXISTS optimizations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy    TEXT    NOT NULL,
    params_json TEXT    NOT NULL,
    sharpe      REAL,
    max_drawdown REAL,
    total_return REAL,
    n_trades    INTEGER,
    timestamp   INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_optimizations_strategy
    ON optimizations(strategy);
"""


# ---------------------------------------------------------------------------
# Database wrapper
# ---------------------------------------------------------------------------

class Database:
    """
    Thin wrapper around sqlite3 that provides connection management
    and convenient CRUD methods for each table.
    """

    def __init__(self, db_path: str = "data/bot.db") -> None:
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    # -- Connection management -------------------------------------------

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield a sqlite3 connection with row factory enabled."""
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self.connection() as conn:
            conn.executescript(_SCHEMA)
        logger.debug("Database schema verified at {}", self._db_path)

    # -- Candle methods --------------------------------------------------

    def insert_candles(self, candles: list[dict[str, Any]]) -> int:
        """Bulk-insert candles. Returns number of rows inserted."""
        if not candles:
            return 0
        sql = (
            "INSERT OR IGNORE INTO candles "
            "(pair, timeframe, timestamp, open, high, low, close, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        )
        rows = [
            (c["pair"], c["timeframe"], c["timestamp"],
             c["open"], c["high"], c["low"], c["close"], c["volume"])
            for c in candles
        ]
        with self.connection() as conn:
            cursor = conn.executemany(sql, rows)
            return cursor.rowcount

    def get_candles(
        self,
        pair: str,
        timeframe: str,
        limit: int = 500,
        end_ts: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """Fetch candles for a pair/timeframe, most recent first up to *limit*."""
        sql = (
            "SELECT pair, timeframe, timestamp, open, high, low, close, volume "
            "FROM candles "
            "WHERE pair = ? AND timeframe = ? "
        )
        params: list[Any] = [pair, timeframe]
        if end_ts is not None:
            sql += "AND timestamp <= ? "
            params.append(end_ts)
        sql += "ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        with self.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def purge_old_candles(self, retention_days: int = 90) -> int:
        """Delete candles older than *retention_days*. Returns count deleted."""
        cutoff = int(datetime.now(timezone.utc).timestamp() * 1000) - (retention_days * 86400 * 1000)
        sql = "DELETE FROM candles WHERE timestamp < ?"
        with self.connection() as conn:
            cursor = conn.execute(sql, (cutoff,))
            return cursor.rowcount

    # -- Trade methods ---------------------------------------------------

    def insert_trade(self, trade: dict[str, Any]) -> int:
        """Insert a single trade record and return its id."""
        sql = (
            "INSERT INTO trades "
            "(pair, strategy, direction, entry_price, exit_price, pnl, fee, "
            "quantity, status, entry_timestamp, exit_timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        params = (
            trade["pair"], trade["strategy"], trade["direction"],
            trade.get("entry_price"), trade.get("exit_price"),
            trade.get("pnl"), trade.get("fee", 0.0),
            trade.get("quantity"), trade.get("status", "open"),
            trade.get("entry_timestamp"), trade.get("exit_timestamp"),
        )
        with self.connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.lastrowid  # type: ignore[return-value]

    def update_trade(self, trade_id: int, updates: dict[str, Any]) -> None:
        """Update fields on an existing trade by id."""
        if not updates:
            return
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [trade_id]
        sql = f"UPDATE trades SET {set_clause} WHERE id = ?"
        with self.connection() as conn:
            conn.execute(sql, values)

    def get_open_trades(self) -> list[dict[str, Any]]:
        """Return all trades with status 'open'."""
        sql = "SELECT * FROM trades WHERE status = 'open'"
        with self.connection() as conn:
            rows = conn.execute(sql).fetchall()
            return [dict(r) for r in rows]

    def get_recent_trades(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return the most recently closed trades."""
        sql = (
            "SELECT * FROM trades WHERE status = 'closed' "
            "ORDER BY exit_timestamp DESC LIMIT ?"
        )
        with self.connection() as conn:
            rows = conn.execute(sql, (limit,)).fetchall()
            return [dict(r) for r in rows]

    def get_daily_pnl(self) -> float:
        """Return total PnL for trades closed today (UTC)."""
        today_start = int(
            datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            .timestamp() * 1000
        )
        sql = "SELECT COALESCE(SUM(pnl), 0) FROM trades WHERE status='closed' AND exit_timestamp >= ?"
        with self.connection() as conn:
            row = conn.execute(sql, (today_start,)).fetchone()
            return float(row[0])

    def get_consecutive_losses(self) -> int:
        """Count consecutive losing trades (most recent first)."""
        sql = (
            "SELECT pnl FROM trades WHERE status='closed' AND pnl IS NOT NULL "
            "ORDER BY exit_timestamp DESC"
        )
        with self.connection() as conn:
            rows = conn.execute(sql).fetchall()
        count = 0
        for row in rows:
            if row["pnl"] < 0:
                count += 1
            else:
                break
        return count

    # -- Signal methods --------------------------------------------------

    def insert_signal(self, signal: dict[str, Any]) -> int:
        """Insert a strategy signal and return its id."""
        sql = (
            "INSERT INTO signals "
            "(pair, strategy, direction, confidence, entry_price, stop_loss, "
            "take_profit, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        )
        params = (
            signal["pair"], signal["strategy"], signal["direction"],
            signal.get("confidence"), signal.get("entry_price"),
            signal.get("stop_loss"), signal.get("take_profit"),
            signal["timestamp"],
        )
        with self.connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.lastrowid  # type: ignore[return-value]

    def get_recent_signals(
        self,
        pair: Optional[str] = None,
        strategy: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch recent signals, optionally filtered by pair/strategy."""
        sql = "SELECT * FROM signals WHERE 1=1"
        params: list[Any] = []
        if pair:
            sql += " AND pair = ?"
            params.append(pair)
        if strategy:
            sql += " AND strategy = ?"
            params.append(strategy)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        with self.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    # -- Optimization methods --------------------------------------------

    def save_optimization(self, opt: dict[str, Any]) -> int:
        """Save an optimization result and return its id."""
        sql = (
            "INSERT INTO optimizations "
            "(strategy, params_json, sharpe, max_drawdown, total_return, n_trades, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)"
        )
        params = (
            opt["strategy"], json.dumps(opt["params"]),
            opt.get("sharpe"), opt.get("max_drawdown"),
            opt.get("total_return"), opt.get("n_trades"),
            opt["timestamp"],
        )
        with self.connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.lastrowid  # type: ignore[return-value]

    def get_best_optimization(self, strategy: str) -> Optional[dict[str, Any]]:
        """Return the best optimization result for a strategy (highest Sharpe)."""
        sql = (
            "SELECT * FROM optimizations "
            "WHERE strategy = ? ORDER BY sharpe DESC LIMIT 1"
        )
        with self.connection() as conn:
            row = conn.execute(sql, (strategy,)).fetchone()
            if row is None:
                return None
            result = dict(row)
            result["params"] = json.loads(result["params_json"])
            return result
