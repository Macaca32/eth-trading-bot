"""
Strategy 3: BB Winner PRO (Mean Reversion)

An enhanced Bollinger Band mean-reversion strategy that identifies
extreme price deviations and trades the reversion.

Logic:
  - LONG:  Price closes below lower BB + RSI oversold + BWI (Band Width Index) expanding
  - SHORT: Price closes above upper BB + RSI overbought + BWI expanding
  - Exits when price returns to the middle band (BB mean)
  - Uses ATR for dynamic stop-loss placement
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from indicators.technical import atr, bollinger_bands, rsi, ema
from strategies.base import BaseStrategy, Signal


class BBWinnerProStrategy(BaseStrategy):
    """
    Bollinger Band Winner PRO — mean-reversion strategy.

    Parameters (with defaults):
        bb_period:        Bollinger Band period (default 20)
        bb_std:           Bollinger Band std devs (default 2.0)
        rsi_period:       RSI period (default 14)
        rsi_oversold:     RSI oversold threshold (default 30)
        rsi_overbought:   RSI overbought threshold (default 70)
        bwi_expand:       BWI expansion ratio for signal (default 1.2)
        bwi_period:       Period for BWI average (default 20)
        atr_period:       ATR period (default 14)
        sl_atr_mult:      Stop-loss ATR multiplier (default 2.0)
        tp_atr_mult:      Take-profit ATR multiplier (default 3.0)
    """

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        super().__init__(params)
        self._params.setdefault("bb_period", 20)
        self._params.setdefault("bb_std", 2.0)
        self._params.setdefault("rsi_period", 14)
        self._params.setdefault("rsi_oversold", 30)
        self._params.setdefault("rsi_overbought", 70)
        self._params.setdefault("bwi_expand", 1.2)
        self._params.setdefault("bwi_period", 20)
        self._params.setdefault("atr_period", 14)
        self._params.setdefault("sl_atr_mult", 2.0)
        self._params.setdefault("tp_atr_mult", 3.0)

    @property
    def name(self) -> str:
        return "BB_Winner_PRO"

    def get_param_ranges(self) -> dict[str, tuple[float, float]]:
        return {
            "bb_period": (10, 40),
            "bb_std": (1.5, 3.5),
            "rsi_period": (7, 28),
            "rsi_oversold": (15, 40),
            "rsi_overbought": (60, 85),
            "bwi_expand": (0.8, 2.0),
            "bwi_period": (10, 40),
            "atr_period": (7, 21),
            "sl_atr_mult": (1.0, 3.5),
            "tp_atr_mult": (2.0, 6.0),
        }

    def required_candle_count(self) -> int:
        return max(
            self._params["bb_period"] + self._params["bwi_period"] + 20,
            150,
        )

    def calculate_signals(self, df: pd.DataFrame) -> list[Signal]:
        """
        Generate mean-reversion signals based on BB extremes + RSI + BWI.

        Args:
            df: OHLCV DataFrame.

        Returns:
            List of Signal objects.
        """
        if len(df) < self.required_candle_count():
            return []

        p = self._params
        h, l, c = df["high"], df["low"], df["close"]

        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = bollinger_bands(c, int(p["bb_period"]), p["bb_std"])

        # Band Width Index (BW) = (upper - lower) / middle * 100
        bb_width = (bb_upper - bb_lower) / bb_middle.replace(0, float("nan")) * 100
        bwi_sma = ema(bb_width, int(p["bwi_period"]))

        # RSI
        rsi_val = rsi(c, int(p["rsi_period"]))

        # ATR
        atr_val = atr(h, l, c, int(p["atr_period"]))

        if len(df) < 2:
            return []

        latest = len(df) - 1
        prev = latest - 1

        if (pd.isna(bb_upper.iloc[latest]) or pd.isna(bb_lower.iloc[latest])
                or pd.isna(bb_middle.iloc[latest]) or pd.isna(bwi_sma.iloc[latest])
                or pd.isna(rsi_val.iloc[latest]) or pd.isna(atr_val.iloc[latest])
                or pd.isna(c.iloc[prev])):
            return []

        close_price = float(c.iloc[latest])
        prev_close = float(c.iloc[prev])
        atr_value = float(atr_val.iloc[latest])

        bb_lower_val = float(bb_lower.iloc[latest])
        bb_upper_val = float(bb_upper.iloc[latest])
        bb_mid_val = float(bb_middle.iloc[latest])
        bb_width_now = float(bb_width.iloc[latest])
        bwi_avg = float(bwi_sma.iloc[latest])
        rsi_now = float(rsi_val.iloc[latest])

        # BWI expansion check: current width > average * factor
        bwi_expanding = bwi_avg > 0 and bb_width_now > bwi_avg * p["bwi_expand"]

        signals: list[Signal] = []

        # --- LONG: price below lower BB + RSI oversold + BWI expanding ---
        below_lower = close_price < bb_lower_val
        prev_above_lower = prev_close >= float(bb_lower.iloc[prev]) if not pd.isna(bb_lower.iloc[prev]) else False
        rsi_oversold = rsi_now < p["rsi_oversold"]

        if below_lower and prev_above_lower and rsi_oversold and bwi_expanding:
            confidence = self._compute_confidence(
                close_price, bb_lower_val, bb_upper_val, rsi_now,
                p["rsi_oversold"], p["rsi_overbought"], bb_width_now, bwi_avg, "long"
            )
            stop_loss = close_price - p["sl_atr_mult"] * atr_value
            take_profit = bb_mid_val  # Target the mean

            signals.append(Signal(
                pair=str(df["pair"].iloc[0]) if "pair" in df.columns else "",
                strategy=self.name,
                direction="long",
                entry_price=close_price,
                stop_loss=round(stop_loss, 6),
                take_profit=round(take_profit, 6),
                confidence=confidence,
                metadata={
                    "rsi": rsi_now, "bb_width": bb_width_now,
                    "bwi_avg": bwi_avg, "bb_lower": bb_lower_val, "bb_mid": bb_mid_val,
                },
            ))

        # --- SHORT: price above upper BB + RSI overbought + BWI expanding ---
        above_upper = close_price > bb_upper_val
        prev_below_upper = prev_close <= float(bb_upper.iloc[prev]) if not pd.isna(bb_upper.iloc[prev]) else False
        rsi_overbought = rsi_now > p["rsi_overbought"]

        if above_upper and prev_below_upper and rsi_overbought and bwi_expanding:
            confidence = self._compute_confidence(
                close_price, bb_lower_val, bb_upper_val, rsi_now,
                p["rsi_oversold"], p["rsi_overbought"], bb_width_now, bwi_avg, "short"
            )
            stop_loss = close_price + p["sl_atr_mult"] * atr_value
            take_profit = bb_mid_val  # Target the mean

            signals.append(Signal(
                pair=str(df["pair"].iloc[0]) if "pair" in df.columns else "",
                strategy=self.name,
                direction="short",
                entry_price=close_price,
                stop_loss=round(stop_loss, 6),
                take_profit=round(take_profit, 6),
                confidence=confidence,
                metadata={
                    "rsi": rsi_now, "bb_width": bb_width_now,
                    "bwi_avg": bwi_avg, "bb_upper": bb_upper_val, "bb_mid": bb_mid_val,
                },
            ))

        return signals

    @staticmethod
    def _compute_confidence(
        close: float, bb_lower: float, bb_upper: float,
        rsi_val: float, rsi_oversold: float, rsi_overbought: float,
        bb_width: float, bwi_avg: float, direction: str,
    ) -> float:
        """Compute confidence in [0.3, 0.95]."""
        bb_range = bb_upper - bb_lower
        if bb_range == 0:
            bb_score = 0.0
        else:
            if direction == "long":
                penetration = (bb_lower - close) / bb_range
            else:
                penetration = (close - bb_upper) / bb_range
            bb_score = min(abs(penetration) * 5, 1.0) * 0.4

        # RSI extremity
        if direction == "long":
            rsi_score = max(0, (rsi_oversold - rsi_val) / rsi_oversold) * 0.3
        else:
            rsi_score = max(0, (rsi_val - rsi_overbought) / (100 - rsi_overbought)) * 0.3

        # BWI expansion score
        bwi_score = (bb_width / bwi_avg - 1.0) * 0.3 if bwi_avg > 0 else 0.0

        return round(min(0.3 + bb_score + rsi_score + bwi_score, 0.95), 4)
