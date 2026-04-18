"""
Strategy 2: MACD + Bollinger Bands + RSI

Triple-confirmation strategy that combines:
  - MACD histogram crossover for momentum shift
  - Bollinger Band squeeze / expansion for volatility context
  - RSI for overbought/oversold filtering

Logic:
  - LONG:  MACD histogram crosses above zero + price near lower BB + RSI < 50
  - SHORT: MACD histogram crosses below zero + price near upper BB + RSI > 50
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from indicators.technical import bollinger_bands, macd, rsi, atr
from strategies.base import BaseStrategy, Signal


class MACDBBRSIStrategy(BaseStrategy):
    """
    MACD + Bollinger Bands + RSI strategy.

    Parameters (with defaults):
        macd_fast:     MACD fast EMA period (default 12)
        macd_slow:     MACD slow EMA period (default 26)
        macd_signal:   MACD signal period (default 9)
        bb_period:     Bollinger Band period (default 20)
        bb_std:        Bollinger Band standard deviations (default 2.0)
        rsi_period:    RSI period (default 14)
        bb_zone:       Fraction of BB width to consider "near band" (default 0.20)
    """

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        super().__init__(params)
        self._params.setdefault("macd_fast", 12)
        self._params.setdefault("macd_slow", 26)
        self._params.setdefault("macd_signal", 9)
        self._params.setdefault("bb_period", 20)
        self._params.setdefault("bb_std", 2.0)
        self._params.setdefault("rsi_period", 14)
        self._params.setdefault("bb_zone", 0.20)

    @property
    def name(self) -> str:
        return "MACD_BB_RSI"

    def get_param_ranges(self) -> dict[str, tuple[float, float]]:
        return {
            "macd_fast": (5, 20),
            "macd_slow": (20, 50),
            "macd_signal": (5, 15),
            "bb_period": (10, 40),
            "bb_std": (1.0, 3.5),
            "rsi_period": (7, 28),
            "bb_zone": (0.05, 0.40),
        }

    def required_candle_count(self) -> int:
        return max(
            self._params["macd_slow"] + self._params["macd_signal"] + 10,
            self._params["bb_period"] + 10,
            100,
        )

    def calculate_signals(self, df: pd.DataFrame) -> list[Signal]:
        """
        Generate signals based on MACD + BB + RSI triple confirmation.

        Args:
            df: OHLCV DataFrame.

        Returns:
            List of Signal objects (most recent candle only).
        """
        if len(df) < self.required_candle_count():
            return []

        p = self._params
        h, l, c = df["high"], df["low"], df["close"]

        # Compute indicators
        macd_line, macd_signal, macd_hist = macd(c, int(p["macd_fast"]),
                                                  int(p["macd_slow"]),
                                                  int(p["macd_signal"]))
        bb_upper, bb_middle, bb_lower = bollinger_bands(c, int(p["bb_period"]), p["bb_std"])
        rsi_val = rsi(c, int(p["rsi_period"]))
        atr_val = atr(h, l, c, 14)

        if len(df) < 2:
            return []

        latest = len(df) - 1
        prev = latest - 1

        if (pd.isna(macd_hist.iloc[latest]) or pd.isna(macd_hist.iloc[prev])
                or pd.isna(bb_lower.iloc[latest]) or pd.isna(bb_upper.iloc[latest])
                or pd.isna(rsi_val.iloc[latest]) or pd.isna(atr_val.iloc[latest])):
            return []

        close_price = float(c.iloc[latest])
        atr_value = float(atr_val.iloc[latest])
        bb_width = float(bb_upper.iloc[latest] - bb_lower.iloc[latest])
        bb_zone_threshold = bb_width * p["bb_zone"]

        hist_now = float(macd_hist.iloc[latest])
        hist_prev = float(macd_hist.iloc[prev])
        rsi_now = float(rsi_val.iloc[latest])
        bb_lower_val = float(bb_lower.iloc[latest])
        bb_upper_val = float(bb_upper.iloc[latest])

        # Distance from bands
        dist_to_lower = close_price - bb_lower_val
        dist_to_upper = bb_upper_val - close_price

        signals: list[Signal] = []

        # --- LONG: MACD hist crosses above 0 + price near lower BB + RSI < 50 ---
        macd_cross_up = hist_prev < 0 and hist_now >= 0
        near_lower = dist_to_lower < bb_zone_threshold
        rsi_bullish = rsi_now < 50

        if macd_cross_up and near_lower and rsi_bullish:
            confidence = self._compute_confidence(hist_now, rsi_now, dist_to_lower, bb_zone_threshold, "long")
            stop_loss = close_price - 1.5 * atr_value
            take_profit = close_price + 3.0 * atr_value

            signals.append(Signal(
                pair=str(df["pair"].iloc[0]) if "pair" in df.columns else "",
                strategy=self.name,
                direction="long",
                entry_price=close_price,
                stop_loss=round(stop_loss, 6),
                take_profit=round(take_profit, 6),
                confidence=confidence,
                metadata={"macd_hist": hist_now, "rsi": rsi_now, "dist_lower": dist_to_lower},
            ))

        # --- SHORT: MACD hist crosses below 0 + price near upper BB + RSI > 50 ---
        macd_cross_down = hist_prev > 0 and hist_now <= 0
        near_upper = dist_to_upper < bb_zone_threshold
        rsi_bearish = rsi_now > 50

        if macd_cross_down and near_upper and rsi_bearish:
            confidence = self._compute_confidence(hist_now, rsi_now, dist_to_upper, bb_zone_threshold, "short")
            stop_loss = close_price + 1.5 * atr_value
            take_profit = close_price - 3.0 * atr_value

            signals.append(Signal(
                pair=str(df["pair"].iloc[0]) if "pair" in df.columns else "",
                strategy=self.name,
                direction="short",
                entry_price=close_price,
                stop_loss=round(stop_loss, 6),
                take_profit=round(take_profit, 6),
                confidence=confidence,
                metadata={"macd_hist": hist_now, "rsi": rsi_now, "dist_upper": dist_to_upper},
            ))

        return signals

    @staticmethod
    def _compute_confidence(
        hist: float, rsi_val: float, dist: float, threshold: float, direction: str
    ) -> float:
        """Compute confidence in [0.3, 0.95]."""
        # MACD strength
        macd_score = min(abs(hist) / 0.5, 1.0) * 0.3

        # RSI score: further from 50 is better
        if direction == "long":
            rsi_score = max(0, (50 - rsi_val) / 50) * 0.35
        else:
            rsi_score = max(0, (rsi_val - 50) / 50) * 0.35

        # Band proximity score
        band_score = max(0, (threshold - dist) / threshold) * 0.35 if threshold > 0 else 0

        return round(min(0.3 + macd_score + rsi_score + band_score, 0.95), 4)
