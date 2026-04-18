"""
Optuna-based parameter optimization.

Uses walk-forward backtesting as the objective function with
multi-objective optimisation: maximise Sharpe ratio, minimise drawdown.

Features:
  - TPE (Tree-structured Parzen Estimator) sampler
  - Walk-forward validation across multiple splits
  - Persistence of results to SQLite
  - Support for loading previously optimised parameters
"""

from __future__ import annotations

import time
from typing import Any, Optional, Type

import optuna
from loguru import logger

from config import OptimizationConfig
from models.database import Database
from optimization.backtester import Backtester, BacktestResult
from optimization.regime_detector import RegimeDetector
from strategies.base import BaseStrategy

# Suppress Optuna's verbose logging
optuna.logging.set_verbosity(optuna.logging.WARNING)


class StrategyOptimizer:
    """
    Optimizes strategy parameters using Optuna.

    The objective function:
      1. Samples parameters from the strategy's defined ranges
      2. Runs walk-forward backtesting
      3. Returns a composite score = sharpe_weight * Sharpe - drawdown_weight * |MaxDD|
    """

    def __init__(
        self,
        config: OptimizationConfig,
        db: Database,
    ) -> None:
        """
        Args:
            config: Optimization configuration.
            db: Database for persisting results.
        """
        self._config = config
        self._db = db
        self._backtester = Backtester(
            train_days=config.train_window_days,
            validation_days=config.validation_window_days,
            n_splits=config.n_splits,
        )
        self._regime_detector = RegimeDetector(n_states=config.hmm_states)

    def optimize(
        self,
        strategy_class: Type[BaseStrategy],
        df,
        n_trials: Optional[int] = None,
        study_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Run parameter optimization for a strategy.

        Args:
            strategy_class: The strategy class to optimize.
            df: OHLCV DataFrame for backtesting.
            n_trials: Number of Optuna trials (overrides config).
            study_name: Optional study name for storage.

        Returns:
            Dict with best_params, best_score, and study summary.
        """
        trials = n_trials or self._config.n_trials
        name = study_name or strategy_class.__name__

        logger.info(
            "Starting optimization for {} ({} trials, walk-forward: {}/{} days, {} splits)",
            name, trials,
            self._config.train_window_days, self._config.validation_window_days,
            self._config.n_splits,
        )

        # Fit regime detector on full data
        self._regime_detector.fit(df)

        # Check that strategy has param ranges
        default_strategy = strategy_class()
        param_ranges = default_strategy.get_param_ranges()
        if not param_ranges:
            logger.warning("Strategy {} has no param ranges defined — nothing to optimize", name)
            return {"best_params": default_strategy.get_params(), "best_score": 0.0}

        # Create Optuna study
        study = optuna.create_study(
            study_name=name,
            direction="maximize",
            sampler=optuna.samplers.TPE(seed=42),
        )

        # Define objective
        def objective(trial: optuna.Trial) -> float:
            # Sample parameters
            params: dict[str, Any] = {}
            for pname, (lo, hi) in param_ranges.items():
                if isinstance(lo, int) and isinstance(hi, int):
                    params[pname] = trial.suggest_int(pname, int(lo), int(hi))
                else:
                    params[pname] = trial.suggest_float(pname, float(lo), float(hi))

            # Create strategy with sampled params
            strategy = strategy_class(params=params)

            # Run backtest
            result = self._backtester.run(strategy, df)

            # Need minimum trades
            if result.total_trades < self._config.min_trades_per_split:
                return -10.0

            # Composite objective: weighted Sharpe - weighted drawdown
            score = (
                self._config.sharpe_weight * result.sharpe_ratio
                - self._config.drawdown_weight * abs(result.max_drawdown_pct) / 100.0
            )

            # Report metrics to Optuna
            trial.set_user_attr("sharpe", result.sharpe_ratio)
            trial.set_user_attr("max_drawdown", result.max_drawdown_pct)
            trial.set_user_attr("total_return", result.total_return_pct)
            trial.set_user_attr("total_trades", result.total_trades)
            trial.set_user_attr("win_rate", result.win_rate)
            trial.set_user_attr("profit_factor", result.profit_factor)

            return score

        # Run optimization
        study.optimize(objective, n_trials=trials, show_progress_bar=False)

        best_params = study.best_params
        best_value = study.best_value

        logger.info(
            "Optimization complete for {}: best_score={:.4f}, best_params={}",
            name, best_value, best_params,
        )

        # Save best result to database
        best_trial = study.best_trial
        self._save_result(
            strategy_name=name,
            params=best_params,
            sharpe=best_trial.user_attrs.get("sharpe", 0),
            max_drawdown=best_trial.user_attrs.get("max_drawdown", 0),
            total_return=best_trial.user_attrs.get("total_return", 0),
            n_trades=best_trial.user_attrs.get("total_trades", 0),
        )

        return {
            "strategy": name,
            "best_params": best_params,
            "best_score": best_value,
            "best_trial_attrs": dict(best_trial.user_attrs),
            "n_trials": len(study.trials),
        }

    def load_best_params(self, strategy_name: str) -> Optional[dict[str, Any]]:
        """
        Load the best previously optimized parameters from the database.

        Args:
            strategy_name: Name of the strategy.

        Returns:
            Dict of parameters, or None if no optimization exists.
        """
        result = self._db.get_best_optimization(strategy_name)
        if result is None:
            return None
        logger.info(
            "Loaded best params for {}: Sharpe={:.2f}, DD={:.2f}%",
            strategy_name, result["sharpe"], result["max_drawdown"],
        )
        return result["params"]

    def _save_result(
        self,
        strategy_name: str,
        params: dict[str, Any],
        sharpe: float,
        max_drawdown: float,
        total_return: float,
        n_trades: int,
    ) -> None:
        """Persist optimization result to the database."""
        self._db.save_optimization({
            "strategy": strategy_name,
            "params": params,
            "sharpe": sharpe,
            "max_drawdown": max_drawdown,
            "total_return": total_return,
            "n_trades": n_trades,
            "timestamp": int(time.time() * 1000),
        })
        logger.debug("Saved optimization result for {}", strategy_name)
