"""
Technical indicator library.

All indicators are implemented from scratch using pandas/numpy
to minimise external dependencies. Every function accepts a pandas
Series (or DataFrame) and returns a pandas Series of the same length.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# =========================================================================
#  Moving Averages
# =========================================================================

def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def dema(series: pd.Series, period: int) -> pd.Series:
    """Double Exponential Moving Average."""
    e = ema(series, period)
    return 2 * e - ema(e, period)


def wma(series: pd.Series, period: int) -> pd.Series:
    """Weighted Moving Average."""
    weights = np.arange(1, period + 1, dtype=float)
    return series.rolling(window=period, min_periods=period).apply(
        lambda x: np.dot(x, weights) / weights.sum(), raw=True
    )


# =========================================================================
#  RSI — Relative Strength Index
# =========================================================================

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index.

    Returns values in [0, 100]. Uses Wilder's smoothing (exponential).
    """
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_vals = 100 - (100 / (1 + rs))
    return rsi_vals


# =========================================================================
#  Stochastic RSI
# =========================================================================

def stochrsi(
    series: pd.Series,
    rsi_period: int = 14,
    stoch_period: int = 14,
    k_smooth: int = 3,
    d_smooth: int = 3,
) -> tuple[pd.Series, pd.Series]:
    """
    Stochastic RSI.

    Returns:
        (stoch_rsi_k, stoch_rsi_d) — both in [0, 100].
    """
    rsi_vals = rsi(series, rsi_period)
    lowest_rsi = rsi_vals.rolling(window=stoch_period, min_periods=stoch_period).min()
    highest_rsi = rsi_vals.rolling(window=stoch_period, min_periods=stoch_period).max()
    stoch = (rsi_vals - lowest_rsi) / (highest_rsi - lowest_rsi).replace(0, np.nan) * 100

    k = stoch.rolling(window=k_smooth, min_periods=k_smooth).mean()
    d = k.rolling(window=d_smooth, min_periods=d_smooth).mean()
    return k, d


# =========================================================================
#  MACD — Moving Average Convergence / Divergence
# =========================================================================

