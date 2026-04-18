"""
Hyperliquid Trading Bot — Main Entry Point.

Starts the bot, initializes all components, and runs the main loop.

Usage:
    # Paper mode (default):
    python main.py

    # Live mode:
    TRADING_MODE=live python main.py

    # Run optimization only:
    python main.py --optimize

    # Custom config:
    python main.py --config /path/to/.env
"""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
from typing import Optional

from loguru import logger

from config import BotConfig, load_config, TradingMode
from exchange.data_manager import DataManager
from exchange.hyperliquid_client import HyperliquidClient
from models.database import Database
from optimization.optimizer import StrategyOptimizer
from optimization.regime_detector import RegimeDetector
from risk.risk_manager import RiskManager
from screening.pair_screener import PairScreener
from strategies.base import BaseStrategy, Signal
from strategies.stochrsi_supertrend import StochRSISupertrendStrategy
from strategies.macd_bb_rsi import MACDBBRSIStrategy
from strategies.bb_winner_pro import BBWinnerProStrategy
from strategies.supertrend_rsi import SupertrendRSIStrategy
from utils.helpers import utc_now
from utils.logger import setup_logger


# ---------------------------------------------------------------------------
# Strategy registry
# ---------------------------------------------------------------------------

STRATEGY_CLASSES: list[type[BaseStrategy]] = [
    StochRSISupertrendStrategy,
    MACDBBRSIStrategy,
    BBWinnerProStrategy,
    SupertrendRSIStrategy,
]


# ---------------------------------------------------------------------------
# Trading bot
# ---------------------------------------------------------------------------

