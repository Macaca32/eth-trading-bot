"""
Pair screening / scoring system.

Ranks tradable pairs by two composite scores:
  - TrendScore: Measures trend quality and momentum
  - RiskScore:  Measures safety and liquidity

Also applies hard filtering rules to eliminate unsuitable pairs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
import pandas as pd
from loguru import logger

from config import ScreenerConfig
from indicators.technical import adx, atr, ema, momentum, rsi, sma
from utils.helpers import clamp


@dataclass
class PairScore:
    """
    Scoring result for a single pair.

    Attributes:
        pair:         Trading pair name.
        trend_score:  Composite trend score [0, 100].
        risk_score:   Composite risk score [0, 100] (higher = safer).
        combined:     Weighted combination of trend and risk.
        passed:       Whether the pair passed all hard filters.
        details:      Individual component scores for debugging.
    """
    pair: str
    trend_score: float = 0.0
    risk_score: float = 0.0
    combined: float = 0.0
    passed: bool = True
    details: dict[str, float] = field(default_factory=dict)


class PairScreener:
    """
    Pair screening and scoring engine.

    TrendScore components (weighted):
      - ADX (trend strength):        30%
      - Volume trend:                25%
      - Momentum (ROC):              25%
      - Volatility (ATR normalized): 20%

    RiskScore components (weighted):
      - Liquidity (avg volume):      25%
      - Volatility (normalized):     25%
      - Spread estimate:             20%
      - Correlation to BTC:          15%
      - Listing age:                 15%

    Hard rules:
      - Minimum daily volume
      - Maximum spread
      - Minimum listing age
    """

    def __init__(self, config: ScreenerConfig) -> None:
        self._config = config

    def screen(
        self,
        pairs_data: dict[str, pd.DataFrame],
        market_info: Optional[dict[str, dict[str, Any]]] = None,
    ) -> list[PairScore]:
        """
        Screen and score a set of trading pairs.

        Args:
            pairs_data: Dict mapping pair name → OHLCV DataFrame.
            market_info: Optional dict of market metadata per pair:
                         {"BTC": {"daily_volume": 1e9, "spread": 0.01, "listing_days": 2000}, ...}

        Returns:
            List of PairScore objects sorted by combined score (descending).
        """
        market_info = market_info or {}
        scores: list[PairScore] = []

        for pair, df in pairs_data.items():
            if len(df) < 50:
                logger.debug("Skipping {} — insufficient data ({} rows)", pair, len(df))
                continue

            score = self._score_pair(pair, df, market_info.get(pair, {}))
            scores.append(score)

        # Sort by combined score descending
        scores.sort(key=lambda s: s.combined, reverse=True)

        # Apply max pairs limit
        if len(scores) > self._config.max_pairs:
            scores = scores[:self._config.max_pairs]

        passed = sum(1 for s in scores if s.passed)
        logger.info(
            "Screened {} pairs: {} passed hard filters, top pair: {} (score={:.1f})",
            len(scores), passed,
            scores[0].pair if scores else "none",
            scores[0].combined if scores else 0,
        )

        return scores

    def _score_pair(
        self,
        pair: str,
        df: pd.DataFrame,
        info: dict[str, Any],
    ) -> PairScore:
        """Score a single pair."""
        score = PairScore(pair=pair)
        h, l, c, v = df["high"], df["low"], df["close"], df["volume"]

        # --- Hard rules ---
        daily_vol = info.get("daily_volume", float(v.tail(24).sum()) if len(df) >= 24 else 0)
        spread = info.get("spread", 0.02)
        listing_days = info.get("listing_days", 365)

        if daily_vol < self._config.min_daily_volume_usd:
            score.passed = False
            score.details["fail_reason"] = "low_volume"
        if spread > self._config.max_spread_pct:
            score.passed = False
            score.details["fail_reason"] = "high_spread"
        if listing_days < self._config.min_listing_days:
            score.passed = False
            score.details["fail_reason"] = "new_listing"

        # --- TrendScore components ---

        # 1. ADX (trend strength)
        adx_val, _, _ = adx(h, l, c, 14)
        adx_latest = float(adx_val.iloc[-1]) if not pd.isna(adx_val.iloc[-1]) else 0
        adx_score = min(adx_latest / 50.0, 1.0) * 100  # Normalize to [0, 100]
        score.details["adx_raw"] = adx_latest
        score.details["adx_score"] = adx_score

        # 2. Volume trend (EMA ratio)
        vol_ema_short = ema(v, 10)
        vol_ema_long = ema(v, 50)
        if not pd.isna(vol_ema_short.iloc[-1]) and not pd.isna(vol_ema_long.iloc[-1]) and vol_ema_long.iloc[-1] > 0:
            vol_ratio = float(vol_ema_short.iloc[-1] / vol_ema_long.iloc[-1])
            vol_score = clamp(vol_ratio, 0.3, 2.0) / 2.0 * 100
        else:
            vol_ratio = 1.0
            vol_score = 50.0
        score.details["vol_ratio"] = vol_ratio
        score.details["vol_score"] = vol_score

        # 3. Momentum (ROC-10)
        roc_val = momentum(c, 10)
        roc_latest = float(roc_val.iloc[-1]) if not pd.isna(roc_val.iloc[-1]) else 0
        close_latest = float(c.iloc[-1])
        roc_pct = (roc_latest / close_latest * 100) if close_latest > 0 else 0
        momentum_score = clamp(50 + roc_pct * 5, 0, 100)
        score.details["roc_pct"] = roc_pct
        score.details["momentum_score"] = momentum_score

        # 4. Volatility (ATR normalized)
        atr_val = atr(h, l, c, 14)
        atr_latest = float(atr_val.iloc[-1]) if not pd.isna(atr_val.iloc[-1]) else 0
        atr_pct = (atr_latest / close_latest * 100) if close_latest > 0 else 0
        # Ideal range: 1-5% ATR
        if atr_pct < 0.5:
            vol_score = 30  # Too quiet
        elif atr_pct > 8:
            vol_score = 30  # Too volatile
        else:
            vol_score = 100 - abs(atr_pct - 3) * 10
        vol_score = clamp(vol_score, 0, 100)
        score.details["atr_pct"] = atr_pct
        score.details["volatility_score"] = vol_score

        # TrendScore weighted average
        score.trend_score = (
            adx_score * self._config.trend_adx_weight
            + vol_score * self._config.trend_volume_weight
            + momentum_score * self._config.trend_momentum_weight
            + vol_score * self._config.trend_volatility_weight
        )

        # --- RiskScore components ---

        # 1. Liquidity (based on average volume)
        if daily_vol > 0:
            liquidity_score = min(np.log10(daily_vol) / 10.0 * 100, 100)
        else:
            liquidity_score = 20
        score.details["liquidity_score"] = liquidity_score

        # 2. Volatility risk (lower = safer = higher score)
        if atr_pct < 1:
            vol_risk = 90
        elif atr_pct < 3:
            vol_risk = 70
        elif atr_pct < 5:
            vol_risk = 50
        elif atr_pct < 8:
            vol_risk = 30
        else:
            vol_risk = 10
        score.details["vol_risk_score"] = vol_risk

        # 3. Spread (lower = better)
        if spread < 0.01:
            spread_score = 100
        elif spread < 0.03:
            spread_score = 80
        elif spread < 0.05:
            spread_score = 60
        elif spread < 0.10:
            spread_score = 40
        else:
            spread_score = 10
        score.details["spread_score"] = spread_score

        # 4. Correlation to BTC (estimate from data similarity — placeholder)
        # In production, this would use actual BTC correlation data
        correlation_score = info.get("correlation_score", 50)
        score.details["correlation_score"] = correlation_score

        # 5. Listing age (older = more established = safer)
        if listing_days > 365:
            age_score = 100
        elif listing_days > 180:
            age_score = 80
        elif listing_days > 90:
            age_score = 60
        elif listing_days > 30:
            age_score = 40
        else:
            age_score = 10
        score.details["age_score"] = age_score

        # RiskScore weighted average
        score.risk_score = (
            liquidity_score * self._config.risk_liquidity_weight
            + vol_risk * self._config.risk_volatility_weight
            + spread_score * self._config.risk_spread_weight
            + correlation_score * self._config.risk_correlation_weight
            + age_score * self._config.risk_age_weight
        )

        # Combined score (60% trend + 40% risk)
        score.combined = 0.6 * score.trend_score + 0.4 * score.risk_score

        return score
