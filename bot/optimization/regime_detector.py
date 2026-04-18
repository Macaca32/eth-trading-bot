"""
HMM-based market regime detection.

Uses a Gaussian Hidden Markov Model to classify the current market
into one of three regimes:
  1. Bull / Trending Up
  2. Bear / Trending Down
  3. Ranging / Sideways

Features used:
  - Returns (close-to-close % change)
  - Realized volatility (rolling std of returns)
  - Volume change rate
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger

try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.mixture import GaussianMixture
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class RegimeDetector:
    """
    Market regime detector using Gaussian Mixture Model (GMM).

    GMM is used instead of a full HMM as it provides similar regime
    detection with fewer dependencies while being more stable for
    this use case.

    Regimes:
      0 — Bull (positive mean returns, moderate volatility)
      1 — Bear (negative mean returns, higher volatility)
      2 — Range (low returns, low volatility)
    """

    def __init__(self, n_states: int = 3, lookback: int = 100) -> None:
        """
        Args:
            n_states: Number of market regimes to detect.
            lookback: Number of bars to use for feature calculation.
        """
        if not HAS_SKLEARN:
            logger.warning("scikit-learn not installed — regime detection will return defaults")

        self.n_states = n_states
        self.lookback = lookback
        self._model: Optional[GaussianMixture] = None
        self._scaler: Optional[StandardScaler] = None
        self._regime_labels: Optional[np.ndarray] = None  # Sorted labels: 0=bull, 1=bear, 2=range
        self._is_fitted = False

    def fit(self, df: pd.DataFrame) -> None:
        """
        Fit the regime model on historical data.

        Args:
            df: OHLCV DataFrame with columns: close, volume.
        """
        if not HAS_SKLEARN:
            return

        features = self._extract_features(df)
        if features is None or len(features) < self.lookback:
            logger.warning("Not enough data to fit regime detector")
            return

        # Use last `lookback` rows
        X = features.tail(self.lookback).values

        # Scale features
        self._scaler = StandardScaler()
        X_scaled = self._scaler.fit_transform(X)

        # Fit GMM
        self._model = GaussianMixture(
            n_components=self.n_states,
            covariance_type="full",
            n_init=5,
            max_iter=200,
            random_state=42,
        )
        self._model.fit(X_scaled)

        # Determine regime labels by sorting component means
        means = self._model.means_[:, 0]  # Mean return for each component
        sorted_indices = np.argsort(means)[::-1]  # Highest return first
        label_map = {old: new for new, old in enumerate(sorted_indices)}
        self._regime_labels = np.array([label_map[i] for i in range(self.n_states)])

        self._is_fitted = True
        logger.info("Regime detector fitted with {} states", self.n_states)

    def predict(self, df: pd.DataFrame) -> int:
        """
        Predict the current market regime.

        Args:
            df: OHLCV DataFrame (must have at least 3 rows for feature calc).

        Returns:
            Regime label: 0 (bull), 1 (bear), 2 (range).
        """
        if not self._is_fitted or self._model is None or self._scaler is None:
            return 2  # Default to range

        features = self._extract_features(df)
        if features is None or len(features) < 3:
            return 2

        # Use the most recent feature vector
        X = features.iloc[[-1]].values
        X_scaled = self._scaler.transform(X)

        raw_label = int(self._model.predict(X_scaled)[0])
        return int(self._regime_labels[raw_label]) if self._regime_labels is not None else raw_label

    def predict_proba(self, df: pd.DataFrame) -> dict[int, float]:
        """
        Predict regime probabilities.

        Returns:
            Dict mapping regime label to probability.
        """
        if not self._is_fitted or self._model is None or self._scaler is None:
            return {0: 0.33, 1: 0.33, 2: 0.34}

        features = self._extract_features(df)
        if features is None or len(features) < 3:
            return {0: 0.33, 1: 0.33, 2: 0.34}

        X = features.iloc[[-1]].values
        X_scaled = self._scaler.transform(X)
        probs = self._model.predict_proba(X_scaled)[0]

        result: dict[int, float] = {}
        if self._regime_labels is not None:
            for i, p in enumerate(probs):
                result[int(self._regime_labels[i])] = round(float(p), 4)
        return result

    def get_regime_name(self, regime: int) -> str:
        """Get human-readable name for a regime label."""
        names = {0: "bull", 1: "bear", 2: "range"}
        return names.get(regime, "unknown")

    def _extract_features(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        Extract features for regime detection.

        Features:
          - returns: Close-to-close % change
          - volatility: Rolling std of returns (10-period)
          - volume_change: % change in volume
        """
        if len(df) < 15:
            return None

        feat = pd.DataFrame(index=df.index)
        feat["returns"] = df["close"].pct_change()
        feat["volatility"] = feat["returns"].rolling(10, min_periods=5).std()
        feat["volume_change"] = df["volume"].pct_change()

        # Drop rows with NaN (first few rows)
        feat = feat.dropna()
        return feat if len(feat) > 0 else None

    @property
    def is_fitted(self) -> bool:
        return self._is_fitted
