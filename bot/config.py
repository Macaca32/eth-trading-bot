"""
Configuration module for the Hyperliquid Trading Bot.

Uses dataclasses for type-safe, structured configuration.
Supports paper (testnet) and live (mainnet) trading modes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent / ".env")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TradingMode(str, Enum):
    """Trading mode: paper trading on testnet or live on mainnet."""
    PAPER = "paper"
    LIVE = "live"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


# ---------------------------------------------------------------------------
# Sub-configurations
# ---------------------------------------------------------------------------

@dataclass
class ExchangeConfig:
    """Hyperliquid exchange connection settings."""
    trading_mode: TradingMode = TradingMode.PAPER
    wallet_private_key: str = ""
    wallet_address: str = ""
    testnet_base_url: str = "https://api.hyperliquid-testnet.xyz"
    mainnet_base_url: str = "https://api.hyperliquid.xyz"
    testnet_ws_url: str = "wss://api.hyperliquid-testnet.xyz/ws"
    mainnet_ws_url: str = "wss://api.hyperliquid.xyz/ws"

    @property
    def base_url(self) -> str:
        return self.testnet_base_url if self.trading_mode == TradingMode.PAPER else self.mainnet_base_url

    @property
    def ws_url(self) -> str:
        return self.testnet_ws_url if self.trading_mode == TradingMode.PAPER else self.mainnet_ws_url


@dataclass
class RiskConfig:
    """Risk management parameters."""
    max_risk_per_trade_pct: float = 1.5        # Max 1.5% of equity per trade
    max_daily_risk_pct: float = 7.0             # Max 7% daily loss limit
    max_concurrent_positions: int = 5           # Max 5 open positions at once
    max_capital_deployed_pct: float = 50.0      # Max 50% of equity deployed
    circuit_breaker_losses: int = 5             # 5 consecutive losses triggers pause
    circuit_breaker_pause_minutes: int = 30     # 30 minute pause after trigger
    default_stop_loss_pct: float = 2.0          # Default 2% stop loss
    default_take_profit_pct: float = 4.0        # Default 4% take profit
    kelly_fraction: float = 0.25                # Quarter-Kelly sizing
    min_position_size_usd: float = 10.0         # Minimum position size in USD
    max_position_size_usd: float = 10000.0      # Maximum position size in USD


@dataclass
class DataConfig:
    """Data pipeline settings."""
    default_timeframe: str = "1h"
    candle_limit: int = 500                     # Max candles to fetch per request
    sqlite_db_path: str = "data/bot.db"
    ws_reconnect_delay_sec: float = 5.0
    ws_ping_interval_sec: float = 30.0
    candles_retention_days: int = 90            # Purge candles older than N days


@dataclass
class StrategyConfig:
    """Strategy-specific settings."""
    default_pair: str = "BTC"
    minimum_confidence: float = 0.6             # Minimum signal confidence to act on
    signal_cooldown_seconds: int = 300          # 5 min cooldown between signals per pair/strategy


@dataclass
class OptimizationConfig:
    """Optuna optimization settings."""
    n_trials: int = 200
    train_window_days: int = 60                 # Walk-forward: 60-day training window
    validation_window_days: int = 30            # Walk-forward: 30-day validation window
    n_splits: int = 3                           # Number of walk-forward splits
    min_trades_per_split: int = 20              # Minimum trades to evaluate a split
    sharpe_weight: float = 0.6                  # Weight for Sharpe ratio in objective
    drawdown_weight: float = 0.4                # Weight for max drawdown in objective
    hmm_states: int = 3                         # HMM regime states


@dataclass
class ScreenerConfig:
    """Pair screening settings."""
    # TrendScore weights
    trend_adx_weight: float = 0.30
    trend_volume_weight: float = 0.25
    trend_momentum_weight: float = 0.25
    trend_volatility_weight: float = 0.20

    # RiskScore weights
    risk_liquidity_weight: float = 0.25
    risk_volatility_weight: float = 0.25
    risk_spread_weight: float = 0.20
    risk_correlation_weight: float = 0.15
    risk_age_weight: float = 0.15

    # Hard rules
    min_daily_volume_usd: float = 1_000_000
    max_spread_pct: float = 0.10
    min_listing_days: int = 30
    max_pairs: int = 20


@dataclass
class ScheduleConfig:
    """Bot scheduling settings."""
    strategy_loop_interval_sec: float = 60.0    # Run strategies every 60s
    screening_interval_sec: float = 3600.0      # Re-screen pairs every hour
    optimization_interval_hours: int = 24       # Run optimization daily
    risk_check_interval_sec: float = 10.0       # Check risk limits every 10s


@dataclass
class BotConfig:
    """Root configuration for the entire trading bot."""
    exchange: ExchangeConfig = field(default_factory=ExchangeConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    data: DataConfig = field(default_factory=DataConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    optimization: OptimizationConfig = field(default_factory=OptimizationConfig)
    screener: ScreenerConfig = field(default_factory=ScreenerConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    log_level: LogLevel = LogLevel.INFO
    log_file: str = "logs/bot.log"


def load_config() -> BotConfig:
    """
    Build a BotConfig from environment variables.

    Environment variables take precedence over defaults.
    """
    cfg = BotConfig()

    # --- Exchange ---
    mode = os.getenv("TRADING_MODE", "paper").strip().lower()
    cfg.exchange.trading_mode = TradingMode.PAPER if mode == "paper" else TradingMode.LIVE
    cfg.exchange.wallet_private_key = os.getenv("WALLET_PRIVATE_KEY", "")
    cfg.exchange.wallet_address = os.getenv("WALLET_ADDRESS", "")

    # --- Risk ---
    if os.getenv("MAX_RISK_PER_TRADE_PCT"):
        cfg.risk.max_risk_per_trade_pct = float(os.getenv("MAX_RISK_PER_TRADE_PCT"))
    if os.getenv("MAX_DAILY_RISK_PCT"):
        cfg.risk.max_daily_risk_pct = float(os.getenv("MAX_DAILY_RISK_PCT"))
    if os.getenv("MAX_CONCURRENT_POSITIONS"):
        cfg.risk.max_concurrent_positions = int(os.getenv("MAX_CONCURRENT_POSITIONS"))
    if os.getenv("MAX_CAPITAL_DEPLOYED_PCT"):
        cfg.risk.max_capital_deployed_pct = float(os.getenv("MAX_CAPITAL_DEPLOYED_PCT"))
    if os.getenv("CIRCUIT_BREAKER_LOSSES"):
        cfg.risk.circuit_breaker_losses = int(os.getenv("CIRCUIT_BREAKER_LOSSES"))
    if os.getenv("CIRCUIT_BREAKER_PAUSE_MINUTES"):
        cfg.risk.circuit_breaker_pause_minutes = int(os.getenv("CIRCUIT_BREAKER_PAUSE_MINUTES"))

    # --- Data ---
    if os.getenv("DEFAULT_TIMEFRAME"):
        cfg.data.default_timeframe = os.getenv("DEFAULT_TIMEFRAME")

    # --- Optimization ---
    if os.getenv("OPTUNA_N_TRIALS"):
        cfg.optimization.n_trials = int(os.getenv("OPTUNA_N_TRIALS"))

    # --- Logging ---
    if os.getenv("LOG_LEVEL"):
        cfg.log_level = LogLevel(os.getenv("LOG_LEVEL").upper())
    if os.getenv("LOG_FILE"):
        cfg.log_file = os.getenv("LOG_FILE")

    return cfg
