"""
Strategy 4: Supertrend + RSI

Combines the Supertrend trend-following indicator with RSI
for entry timing and overbought/oversold confirmation.

Logic:
  - LONG:  Supertrend flips bullish + RSI is in healthy range (40–70)
  - SHORT: Supertrend flips bearish + RSI is in healthy range (30–60)
  - Extra filters: ATR-based volatility check and ADX for trend strength
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from indicators.technical import adx, atr, ema, rsi, supertrend
from strategies.base import BaseStrategy, Signal


class SupertrendRSIStrategy(BaseStrategy):
    """
    Supertrend + RSI trend-following strategy.

    Parameters (with defaults):
        st_period:        Supertrend ATR period (default 10)
        st_multiplier:    Supertrend multiplier (default 3.0)
        rsi_period:       RSI period (default 14)
        rsi_long_min:     Minimum RSI for long entry (default 40)
        rsi_long_max:     Maximum RSI for long entry (default 70)
        rsi_short_min:    Minimum RSI for short entry (default 30)
        rsi_short_max:    Maximum RSI for short entry (default 60)
        adx_period:       ADX period (default 14)
        adx_threshold:    Minimum ADX for trend strength (default 20)
        atr_period:       ATR period for SL/TP (default 14)
        sl_atr_mult:      Stop-loss ATR multiplier (default 2.0)
        tp_atr_mult:      Take-profit ATR multiplier (default 3.5)
    """

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        super().__init__(params)
        self._params.setdefault("st_period", 10)
        self._params.setdefault("st_multiplier", 3.0)
        self._params.setdefault("rsi_period", 14)
        self._params.setdefault("rsi_long_min", 40)
        self._params.setdefault("rsi_long_max", 70)
        self._params.setdefault("rsi_short_min", 30)
        self._params.setdefault("rsi_short_max", 60)
        self._params.setdefault("adx_period", 14)
        self._params.setdefault("adx_threshold", 20)
        self._params.setdefault("atr_period", 14)
        self._params.setdefault("sl_atr_mult", 2.0)
        self._params.setdefault("tp_atr_mult", 3.5)

    @property
    def name(self) -> str:
        return "Supertrend_RSI"

    def get_param_ranges(self) -> dict[str, tuple[float, float]]:
        return {
            "st_period": (5, 25),
            "st_multiplier": (1.5, 5.0),
            "rsi_period": (7, 28),
            "rsi_long_min": (25, 50),
            "rsi_long_max": (60, 85),
            "rsi_short_min": (15, 40),
            "rsi_short_max": (50, 75),
            "adx_period": (7, 28),
            "adx_threshold": (10, 40),
            "atr_period": (7, 21),
            "sl_atr_mult": (1.0, 4.0),
            "tp_atr_mult": (2.0, 6.0),
        }

    def required_candle_count(self) -> int:
        return max(
            self._params["st_period"] * 3,
            self._params["adx_period"] * 4,
            150,
        )

    def calculate_signals(self, df: pd.DataFrame) -> list[Signal]:
        """
        Generate trend-following signals based on Supertrend direction flips + RSI.

        Args:
            df: OHLCV DataFrame.

        Returns:
            List of Signal objects.
        """
        if len(df) < self.required_candle_count():
            return []

        p = self._params
        h, l, c = df["high"], df["low"], df["close"]

        # Compute indicators
        st_val, st_dir = supertrend(h, l, c, int(p["st_period"]), p["st_multiplier"])
        rsi_val = rsi(c, int(p["rsi_period"]))
        adx_val, plus_di, minus_di = adx(h, l, c, int(p["adx_period"]))
        atr_val = atr(h, l, c, int(p["atr_period"]))

        if len(df) < 2:
            return []

        latest = len(df) - 1
        prev = latest - 1

        if (pd.isna(st_dir.iloc[latest]) or pd.isna(st_dir.iloc[prev])
                or pd.isna(rsi_val.iloc[latest]) or pd.isna(adx_val.iloc[latest])
                or pd.isna(atr_val.iloc[latest]) or pd.isna(plus_di.iloc[latest])
                or pd.isna(minus_di.iloc[latest])):
            return []

        close_price = float(c.iloc[latest])
        atr_value = float(atr_val.iloc[latest])
        st_now = int(st_dir.iloc[latest])
        st_prev = int(st_dir.iloc[prev])
        rsi_now = float(rsi_val.iloc[latest])
        adx_now = float(adx_val.iloc[latest])
        pdi = float(plus_di.iloc[latest])
        mdi = float(minus_di.iloc[latest])

        signals: list[Signal] = []

        # --- LONG: Supertrend flips to bullish + RSI in range + ADX strong ---
        st_flip_bullish = st_prev == -1 and st_now == 1
        rsi_long_ok = p["rsi_long_min"] <= rsi_now <= p["rsi_long_max"]
        trend_strong = adx_now >= p["adx_threshold"]
        di_bullish = pdi > mdi

        if st_flip_bullish and rsi_long_ok and trend_strong and di_bullish:
            confidence = self._compute_confidence(
                rsi_now, adx_now, p["adx_threshold"],
                p["rsi_long_min"], p["rsi_long_max"], "long",
                pdi, mdi,
            )
            stop_loss = close_price - p["sl_atr_mult"] * atr_value
            take_profit = close_price + p["tp_atr_mult"] * atr_value

            signals.append(Signal(
                pair=str(df["pair"].iloc[0]) if "pair" in df.columns else "",
                strategy=self.name,
                direction="long",
                entry_price=close_price,
                stop_loss=round(stop_loss, 6),
                take_profit=round(take_profit, 6),
                confidence=confidence,
                metadata={
                    "supertrend_dir": st_now, "rsi": rsi_now,
                    "adx": adx_now, "plus_di": pdi, "minus_di": mdi,
                },
            ))

        # --- SHORT: Supertrend flips to bearish + RSI in range + ADX strong ---
        st_flip_bearish = st_prev == 1 and st_now == -1
        rsi_short_ok = p["rsi_short_min"] <= rsi_now <= p["rsi_short_max"]
        di_bearish = mdi > pdi

        if st_flip_bearish and rsi_short_ok and trend_strong and di_bearish:
            confidence = self._compute_confidence(
                rsi_now, adx_now, p["adx_threshold"],
                p["rsi_short_min"], p["rsi_short_max"], "short",
                pdi, mdi,
            )
            stop_loss = close_price + p["sl_atr_mult"] * atr_value
            take_profit = close_price - p["tp_atr_mult"] * atr_value

            signals.append(Signal(
                pair=str(df["pair"].iloc[0]) if "pair" in df.columns else "",
                strategy=self.name,
                direction="short",
                entry_price=close_price,
                stop_loss=round(stop_loss, 6),
                take_profit=round(take_profit, 6),
                confidence=confidence,
                metadata={
                    "supertrend_dir": st_now, "rsi": rsi_now,
                    "adx": adx_now, "plus_di": pdi, "minus_di": mdi,
                },
            ))

        return signals

    @staticmethod
    def _compute_confidence(
        rsi_val: float, adx_val: float, adx_threshold: float,
        rsi_lo: float, rsi_hi: float, direction: str,
        plus_di: float, minus_di: float,
    ) -> float:
        """Compute confidence in [0.3, 0.95]."""
        # ADX strength: stronger trend → higher confidence
        adx_score = min((adx_val - adx_threshold) / (50 - adx_threshold), 1.0) * 0.35
        adx_score = max(adx_score, 0.0)

        # RSI sweet-spot score: center of the range is ideal
        rsi_center = (rsi_lo + rsi_hi) / 2
        rsi_half_range = (rsi_hi - rsi_lo) / 2
        if rsi_half_range > 0:
            rsi_dist = abs(rsi_val - rsi_center) / rsi_half_range
            rsi_score = max(0, 1.0 - rsi_dist) * 0.35
        else:
            rsi_score = 0.0

        # DI confirmation score
        if direction == "long":
            di_score = min((plus_di - minus_di) / 30.0, 1.0) * 0.3
        else:
            di_score = min((minus_di - plus_di) / 30.0, 1.0) * 0.3
        di_score = max(di_score, 0.0)

        return round(min(0.3 + adx_score + rsi_score + di_score, 0.95), 4)
