# Hyperliquid Trading Bot

A production-ready Python trading bot for the [Hyperliquid](https://hyperliquid.xyz) decentralized exchange.
Features 4 complementary strategies with AI-optimized parameters, comprehensive risk management,
and walk-forward backtesting.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              main.py                                    │
│                        (Orchestrator / Scheduler)                       │
├─────────┬──────────┬──────────────┬────────────┬───────────────┬───────┤
│Exchange │          │  Strategies  │    Risk    │ Optimization  │Screen │
│         │  Data    │              │            │               │       │
│Hyperliq │ Manager  │ ┌──────────┐ │ ┌────────┐│ ┌───────────┐ │ ┌───┐ │
│Client   │          │ │StochRSI  │ │ │Position││ │  Optuna   │ │ │Trend│ │
│         │REST + WS │ │+SuperTrend│ │ │ Sizer  ││ │ Optimizer │ │ │Score│ │
│Orders   │          │ ├──────────┤ │ ├────────┤│ │           │ │ │     │ │
│Balance  │SQLite    │ │MACD+BB   │ │ │Circuit ││ │ Walk-Fwd  │ │ │Risk │ │
│Positions│Pipeline  │ │+RSI      │ │ │Breaker ││ │Backtester │ │ │Score│ │
│OHLCV    │          │ ├──────────┤ │ ├────────┤│ ├───────────┤ │ │     │ │
│WebSocket│          │ │BB Winner │ │ │Unified ││ │  HMM      │ │ │Hard │ │
│         │          │ │PRO       │ │ │Risk Mgr││ │  Regime   │ │ │Rules│ │
│         │          │ ├──────────┤ │ │        ││ │  Detector │ │ └───┘ │
│         │          │ │SuperTrend│ │ └────────┘│ └───────────┘ │       │
│         │          │ │+RSI      │ │            │               │       │
│         │          │ └──────────┘ │            │               │       │
├─────────┴──────────┴──────────────┴────────────┴───────────────┴───────┤
│                        indicators/technical.py                         │
│              RSI, MACD, BB, StochRSI, SuperTrend, ATR, ADX, etc.      │
├─────────────────────────────────────────────────────────────────────────┤
│                          models/database.py                            │
│                    SQLite (candles, trades, signals, opts)             │
└─────────────────────────────────────────────────────────────────────────┘
```

## Features

- **4 Trading Strategies** — Each using unique indicator combinations
- **AI Optimization** — Optuna TPE with walk-forward validation
- **Risk Management** — Quarter-Kelly sizing, circuit breaker, daily loss limits
- **Market Regime Detection** — GMM-based bull/bear/range classification
- **Pair Screening** — Multi-factor scoring with hard filtering rules
- **Real-time Data** — WebSocket + REST + SQLite persistence
- **Paper / Live Mode** — Toggle via environment variable

## Strategies

| # | Strategy | Type | Indicators | Entry Logic |
|---|----------|------|-----------|-------------|
| 1 | StochRSI + Supertrend | Momentum | StochRSI, Supertrend, ATR | Oversold crossover + bullish trend |
| 2 | MACD + BB + RSI | Momentum | MACD, Bollinger Bands, RSI | MACD cross + BB proximity + RSI filter |
| 3 | BB Winner PRO | Mean Reversion | Bollinger Bands, RSI, ATR, BWI | BB penetration + oversold + expanding bands |
| 4 | Supertrend + RSI | Trend Following | Supertrend, RSI, ADX, ATR | ST flip + RSI range + strong ADX |

## Project Structure

```
bot/
├── main.py                    # Entry point, bot startup, scheduler
├── config.py                  # Dataclass configuration (env vars)
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── exchange/
│   ├── hyperliquid_client.py  # Hyperliquid SDK wrapper
│   └── data_manager.py        # OHLCV data pipeline (WS + REST + SQLite)
├── strategies/
│   ├── base.py                # Abstract base strategy + Signal dataclass
│   ├── stochrsi_supertrend.py # Strategy 1
│   ├── macd_bb_rsi.py         # Strategy 2
│   ├── bb_winner_pro.py       # Strategy 3
│   └── supertrend_rsi.py      # Strategy 4
├── indicators/
│   └── technical.py           # All technical indicators (pure pandas/numpy)
├── risk/
│   ├── position_sizer.py      # Quarter-Kelly position sizing
│   ├── circuit_breaker.py     # Consecutive loss circuit breaker
│   └── risk_manager.py        # Unified risk checks
├── optimization/
│   ├── optimizer.py           # Optuna-based parameter optimization
│   ├── backtester.py          # Walk-forward backtesting engine
│   └── regime_detector.py     # GMM market regime detection
├── screening/
│   └── pair_screener.py       # TrendScore + RiskScore pair screening
├── models/
│   └── database.py            # SQLite models (trades, candles, signals, optimizations)
└── utils/
    ├── logger.py              # Loguru logging setup
    └── helpers.py             # Utility functions (time, math, retry)
```

## Setup

### 1. Install Dependencies

```bash
cd bot/
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
# Required for live trading (leave empty for paper mode)
WALLET_PRIVATE_KEY=your_private_key_here
WALLET_ADDRESS=your_wallet_address_here

# Trading mode: "paper" (testnet) or "live" (mainnet)
TRADING_MODE=paper

# Risk parameters (defaults shown)
MAX_RISK_PER_TRADE_PCT=1.5
MAX_DAILY_RISK_PCT=7.0
MAX_CONCURRENT_POSITIONS=5
MAX_CAPITAL_DEPLOYED_PCT=50.0
CIRCUIT_BREAKER_LOSSES=5
CIRCUIT_BREAKER_PAUSE_MINUTES=30

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/bot.log

# Data
DEFAULT_TIMEFRAME=1h

# Optimization
OPTUNA_N_TRIALS=200
```

### 3. Run the Bot

```bash
# Paper mode (default — uses Hyperliquid testnet)
python main.py

# Live mode (uses Hyperliquid mainnet with real funds)
TRADING_MODE=live python main.py

# Trade specific pairs
python main.py --pairs BTC,ETH,SOL
```

### 4. Run Optimization Only

```bash
# Optimize all strategy parameters and exit
python main.py --optimize

# With custom trial count
OPTUNA_N_TRIALS=500 python main.py --optimize
```

## Risk Management

| Parameter | Default | Description |
|-----------|---------|-------------|
| Max Risk Per Trade | 1.5% | Maximum equity risked per trade |
| Max Daily Risk | 7.0% | Maximum daily loss before trading stops |
| Max Concurrent Positions | 5 | Maximum open positions at once |
| Max Capital Deployed | 50% | Maximum % of equity in open positions |
| Circuit Breaker | 5 losses | Consecutive losses to trigger pause |
| Circuit Breaker Pause | 30 min | Duration of trading pause |
| Position Sizing | Quarter-Kelly | Kelly criterion × 0.25 |

## Optimization

The bot uses [Optuna](https://optuna.org/) with a TPE (Tree-structured Parzen Estimator) sampler
to find optimal strategy parameters:

- **Walk-forward validation**: 60-day training / 30-day validation windows
- **Multi-split**: 3 splits by default for robustness
- **Multi-objective**: `score = 0.6 × Sharpe - 0.4 × |MaxDrawdown|/100`
- **Minimum trades**: Splits with fewer than 20 trades are penalized
- **Persistence**: Best parameters saved to SQLite and auto-loaded on startup

## Pair Screening

Pairs are scored on two dimensions:

**TrendScore** (60% weight):
- ADX (trend strength): 30%
- Volume trend: 25%
- Momentum (ROC): 25%
- Volatility: 20%

**RiskScore** (40% weight):
- Liquidity: 25%
- Volatility risk: 25%
- Spread: 20%
- Correlation: 15%
- Listing age: 15%

**Hard filters** eliminate pairs that don't meet minimum volume, spread, or age requirements.

## Technical Indicators

All indicators are implemented from scratch using pandas/numpy (no pandas-ta dependency):

RSI, Stochastic RSI, MACD, Bollinger Bands, Supertrend, ATR, ADX, DMI (+DI/-DI),
Aroon, VWAP, OBV, CCI, Williams %R, EMA, SMA, DEMA, WMA, Momentum, ROC

## Development

```bash
# Install in development mode
pip install -e .

# Run with debug logging
LOG_LEVEL=DEBUG python main.py

# Run a single strategy backtest
python -c "
from strategies.macd_bb_rsi import MACDBBRSIStrategy
from optimization.backtester import Backtester
import pandas as pd
# ... load data and run
"
```

## Disclaimer

**This software is for educational purposes only.** Trading cryptocurrencies involves
significant risk of loss. Always test with paper mode first. Past performance does not
guarantee future results. Use at your own risk.

## License

MIT
