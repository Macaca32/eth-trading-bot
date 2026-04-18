"""
Circuit breaker logic.

Monitors consecutive losses and triggers a trading pause when
the threshold is exceeded. Prevents runaway losses during
adverse market conditions.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from config import RiskConfig


class CircuitBreaker:
    """
    Circuit breaker that pauses trading after a configurable
    number of consecutive losses.

    Features:
      - Configurable loss threshold and pause duration
      - Manual override to force-open or force-close
      - Persistent state across checks
    """

    def __init__(self, config: RiskConfig) -> None:
        self._config = config
        self._consecutive_losses: int = 0
        self._pause_until: Optional[float] = None  # Unix timestamp (seconds)
        self._total_triggers: int = 0
        self._is_manual_override: bool = False

    @property
    def is_tripped(self) -> bool:
        """Check if the circuit breaker is currently active (tripped)."""
        if self._is_manual_override:
            return False
        if self._pause_until is not None:
            if time.time() < self._pause_until:
                return True
            else:
                # Pause expired, reset
                self._pause_until = None
                logger.info("Circuit breaker pause expired — trading resumed")
                return False
        return False

    @property
    def consecutive_losses(self) -> int:
        return self._consecutive_losses

    @property
    def pause_remaining_seconds(self) -> float:
        """Seconds remaining in the current pause (0 if not paused)."""
        if self._pause_until is None:
            return 0.0
        remaining = self._pause_until - time.time()
        return max(0.0, remaining)

    @property
    def total_triggers(self) -> int:
        return self._total_triggers

    def update(self, pnl: float) -> None:
        """
        Update the circuit breaker with the result of a closed trade.

        Args:
            pnl: Profit/Loss of the trade (positive = win, negative = loss).
        """
        if pnl < 0:
            self._consecutive_losses += 1
            logger.debug(
                "Circuit breaker: loss recorded (consecutive={}/{})",
                self._consecutive_losses, self._config.circuit_breaker_losses,
            )

            if (self._consecutive_losses >= self._config.circuit_breaker_losses
                    and self._pause_until is None):
                self._trigger()
        else:
            if self._consecutive_losses > 0:
                logger.debug(
                    "Circuit breaker: win resets consecutive losses (was {})",
                    self._consecutive_losses,
                )
            self._consecutive_losses = 0

    def check(self) -> tuple[bool, str]:
        """
        Check if trading is allowed.

        Returns:
            (is_allowed, reason) — if not allowed, reason explains why.
        """
        if self._is_manual_override:
            return True, "Manual override active"

        if self.is_tripped:
            remaining = self.pause_remaining_seconds
            mins = int(remaining // 60)
            secs = int(remaining % 60)
            return False, (
                f"Circuit breaker active: {self._consecutive_losses} consecutive losses. "
                f"Pause remaining: {mins}m {secs}s"
            )

        return True, "OK"

    def force_open(self) -> None:
        """Manually override the circuit breaker to allow trading."""
        self._is_manual_override = True
        logger.warning("Circuit breaker: manual override — trading FORCE OPEN")

    def force_close(self) -> None:
        """Manually trip the circuit breaker to stop trading."""
        self._is_manual_override = False
        self._trigger()
        logger.warning("Circuit breaker: manually TRIPPED")

    def reset(self) -> None:
        """Reset the circuit breaker state completely."""
        self._consecutive_losses = 0
        self._pause_until = None
        self._is_manual_override = False
        logger.info("Circuit breaker: RESET")

    def _trigger(self) -> None:
        """Activate the circuit breaker pause."""
        pause_seconds = self._config.circuit_breaker_pause_minutes * 60
        self._pause_until = time.time() + pause_seconds
        self._total_triggers += 1
        logger.warning(
            "CIRCUIT BREAKER TRIPPED: {} consecutive losses → "
            "pausing for {} minutes (trigger #{})",
            self._consecutive_losses,
            self._config.circuit_breaker_pause_minutes,
            self._total_triggers,
        )

    def __repr__(self) -> str:
        status = "TRIPPED" if self.is_tripped else "CLOSED"
        return (
            f"CircuitBreaker(status={status}, "
            f"losses={self._consecutive_losses}/{self._config.circuit_breaker_losses}, "
            f"triggers={self._total_triggers})"
        )