class TradingBot:
    """
    Main trading bot orchestrator.

    Coordinates the exchange client, data pipeline, strategies,
    risk management, and optimization.
    """

    def __init__(self, config: BotConfig) -> None:
        self._config = config
        self._running = False
        self._shutdown_event = asyncio.Event()

        # Core components (initialized in start())
        self._db: Optional[Database] = None
        self._client: Optional[HyperliquidClient] = None
        self._data_manager: Optional[DataManager] = None
        self._risk_manager: Optional[RiskManager] = None
        self._screener: Optional[PairScreener] = None
        self._optimizer: Optional[StrategyOptimizer] = None
        self._regime_detector: Optional[RegimeDetector] = None

        # Active strategy instances
        self._strategies: list[BaseStrategy] = []
        self._approved_pairs: list[str] = [config.strategy.default_pair]

    async def start(self) -> None:
        """Initialize all components and start the main loop."""
        logger.info("=" * 60)
        logger.info("  Hyperliquid Trading Bot starting...")
        logger.info("  Mode: {}", self._config.exchange.trading_mode.value)
        logger.info("=" * 60)

        # Initialize components
        self._db = Database(self._config.data.sqlite_db_path)
        self._client = HyperliquidClient(self._config.exchange)
        self._data_manager = DataManager(
            self._client, self._db, self._config.data,
        )
        self._risk_manager = RiskManager(self._config.risk, self._db)
        self._screener = PairScreener(self._config.screener)
        self._optimizer = StrategyOptimizer(self._config.optimization, self._db)
        self._regime_detector = RegimeDetector(n_states=self._config.optimization.hmm_states)

        # Initialize strategies (try to load optimized params)
        for cls in STRATEGY_CLASSES:
            strategy = cls()
            # Try loading previously optimized parameters
            best_params = self._optimizer.load_best_params(strategy.name)
            if best_params:
                strategy.set_params(best_params)
                logger.info("Loaded optimized params for {}", strategy.name)
            self._strategies.append(strategy)
            logger.info("Strategy registered: {}", strategy.name)

        # Fetch initial data
        await self._fetch_initial_data()

        # Subscribe to real-time data
        await self._data_manager.start()
        for pair in self._approved_pairs:
            await self._data_manager.subscribe(pair, self._config.data.default_timeframe)

        # Start main loop
        self._running = True
        logger.info("Bot started successfully — entering main loop")

        try:
            await self._main_loop()
        except asyncio.CancelledError:
            logger.info("Main loop cancelled")
        finally:
            await self._shutdown()

    async def _fetch_initial_data(self) -> None:
        """Fetch historical candles for all approved pairs."""
        logger.info("Fetching initial historical data...")
        for pair in self._approved_pairs:
            count = await self._data_manager.fetch_and_store(
                pair, self._config.data.default_timeframe, self._config.data.candle_limit,
            )
            logger.info("  {} → {} new candles", pair, count)

    async def _main_loop(self) -> None:
        """
        Main bot loop.

        Runs strategy evaluation at the configured interval,
        checks risk, and executes trades.
        """
        loop_interval = self._config.schedule.strategy_loop_interval_sec
        screening_counter = 0

        while self._running:
            try:
                cycle_start = utc_now()

                # 1. Periodic pair screening (every N cycles)
                screening_counter += 1
                screening_cycles = int(
                    self._config.schedule.screening_interval_sec / loop_interval
                )
                if screening_cycles > 0 and screening_counter >= screening_cycles:
                    await self._run_screening()
                    screening_counter = 0

                # 2. Check risk status
                cb_ok, cb_reason = self._risk_manager.circuit_breaker.check()
                if not cb_ok:
                    logger.debug("Circuit breaker active: {}", cb_reason)
                    await asyncio.sleep(loop_interval)
                    continue

                # 3. Evaluate strategies
                await self._evaluate_strategies()

                # 4. Sleep until next cycle
                elapsed = (utc_now() - cycle_start).total_seconds()
                sleep_time = max(0, loop_interval - elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

            except Exception as exc:
                logger.error("Error in main loop: {}", exc)
                await asyncio.sleep(loop_interval)

    async def _evaluate_strategies(self) -> None:
        """Run all strategies on all approved pairs."""
        assert self._client is not None
        assert self._data_manager is not None
        assert self._risk_manager is not None

        for pair in self._approved_pairs:
            df = self._data_manager.get_candles_df(
                pair, self._config.data.default_timeframe, self._config.data.candle_limit,
            )

            if df.empty or len(df) < 50:
                continue

            for strategy in self._strategies:
                try:
                    if len(df) < strategy.required_candle_count():
                        continue

                    signals = strategy.calculate_signals(df)

                    for signal in signals:
                        # Skip low-confidence signals
                        if signal.confidence < self._config.strategy.minimum_confidence:
                            logger.debug(
                                "Signal rejected (low confidence): {} {} conf={:.2f}",
                                pair, strategy.name, signal.confidence,
                            )
                            continue

                        # Ensure pair is set
                        if not signal.pair:
                            signal.pair = pair

                        # Store signal in database
                        self._db.insert_signal({
                            "pair": signal.pair,
                            "strategy": signal.strategy,
                            "direction": signal.direction,
                            "confidence": signal.confidence,
                            "entry_price": signal.entry_price,
                            "stop_loss": signal.stop_loss,
                            "take_profit": signal.take_profit,
                            "timestamp": signal.timestamp,
                        })

                        # Risk assessment
                        assessment = await self._risk_manager.assess(
                            self._client,
                            signal.direction,
                            signal.entry_price,
                            signal.stop_loss,
                        )

                        if not assessment.allowed:
                            logger.debug(
                                "Trade blocked by risk: {} {} — {}",
                                pair, strategy.name, assessment.reason,
                            )
                            continue

                        # Execute trade
                        await self._execute_trade(signal, assessment.position_size)

                except Exception as exc:
                    logger.error(
                        "Strategy error ({} on {}): {}",
                        strategy.name, pair, exc,
                    )

    async def _execute_trade(self, signal: Signal, pos_size) -> None:
        """
        Execute a trade based on a signal.

        Args:
            signal: The trading signal.
            pos_size: PositionSize from risk assessment.
        """
        assert self._client is not None
        assert self._db is not None
        assert self._risk_manager is not None

        from exchange.hyperliquid_client import OrderSide, OrderType

        side = OrderSide.BUY if signal.direction == "long" else OrderSide.SELL

        logger.info(
            "EXECUTING {} {} — {} | entry={:.6f} sl={:.6f} tp={:.6f} "
            "qty={:.6f} conf={:.2f}",
            signal.direction.upper(), signal.pair, signal.strategy,
            signal.entry_price, signal.stop_loss, signal.take_profit,
            pos_size.quantity, signal.confidence,
        )

        result = await self._client.place_order(
            coin=signal.pair,
            side=side,
            size=pos_size.quantity,
            order_type=OrderType.MARKET,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
        )

        if result.success:
            # Record trade in database
            self._db.insert_trade({
                "pair": signal.pair,
                "strategy": signal.strategy,
                "direction": signal.direction,
                "entry_price": signal.entry_price,
                "quantity": pos_size.quantity,
                "status": "open",
                "entry_timestamp": signal.timestamp,
            })
            logger.info(
                "Order filled: {} {} qty={:.6f} (id={})",
                signal.direction, signal.pair, pos_size.quantity, result.order_id,
            )
        else:
            logger.error(
                "Order failed: {} {} — {}",
                signal.direction, signal.pair, result.error,
            )

    async def _run_screening(self) -> None:
        """Run pair screening to update the approved pairs list."""
        assert self._data_manager is not None

        logger.info("Running pair screening...")
        pairs_data: dict[str, pd.DataFrame] = {}
        for pair in self._approved_pairs:
            df = self._data_manager.get_candles_df(
                pair, self._config.data.default_timeframe, self._config.data.candle_limit,
            )
            if not df.empty:
                pairs_data[pair] = df

        if not pairs_data:
            return

        scores = self._screener.screen(pairs_data)
        self._approved_pairs = [s.pair for s in scores if s.passed]

        for s in scores[:5]:
            logger.info(
                "  {} → trend={:.1f}, risk={:.1f}, combined={:.1f}, passed={}",
                s.pair, s.trend_score, s.risk_score, s.combined, s.passed,
            )

    async def _run_optimization(self) -> None:
        """Run parameter optimization for all strategies."""
        assert self._data_manager is not None
        assert self._optimizer is not None

        logger.info("Running strategy optimization...")
        pair = self._config.strategy.default_pair
        df = self._data_manager.get_candles_df(
            pair, self._config.data.default_timeframe, self._config.data.candle_limit,
        )

        if df.empty:
            logger.error("No data available for optimization")
            return

        for cls in STRATEGY_CLASSES:
            try:
                result = self._optimizer.optimize(cls, df)
                logger.info(
                    "  {} → best_score={:.4f}, params={}",
                    result["strategy"], result["best_score"], result["best_params"],
                )

                # Apply best params to active strategy
                for s in self._strategies:
                    if s.name == result["strategy"]:
                        s.set_params(result["best_params"])
                        logger.info("  Updated active strategy params for {}", s.name)

            except Exception as exc:
                logger.error("Optimization failed for {}: {}", cls.__name__, exc)

    async def _shutdown(self) -> None:
        """Gracefully shut down all components."""
        logger.info("Shutting down...")

        if self._data_manager:
            await self._data_manager.stop()

        if self._client:
            await self._client.close()

        self._running = False
        logger.info("Bot shutdown complete")

    def request_shutdown(self) -> None:
        """Request a graceful shutdown from the main loop."""
        self._running = False
        self._shutdown_event.set()
        logger.info("Shutdown requested")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Hyperliquid Trading Bot")
    parser.add_argument(
        "--optimize", action="store_true",
        help="Run optimization only, then exit",
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="Path to .env file (default: .env in project root)",
    )
    parser.add_argument(
        "--pairs", type=str, default=None,
        help="Comma-separated list of pairs to trade (e.g. 'BTC,ETH,SOL')",
    )
    return parser.parse_args()


async def async_main() -> None:
    """Async main entry point."""
    args = parse_args()

    # Load configuration
    config = load_config()

    # Override pairs from CLI
    if args.pairs:
        config.strategy.default_pair = args.pairs.split(",")[0]

    # Setup logging
    setup_logger(
        log_level=config.log_level.value,
        log_file=config.log_file,
    )

    bot = TradingBot(config)

    # Register signal handlers for graceful shutdown
    def _signal_handler(sig, frame):
        logger.info("Received signal {} — shutting down...", sig)
        bot.request_shutdown()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    if args.optimize:
        # Optimization-only mode
        db = Database(config.data.sqlite_db_path)
        client = HyperliquidClient(config.exchange)
        data_manager = DataManager(client, db, config.data)

        await data_manager.start()
        pair = config.strategy.default_pair
        count = await data_manager.fetch_and_store(
            pair, config.data.default_timeframe, config.data.candle_limit,
        )

        if count == 0:
            logger.error("No data available for optimization")
            await data_manager.stop()
            await client.close()
            return

        optimizer = StrategyOptimizer(config.optimization, db)
        df = data_manager.get_candles_df(pair, config.data.default_timeframe, config.data.candle_limit)

        for cls in STRATEGY_CLASSES:
            try:
                result = optimizer.optimize(cls, df)
                logger.info(
                    "Optimization result for {}:\n"
                    "  Score: {:.4f}\n"
                    "  Sharpe: {:.2f}\n"
                    "  Max Drawdown: {:.2f}%\n"
                    "  Total Return: {:.2f}%\n"
                    "  Trades: {}\n"
                    "  Params: {}",
                    result["strategy"],
                    result["best_score"],
                    result["best_trial_attrs"].get("sharpe", 0),
                    result["best_trial_attrs"].get("max_drawdown", 0),
                    result["best_trial_attrs"].get("total_return", 0),
                    result["best_trial_attrs"].get("total_trades", 0),
                    result["best_params"],
                )
            except Exception as exc:
                logger.error("Optimization failed for {}: {}", cls.__name__, exc)

        await data_manager.stop()
        await client.close()
    else:
        # Normal bot mode
        await bot.start()


def main() -> None:
    """Synchronous entry point."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")


if __name__ == "__main__":
    main()
