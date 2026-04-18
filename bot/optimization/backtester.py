"""
Walk-forward backtesting engine.

Simulates strategy execution on historical data with:
  - Walk-forward splits (train/validation windows)
  - Realistic trade simulation (entry at open, SL/TP checks)
  - Performance metrics (Sharpe, drawdown, total return, win rate)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
import pandas as pd
from loguru import logger

from strategies.base import BaseStrategy, Signal


# ---------------------------------------------------------------------------
# Trade simulation
# ---------------------------------------------------------------------------

@dataclass
class SimulatedTrade:
    """A single simulated trade."""
    entry_time: int
    exit_time: int
    direction: str          # "long" or "short"
    entry_price: float
    exit_price: float
    pnl_pct: float          # PnL as percentage of entry
    pnl: float              # Absolute PnL (assuming $1000 per trade)
    holding_bars: int
    signal_confidence: float
    strategy: str


@dataclass
class BacktestResult:
    """Aggregated results from a backtest run."""
    trades: list[SimulatedTrade] = field(default_factory=list)
    total_return_pct: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    win_rate: float = 0.0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    n_splits: int = 1
    split_results: list[dict[str, float]] = field(default_factory=list)


class Backtester:
    """
    Walk-forward backtesting engine.

    Splits historical data into train and validation windows, then
    simulates trades on the validation window using signals from the
    strategy.
    """

    def __init__(
        self,
        train_days: int = 60,
        validation_days: int = 30,
        n_splits: int = 3,
        initial_capital: float = 1000.0,
    ) -> None:
        """
        Args:
            train_days: Number of days in the training window.
            validation_days: Number of days in the validation window.
            n_splits: Number of walk-forward splits.
            initial_capital: Starting capital for PnL calculation.
        """
        self.train_days = train_days
        self.validation_days = validation_days
        self.n_splits = n_splits
        self.initial_capital = initial_capital

    def run(
        self,
        strategy: BaseStrategy,
        df: pd.DataFrame,
    ) -> BacktestResult:
        """
        Run a walk-forward backtest.

        Args:
            strategy: Strategy instance (with params already set).
            df: OHLCV DataFrame sorted by timestamp (ascending).
                Must have 'timestamp' column in milliseconds.

        Returns:
            BacktestResult with aggregated metrics.
        """
        if len(df) < 100:
            logger.warning("Not enough data for backtesting ({} rows)", len(df))
            return BacktestResult()

        # Convert timestamps to datetime for splitting
        if "timestamp" in df.columns:
            df = df.copy()
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
        elif isinstance(df.index, pd.DatetimeIndex):
            df = df.copy()
            df["datetime"] = df.index
        else:
            logger.error("DataFrame must have 'timestamp' column or DatetimeIndex")
            return BacktestResult()

        total_days = (df["datetime"].iloc[-1] - df["datetime"].iloc[0]).days
        if total_days < (self.train_days + self.validation_days):
            logger.warning(
                "Data spans {} days but need at least {}",
                total_days, self.train_days + self.validation_days,
            )
            return BacktestResult()

        step_days = self.validation_days
        all_trades: list[SimulatedTrade] = []
        split_results: list[dict[str, float]] = []

        for split_idx in range(self.n_splits):
            # Calculate window boundaries
            val_end_offset = total_days - split_idx * step_days
            val_start_offset = val_end_offset - self.validation_days
            train_end_offset = val_start_offset

            cutoff_end = df["datetime"].iloc[-1] - pd.Timedelta(days=split_idx * step_days)
            cutoff_start = cutoff_end - pd.Timedelta(days=self.validation_days)
            cutoff_train_start = cutoff_start - pd.Timedelta(days=self.train_days)

            # Split data
            train_df = df[(df["datetime"] >= cutoff_train_start) & (df["datetime"] < cutoff_start)]
            val_df = df[(df["datetime"] >= cutoff_start) & (df["datetime"] < cutoff_end)]

            if len(train_df) < 50 or len(val_df) < 20:
                logger.debug(
                    "Split {}: insufficient data (train={}, val={})",
                    split_idx, len(train_df), len(val_df),
                )
                continue

            # Run simulation on validation window
            split_trades = self._simulate(strategy, val_df)
            all_trades.extend(split_trades)

            # Calculate split metrics
            split_metrics = self._calculate_metrics(split_trades)
            split_metrics["split"] = split_idx
            split_results.append(split_metrics)

            logger.debug(
                "Split {}: {} trades, Sharpe={:.2f}, Return={:.2f}%, DD={:.2f}%",
                split_idx, len(split_trades),
                split_metrics["sharpe_ratio"],
                split_metrics["total_return_pct"],
                split_metrics["max_drawdown_pct"],
            )

        # Aggregate across all splits
        result = self._calculate_metrics(all_trades)
        result.trades = all_trades
        result.total_trades = len(all_trades)
        result.n_splits = max(len(split_results), 1)
        result.split_results = split_results

        logger.info(
            "Backtest complete: {} total trades across {} splits, "
            "Sharpe={:.2f}, Return={:.2f}%, MaxDD={:.2f}%, WinRate={:.1f}%",
            len(all_trades), len(split_results),
            result.sharpe_ratio, result.total_return_pct,
            result.max_drawdown_pct, result.win_rate * 100,
        )

        return result

    def _simulate(
        self,
        strategy: BaseStrategy,
        df: pd.DataFrame,
    ) -> list[SimulatedTrade]:
        """
        Simulate trading on a validation DataFrame.

        Processes each candle, checks for new signals, and manages
        open positions with SL/TP logic.
        """
        trades: list[SimulatedTrade] = []
        open_trade: Optional[dict[str, Any]] = None

        for i in range(len(df)):
            row = df.iloc[i]
            current_close = float(row["close"])
            current_high = float(row["high"])
            current_low = float(row["low"])
            current_ts = int(row.get("timestamp", 0))

            # Check open trade SL/TP
            if open_trade is not None:
                exited = False
                exit_price = current_close

                if open_trade["direction"] == "long":
                    if current_low <= open_trade["stop_loss"]:
                        exit_price = open_trade["stop_loss"]
                        exited = True
                    elif current_high >= open_trade["take_profit"]:
                        exit_price = open_trade["take_profit"]
                        exited = True
                else:  # short
                    if current_high >= open_trade["stop_loss"]:
                        exit_price = open_trade["stop_loss"]
                        exited = True
                    elif current_low <= open_trade["take_profit"]:
                        exit_price = open_trade["take_profit"]
                        exited = True

                if exited:
                    # Record trade
                    entry = open_trade["entry_price"]
                    if open_trade["direction"] == "long":
                        pnl_pct = (exit_price - entry) / entry * 100
                    else:
                        pnl_pct = (entry - exit_price) / entry * 100

                    trades.append(SimulatedTrade(
                        entry_time=open_trade["entry_time"],
                        exit_time=current_ts,
                        direction=open_trade["direction"],
                        entry_price=entry,
                        exit_price=exit_price,
                        pnl_pct=pnl_pct,
                        pnl=pnl_pct / 100 * self.initial_capital,
                        holding_bars=i - open_trade["entry_bar"],
                        signal_confidence=open_trade["confidence"],
                        strategy=open_trade["strategy"],
                    ))
                    open_trade = None

            # Generate signals on the current window
            window = df.iloc[:i + 1]
            if len(window) >= strategy.required_candle_count():
                signals = strategy.calculate_signals(window)
                if signals and open_trade is None:
                    # Take the first signal
                    sig = signals[0]
                    open_trade = {
                        "direction": sig.direction,
                        "entry_price": sig.entry_price if sig.entry_price > 0 else current_close,
                        "stop_loss": sig.stop_loss,
                        "take_profit": sig.take_profit,
                        "entry_time": current_ts,
                        "entry_bar": i,
                        "confidence": sig.confidence,
                        "strategy": sig.strategy,
                    }

        # Close any remaining open trade at the last price
        if open_trade is not None:
            entry = open_trade["entry_price"]
            last_close = float(df.iloc[-1]["close"])
            last_ts = int(df.iloc[-1].get("timestamp", 0))
            if open_trade["direction"] == "long":
                pnl_pct = (last_close - entry) / entry * 100
            else:
                pnl_pct = (entry - last_close) / entry * 100
            trades.append(SimulatedTrade(
                entry_time=open_trade["entry_time"],
                exit_time=last_ts,
                direction=open_trade["direction"],
                entry_price=entry,
                exit_price=last_close,
                pnl_pct=pnl_pct,
                pnl=pnl_pct / 100 * self.initial_capital,
                holding_bars=len(df) - 1 - open_trade["entry_bar"],
                signal_confidence=open_trade["confidence"],
                strategy=open_trade["strategy"],
            ))

        return trades

    @staticmethod
    def _calculate_metrics(trades: list[SimulatedTrade]) -> BacktestResult:
        """Calculate performance metrics from a list of trades."""
        result = BacktestResult()

        if not trades:
            return result

        pnls = [t.pnl_pct for t in trades]
        result.total_trades = len(trades)
        result.total_return_pct = sum(pnls)

        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        result.win_rate = len(wins) / len(pnls) if pnls else 0
        result.avg_win_pct = np.mean(wins) if wins else 0
        result.avg_loss_pct = np.mean(losses) if losses else 0

        # Profit factor
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0.001
        result.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Max drawdown
        cumulative = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = cumulative - running_max
        result.max_drawdown_pct = float(np.min(drawdowns)) if len(drawdowns) > 0 else 0

        # Sharpe ratio (annualised, assuming ~1 trade per day per 100 bars)
        if len(pnls) > 1:
            mean_pnl = np.mean(pnls)
            std_pnl = np.std(pnls, ddof=1)
            if std_pnl > 0:
                result.sharpe_ratio = float(mean_pnl / std_pnl * np.sqrt(252))
            else:
                result.sharpe_ratio = 0.0
        else:
            result.sharpe_ratio = 0.0

        return result