def macd(
    series: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    MACD indicator.

    Returns:
        (macd_line, signal_line, histogram)
    """
    fast_ema = ema(series, fast_period)
    slow_ema = ema(series, slow_period)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal_period)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


# =========================================================================
#  Bollinger Bands
# =========================================================================

def bollinger_bands(
    series: pd.Series,
    period: int = 20,
    num_std: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Bollinger Bands.

    Returns:
        (upper_band, middle_band, lower_band)
    """
    middle = sma(series, period)
    std = series.rolling(window=period, min_periods=period).std(ddof=0)
    upper = middle + num_std * std
    lower = middle - num_std * std
    return upper, middle, lower


# =========================================================================
#  ATR — Average True Range
# =========================================================================

def atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """
    Average True Range.

    Uses Wilder's smoothing (equivalent to EMA with alpha = 1/period).
    """
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return true_range.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


# =========================================================================
#  Supertrend
# =========================================================================

def supertrend(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 10,
    multiplier: float = 3.0,
) -> tuple[pd.Series, pd.Series]:
    """
    Supertrend indicator.

    Returns:
        (supertrend_value, direction)
        direction: +1 when uptrend (price above supertrend),
                   -1 when downtrend.
    """
    hl2 = (high + low) / 2
    atr_val = atr(high, low, close, period)

    upper_band = hl2 + multiplier * atr_val
    lower_band = hl2 - multiplier * atr_val

    # Initialize arrays
    st = pd.Series(np.nan, index=close.index)
    direction = pd.Series(np.nan, index=close.index)

    # First valid value
    first_valid = period  # min_periods for atr
    if first_valid >= len(close):
        return st, direction

    st.iloc[first_valid] = upper_band.iloc[first_valid]
    direction.iloc[first_valid] = 1  # Default start

    for i in range(first_valid + 1, len(close)):
        # Lower band logic
        if lower_band.iloc[i] > lower_band.iloc[i - 1] or close.iloc[i - 1] < lower_band.iloc[i - 1]:
            lb = lower_band.iloc[i]
        else:
            lb = lower_band.iloc[i - 1]

        # Upper band logic
        if upper_band.iloc[i] < upper_band.iloc[i - 1] or close.iloc[i - 1] > upper_band.iloc[i - 1]:
            ub = upper_band.iloc[i]
        else:
            ub = upper_band.iloc[i - 1]

        # Direction
        if direction.iloc[i - 1] == 1:
            if close.iloc[i] < lb:
                st_val = ub
                d = -1
            else:
                st_val = lb
                d = 1
        else:
            if close.iloc[i] > ub:
                st_val = lb
                d = 1
            else:
                st_val = ub
                d = -1

        st.iloc[i] = st_val
        direction.iloc[i] = d

    return st, direction


# =========================================================================
#  ADX — Average Directional Index
# =========================================================================

def adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Average Directional Index with +DI and -DI.

    Returns:
        (adx, plus_di, minus_di)
    """
    prev_high = high.shift(1)
    prev_low = low.shift(1)

    plus_dm = high - prev_high
    minus_dm = prev_low - low

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    atr_val = atr(high, low, close, period)

    plus_di = 100 * (plus_dm.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
                      / atr_val.replace(0, np.nan))
    minus_di = 100 * (minus_dm.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
                       / atr_val.replace(0, np.nan))

    dx_denom = (plus_di + minus_di).replace(0, np.nan)
    dx = ((plus_di - minus_di).abs() / dx_denom) * 100
    adx_val = dx.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    return adx_val, plus_di, minus_di


# =========================================================================
#  Aroon
# =========================================================================

def aroon(
    high: pd.Series,
    low: pd.Series,
    period: int = 25,
) -> tuple[pd.Series, pd.Series]:
    """
    Aroon Up / Aroon Down.

    Returns:
        (aroon_up, aroon_down) — both in [0, 100].
    """
    aroon_up = high.rolling(window=period + 1, min_periods=period + 1).apply(
        lambda x: float(np.argmax(x)) / period * 100, raw=True
    )
    aroon_down = low.rolling(window=period + 1, min_periods=period + 1).apply(
        lambda x: float(np.argmin(x)) / period * 100, raw=True
    )
    return aroon_up, aroon_down


# =========================================================================
#  VWAP — Volume-Weighted Average Price
# =========================================================================

def vwap(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
) -> pd.Series:
    """Volume-Weighted Average Price (resets daily if index is DatetimeIndex)."""
    typical_price = (high + low + close) / 3
    cumulative_vp = (typical_price * volume).cumsum()
    cumulative_vol = volume.cumsum()
    return cumulative_vp / cumulative_vol.replace(0, np.nan)


# =========================================================================
#  OBV — On-Balance Volume
# =========================================================================

def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume."""
    direction = np.sign(close.diff())
    obv_vals = (direction * volume).cumsum().fillna(0)
    return obv_vals


# =========================================================================
#  CCI — Commodity Channel Index
# =========================================================================

def cci(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 20,
) -> pd.Series:
    """Commodity Channel Index."""
    typical_price = (high + low + close) / 3
    sma_tp = sma(typical_price, period)
    mean_dev = typical_price.rolling(window=period, min_periods=period).apply(
        lambda x: np.abs(x - x.mean()).mean(), raw=True
    )
    cci_val = (typical_price - sma_tp) / (0.015 * mean_dev.replace(0, np.nan))
    return cci_val


# =========================================================================
#  Williams %R
# =========================================================================

def williams_r(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """Williams %R. Returns values in [-100, 0]."""
    highest_high = high.rolling(window=period, min_periods=period).max()
    lowest_low = low.rolling(window=period, min_periods=period).min()
    denom = (highest_high - lowest_low).replace(0, np.nan)
    return ((highest_high - close) / denom) * -100


# =========================================================================
#  Momentum / Rate of Change
# =========================================================================

def momentum(series: pd.Series, period: int = 10) -> pd.Series:
    """Momentum = current value - value N periods ago."""
    return series - series.shift(period)


def roc(series: pd.Series, period: int = 10) -> pd.Series:
    """Rate of Change in percent."""
    prev = series.shift(period)
    return ((series - prev) / prev.replace(0, np.nan)) * 100


# =========================================================================
#  Helpers for strategy use
# =========================================================================

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a broad set of standard indicators to an OHLCV DataFrame.

    Expected columns: 'open', 'high', 'low', 'close', 'volume'.
    Adds many columns in-place and returns the DataFrame.
    """
    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]

    # Moving averages
    df["sma_20"] = sma(c, 20)
    df["sma_50"] = sma(c, 50)
    df["sma_200"] = sma(c, 200)
    df["ema_9"] = ema(c, 9)
    df["ema_21"] = ema(c, 21)

    # RSI
    df["rsi_14"] = rsi(c, 14)

    # Stochastic RSI
    df["stoch_rsi_k"], df["stoch_rsi_d"] = stochrsi(c)

    # MACD
    df["macd"], df["macd_signal"], df["macd_hist"] = macd(c)

    # Bollinger Bands
    df["bb_upper"], df["bb_middle"], df["bb_lower"] = bollinger_bands(c)
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]

    # ATR
    df["atr_14"] = atr(h, l, c, 14)

    # Supertrend
    df["supertrend"], df["st_direction"] = supertrend(h, l, c)

    # ADX
    df["adx"], df["plus_di"], df["minus_di"] = adx(h, l, c)

    # Aroon
    df["aroon_up"], df["aroon_down"] = aroon(h, l)

    # VWAP
    df["vwap"] = vwap(h, l, c, v)

    # OBV
    df["obv"] = obv(c, v)

    # Momentum
    df["momentum_10"] = momentum(c, 10)
    df["roc_10"] = roc(c, 10)

    return df


__all__ = [
    "sma", "ema", "dema", "wma",
    "rsi", "stochrsi",
    "macd",
    "bollinger_bands",
    "atr", "supertrend",
    "adx", "aroon",
    "vwap", "obv",
    "cci", "williams_r",
    "momentum", "roc",
    "add_indicators",
]
