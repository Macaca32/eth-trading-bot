# ETH Crypto Trading Bot

A decentralized, AI-optimized cryptocurrency trading bot built for **Hyperliquid DEX** — no KYC required. Trades ETH spot pairs using 4 battle-tested strategies with continuous parameter optimization.

![Trading Dashboard](https://img.shields.io/badge/Dashboard-Next.js_16-000?style=flat-square&logo=nextdotjs)
![Bot Core](https://img.shields.io/badge/Bot-Python-3776AB?style=flat-square&logo=python)
![Exchange](https://img.shields.io/badge/Exchange-Hyperliquid-00D395?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                NEXT.JS DASHBOARD (Port 3000)         │
│  Overview · Strategies · AI Optimizer · Pair Screener │
│  Trade Log · Risk Monitor · Settings                  │
├─────────────────────────────────────────────────────┤
│               PYTHON BOT CORE (Port 3003)            │
│                                                      │
│  ┌──────────┐  ┌───────────┐  ┌──────────────────┐ │
│  │ Strategy  │  │ AI Optuna │  │ Risk Manager     │ │
│  │ Engine    │  │ Optimizer │  │ (Kelly, Circuit  │ │
│  │ (4 strats)│  │ (weekly)  │  │  Breaker, Limits)│ │
│  └────┬─────┘  └─────┬─────┘  └────────┬─────────┘ │
│       └───────────────┼─────────────────┘            │
│                       ↓                              │
│  ┌─────────────────────────────────────────────────┐ │
│  │         Signal Aggregator + Order Manager        │ │
│  └──────────────────────────┬──────────────────────┘ │
│                              ↓                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │       hyperliquid-python-sdk                     │ │
│  │  REST + WebSocket (OHLCV, Orders, Account)       │ │
│  └──────────────────────────┬──────────────────────┘ │
└─────────────────────────────┼───────────────────────┘
                              ↓
                    ┌─────────────────┐
                    │   Hyperliquid    │
                    │  (DEX, No KYC)   │
                    └─────────────────┘
```

---

## Features

- **4 Trading Strategies**: StochRSI+Supertrend, MACD+BB+RSI, BB Winner PRO, Supertrend+RSI
- **AI Parameter Optimization**: Optuna with Bayesian optimization and walk-forward validation
- **Market Regime Detection**: GMM-based classification (trending, ranging, volatile)
- **Dynamic Pair Screening**: Real-time TrendScore and RiskScore for all ETH pairs
- **Comprehensive Risk Management**: Quarter-Kelly sizing, circuit breakers, daily loss limits
- **Paper Trading Mode**: Identical simulation on Hyperliquid testnet
- **Real-Time Dashboard**: Next.js 16 with live charts, signal feed, and strategy controls
- **Zero Gas Fees**: Hyperliquid's off-chain execution model
- **Lowest Fees**: 0.015% maker / 0.035% taker (cheapest in crypto)

---

## Quick Start

### Prerequisites
- Node.js 18+ and Bun
- Python 3.10+
- A Hyperliquid account (no KYC needed — just a wallet)

### 1. Clone and Install

```bash
git clone https://github.com/Macaca32/eth-trading-bot.git
cd eth-trading-bot
```

#### Frontend (Dashboard)

```bash
cd web
bun install
bun run dev
# Open http://localhost:3000
```

#### Backend (Trading Bot)

```bash
cd bot
pip install -r requirements.txt
```

### 2. Configure

Copy the example environment file and edit:

```bash
cd bot
cp .env.example .env
```

```env
# Trading Mode: "paper" or "live"
TRADING_MODE=paper

# Hyperliquid (use testnet for paper trading)
HL_BASE_URL=https://api.hyperliquid-testnet.xyz
HL_WS_URL=wss://api.hyperliquid-testnet.xyz/ws

# Wallet private key (NEVER share this)
WALLET_PRIVATE_KEY=your_private_key_here

# Risk Limits
MAX_RISK_PER_TRADE=0.015
MAX_DAILY_RISK=0.07
MAX_POSITIONS=5
MAX_CAPITAL_DEPLOYED=0.50
CIRCUIT_BREAKER_LOSSES=5
```

### 3. Run

```bash
cd bot
# Start the bot (paper trading by default)
python main.py

# Run with specific options
python main.py --mode paper --pairs ETH/USDT,ETH/BTC,ETH/SOL
python main.py --mode live --optimize
python main.py --backtest --days 90
```

---

## Strategies

| Strategy | Type | Best For | Parameters |
|----------|------|----------|------------|
| **StochRSI + Supertrend** | Momentum + Trend | Trending markets | 11 |
| **MACD + BB + RSI** | Multi-Indicator | Momentum shifts | 18+ |
| **BB Winner PRO** | Mean-Reversion | Ranging/volatile | 20+ |
| **Supertrend + RSI** | Trend-Following | Sustained trends | 7 |

All strategies are fully customizable. Parameters can be adjusted in the dashboard or optimized via the AI engine.

---

## AI Optimization

The bot uses **Optuna** with Tree-structured Parzen Estimator (TPE) for hyperparameter optimization:

- **Daily**: 50 trials per strategy on recent 60-day window
- **Weekly**: 200 trials with full walk-forward validation
- **Objectives**: Maximize Sharpe Ratio + Minimize Max Drawdown
- **Regime-aware**: Different parameters for trending/ranging/volatile markets

```bash
# Run optimization
python main.py --optimize --trials 200

# Backtest with walk-forward
python main.py --backtest --walk-forward --train-days 60 --test-days 30
```

---

## Risk Management

| Rule | Value | Description |
|------|-------|-------------|
| Max risk per trade | 1.5% | Quarter-Kelly position sizing |
| Max daily risk | 7% | Hard stop all trading |
| Max concurrent positions | 5 | Portfolio exposure limit |
| Max capital deployed | 50% | Reserve buffer |
| Circuit breaker | 5 losses | 30-min pause after consecutive losses |
| Stop-loss | 5x ATR | Volatility-adaptive |

---

## Project Structure

```
eth-trading-bot/
├── src/                     # Next.js 16 Dashboard
│   ├── app/                 # App router (single-page)
│   ├── components/          # React components
│   │   ├── views/           # 7 dashboard views
│   │   └── ui/              # Reusable UI components
│   └── lib/                 # Store, types, mock data, utils
├── bot/                     # Python Trading Bot
│   ├── exchange/            # Hyperliquid client + data pipeline
│   ├── strategies/          # 4 trading strategies
│   ├── indicators/          # 20+ technical indicators
│   ├── risk/                # Position sizing, circuit breakers
│   ├── optimization/        # Optuna optimizer, backtester
│   ├── screening/           # Pair screener (Trend + Risk scores)
│   ├── models/              # SQLite database models
│   └── utils/               # Logger, helpers
├── prisma/                  # Database schema (dashboard data)
└── docs/                    # Master plan document
```

---

## Cost

| Item | Monthly Cost |
|------|-------------|
| Trading fees (240 trades/day) | ~$36 |
| Gas fees | $0 |
| VPS hosting | $10-20 |
| **Total** | **~$46-56/month** |

---

## Disclaimer

This is experimental software. Trading cryptocurrencies involves substantial risk of loss. Past performance does not guarantee future results. Always start with paper trading and only risk capital you can afford to lose.

---

## License

MIT
