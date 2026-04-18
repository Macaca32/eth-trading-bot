"""
Strategy 1: StochRSI + Supertrend

Combines the Stochastic RSI oscillator for overbought/oversold conditions
with the Supertrend indicator for trend direction confirmation.

Logic:
  - LONG:  StochRSI-K crosses above D while in oversold zone AND Supertrend is bullish
  - SHORT: StochRSI-K crosses below D while in overbought zone AND Supertrend is bearish
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from indicators.technical import atr, rsi, stochrsi, supertrend
from strategies.base import BaseStrategy, Signal


class StochRSISupertrendStrategy(BaseStrategy):
    """
    StochRSI + Supertrend strategy.

    Parameters (with defaults):
        rsi_period:        RSI lookback (default 14)
        stoch_period:      Stochastic lookback (default 14)
        k_smooth:          %K smoothing (default 3)
        d_smooth:          %D smoothing (default 3)
        st_period:         Supertrend ATR period (default 10)
        st_multiplier:     Supertrend multiplier (default 3.0)
        oversold:          Oversold threshold (default 20)
        overbought:        Overbought threshold (default 80)
    """

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        super().__init__(params)
        # Defaults
        self._params.setdefault("rsi_period", 14)
        self._params.setdefault("stoch_period", 14)
        self._params.setdefault("k_smooth", 3)
        self._params.setdefault("d_smooth", 3)
        self._params.setdefault("st_period", 10)
        self._params.setdefault("st_multiplier", 3.0)
        self._params.setdefault("oversold", 20)
        self._params.setdefault("overbought", 80)

    @property
    def name(self) -> str:
        return "StochRSI_Supertrend"

    def get_param_ranges(self) -> dict[str, tuple[float, float]]:
        return {
            "rsi_period": (5, 30),
            "stoch_period": (5, 30),
            "k_smooth": (1, 7),
            "d_smooth": (1, 7),
            "st_period": (5, 20),
            "st_multiplier": (1.0, 5.0),
            "oversold": (10, 35),
            "overbought": (65, 90),
        }

    def required_candle_count(self) -> int:
        return max(
            self._params["rsi_period"] * 4,
            self._params["stoch_period"] * 4,
            self._params["st_period"] * 3,
            100,
        )

    def calculate_signals(self, df: pd.DataFrame) -> list[Signal]:
        """
        Generate signals based on StochRSI crossovers confirmed by Supertrend.

        Args:
            df: OHLCV DataFrame with columns open, high, low, close, volume.

        Returns:
            List of Signal objects (at most one per candle, most recent only).
        """
        if len(df) < self.required_candle_count():
            return []

        p = self._params
        h, l, c = df["high"], df["low"], df["close"]

        # Compute indicators
        stoch_k, stoch_d = stochrsi(c, p["rsi_period"], p["stoch_period"],
                                     int(p["k_smooth"]), int(p["d_smooth"]))
        st_val, st_dir = supertrend(h, l, c, int(p["st_period"]), p["st_multiplier"])
        atr_val = atr(h, l, c, int(p["st_period"]))

        # We need at least 2 rows for crossover detection
        if len(df) < 2 or stoch_k.isna().all():
            return []

        signals: list[Signal] = []
        latest = len(df) - 1
        prev = latest - 1

        # Skip if key indicator values are NaN
        if (pd.isna(stoch_k.iloc[latest]) or pd.isna(stoch_d.iloc[latest])
                or pd.isna(stoch_k.iloc[prev]) or pd.isna(stoch_d.iloc[prev])
                or pd.isna(st_dir.iloc[latest]) or pd.isna(atr_val.iloc[latest])):
            return []

        close_price = float(c.iloc[latest])
        atr_value = float(atr_val.iloc[latest])

        # --- LONG signal ---
        # StochRSI-K crosses above D in oversold zone + Supertrend bullish
        k_now = float(stoch_k.iloc[latest])
        d_now = float(stoch_d.iloc[latest])
        k_prev = float(stoch_k.iloc[prev])
        d_prev = float(stoch_d.iloc[prev])
        st_now = int(st_dir.iloc[latest])

        oversold = p["oversold"]
        overbought = p["overbought"]

        long_crossover = k_prev <= d_prev and k_now > d_now
        short_crossover = k_prev >= d_prev and k_now < d_now

        if long_crossover and k_now < oversold and st_now == 1:
            confidence = self._compute_confidence(k_now, d_now, oversold, overbought, "long")
            stop_loss = close_price - 2.0 * atr_value
            take_profit = close_price + 3.0 * atr_value

            signals.append(Signal(
                pair=str(df["pair"].iloc[0]) if "pair" in df.columns else "",
                strategy=self.name,
                direction="long",
                entry_price=close_price,
                stop_loss=round(stop_loss, 6),
                take_profit=round(take_profit, 6),
                confidence=confidence,
                metadata={"stoch_k": k_now, "stoch_d": d_now, "st_dir": st_now, "atr": atr_value},
            ))

        # --- SHORT signal ---
        elif short_crossover and k_now > overbought and st_now == -1:
            confidence = self._compute_confidence(k_now, d_now, oversold, overbought, "short")
            stop_loss = close_price + 2.0 * atr_value
            take_profit = close_price - 3.0 * atr_value

            signals.append(Signal(
                pair=str(df["pair"].iloc[0]) if "pair" in df.columns else "",
                strategy=self.name,
                direction="short",
                entry_price=close_price,
                stop_loss=round(stop_loss, 6),
                take_profit=round(take_profit, 6),
                confidence=confidence,
                metadata={"stoch_k": k_now, "stoch_d": d_now, "st_dir": st_now, "atr": atr_value},
            ))

        return signals

    @staticmethod
    def _compute_confidence(
        k: float, d: float, oversold: float, overbought: float, direction: str
    ) -> float:
        """Compute a confidence score in [0.3, 0.95]."""
        spread = abs(k - d)
        base = 0.3 + min(spread / 30.0, 0.4)  # 0.3 – 0.7 from crossover strength

        if direction == "long":
            # Higher confidence the deeper in oversold
            zone_bonus = max(0, (oversold - k) / oversold) * 0.25
        else:
            zone_bonus = max(0, (k - overbought) / (100 - overbought)) * 0.25

        return round(min(base + zone_bonus, 0.95), 4)
