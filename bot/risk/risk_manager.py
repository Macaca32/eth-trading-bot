"""
Unified risk management.

Combines position sizing, circuit breaking, and daily loss tracking
into a single interface that the main bot loop consults before
placing any trade.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from loguru import logger

from config import RiskConfig
from exchange.hyperliquid_client import AccountBalance, HyperliquidClient, Position
from models.database import Database
from risk.circuit_breaker import CircuitBreaker
from risk.position_sizer import PositionSizer, PositionSize
from utils.helpers import clamp


@dataclass
class RiskAssessment:
    """
    Result of a pre-trade risk check.

    Attributes:
        allowed:         Whether the trade is permitted.
        reason:          Human-readable reason if not allowed.
        position_size:   Calculated position size (if allowed).
        daily_pnl:       Current daily PnL.
        open_positions:  Number of currently open positions.
        deployed_pct:    Percentage of equity currently deployed.
    """
    allowed: bool
    reason: str
    position_size: Optional[PositionSize] = None
    daily_pnl: float = 0.0
    open_positions: int = 0
    deployed_pct: float = 0.0


class RiskManager:
    """
    Centralised risk manager.

    Performs all pre-trade checks:
      1. Circuit breaker status
      2. Daily loss limit
      3. Concurrent position limit
      4. Capital deployment limit
      5. Position sizing calculation
    """

    def __init__(self, config: RiskConfig, db: Database) -> None:
        self._config = config
        self._db = db
        self._position_sizer = PositionSizer(config)
        self._circuit_breaker = CircuitBreaker(config)
        self._daily_pnl_cache: float = 0.0
        self._cache_ts: float = 0.0

    # -- Properties ------------------------------------------------------

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        """Access the circuit breaker directly."""
        return self._circuit_breaker

    @property
    def position_sizer(self) -> PositionSizer:
        """Access the position sizer directly."""
        return self._position_sizer

    # -- Public API ------------------------------------------------------

    async def assess(
        self,
        client: HyperliquidClient,
        direction: str,
        entry_price: float,
        stop_loss: float,
    ) -> RiskAssessment:
        """
        Perform a full pre-trade risk assessment.

        Args:
            client: Exchange client to fetch balance/positions.
            direction: "long" or "short".
            entry_price: Planned entry price.
            stop_loss: Planned stop-loss price.

        Returns:
            RiskAssessment with allowed/reason and optionally a position size.
        """
        # 1. Circuit breaker
        cb_ok, cb_reason = self._circuit_breaker.check()
        if not cb_ok:
            logger.warning("Trade blocked by circuit breaker: {}", cb_reason)
            return RiskAssessment(allowed=False, reason=cb_reason)

        # 2. Fetch account info
        balance = await client.get_balance()
        positions = await client.get_positions()
        equity = balance.total_equity

        if equity <= 0:
            return RiskAssessment(
                allowed=False,
                reason=f"Insufficient equity: ${equity:.2f}",
            )

        # 3. Daily loss check
        daily_pnl = self._get_daily_pnl()
        daily_limit = equity * (self._config.max_daily_risk_pct / 100)

        if daily_pnl < -daily_limit:
            return RiskAssessment(
                allowed=False,
                reason=f"Daily loss limit reached: ${daily_pnl:.2f} / -${daily_limit:.2f}",
                daily_pnl=daily_pnl,
                open_positions=len(positions),
            )

        # 4. Concurrent position limit
        if len(positions) >= self._config.max_concurrent_positions:
            return RiskAssessment(
                allowed=False,
                reason=f"Max concurrent positions reached: {len(positions)}/{self._config.max_concurrent_positions}",
                daily_pnl=daily_pnl,
                open_positions=len(positions),
            )

        # 5. Capital deployment check
        current_deployed = sum(abs(p.size * p.entry_price) for p in positions)
        deployed_pct = (current_deployed / equity * 100) if equity > 0 else 0
        max_deploy = equity * (self._config.max_capital_deployed_pct / 100)

        if current_deployed >= max_deploy:
            return RiskAssessment(
                allowed=False,
                reason=f"Max capital deployed: {deployed_pct:.1f}%/{self._config.max_capital_deployed_pct}%",
                daily_pnl=daily_pnl,
                open_positions=len(positions),
                deployed_pct=deployed_pct,
            )

        # 6. Calculate position size
        pos_size = self._position_sizer.calculate(
            equity=equity,
            entry_price=entry_price,
            stop_loss=stop_loss,
            current_positions_value=current_deployed,
            direction=direction,
        )

        if pos_size.size_usd <= 0:
            return RiskAssessment(
                allowed=False,
                reason="Position size too small after risk constraints",
                daily_pnl=daily_pnl,
                open_positions=len(positions),
                deployed_pct=deployed_pct,
            )

        return RiskAssessment(
            allowed=True,
            reason="OK",
            position_size=pos_size,
            daily_pnl=daily_pnl,
            open_positions=len(positions),
            deployed_pct=deployed_pct,
        )

    def record_trade_result(self, pnl: float) -> None:
        """
        Record the result of a closed trade.

        Updates the circuit breaker state.
        """
        self._circuit_breaker.update(pnl)
        self._daily_pnl_cache = 0.0  # Force cache refresh
        self._cache_ts = 0.0

    def reset_daily(self) -> None:
        """Reset daily tracking (call at midnight UTC)."""
        self._daily_pnl_cache = 0.0
        self._cache_ts = 0.0
        logger.info("Risk manager: daily counters reset")

    # -- Internals -------------------------------------------------------

    def _get_daily_pnl(self) -> float:
        """Get daily PnL with a short cache (10s TTL)."""
        import time
        now = time.time()
        if now - self._cache_ts < 10:
            return self._daily_pnl_cache
        self._daily_pnl_cache = self._db.get_daily_pnl()
        self._cache_ts = now
        return self._daily_pnl_cache

    def __repr__(self) -> str:
        return (
            f"RiskManager("
            f"cb={self._circuit_breaker}, "
            f"max_positions={self._config.max_concurrent_positions}, "
            f"max_risk={self._config.max_risk_per_trade_pct}%)"
        )
