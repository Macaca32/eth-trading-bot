"""
Quarter-Kelly position sizing.

Calculates optimal position size based on:
  - Account equity
  - Maximum risk per trade (% of equity)
  - Stop-loss distance (price)
  - Kelly fraction multiplier (default: 0.25 = quarter-Kelly)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from loguru import logger

from config import RiskConfig
from utils.helpers import clamp


@dataclass
class PositionSize:
    """
    Result of position sizing calculation.

    Attributes:
        quantity:       Position size in asset units (coins).
        size_usd:       Position size in USD value.
        risk_usd:       Dollar amount at risk (equity * risk_pct).
        stop_distance:  Stop-loss distance as a fraction of entry price.
    """
    quantity: float
    size_usd: float
    risk_usd: float
    stop_distance: float


class PositionSizer:
    """
    Quarter-Kelly position sizer.

    Formula:
        risk_usd = equity * max_risk_pct / 100
        size_usd = risk_usd / stop_distance_frac
        quantity = size_usd / entry_price
        # Apply Kelly fraction
        final_size_usd = size_usd * kelly_fraction
        final_quantity = final_size_usd / entry_price
    """

    def __init__(self, config: RiskConfig) -> None:
        self._config = config

    def calculate(
        self,
        equity: float,
        entry_price: float,
        stop_loss: float,
        current_positions_value: float = 0.0,
        direction: str = "long",
    ) -> PositionSize:
        """
        Calculate the optimal position size.

        Args:
            equity: Total account equity in USD.
            entry_price: Entry price per unit of the asset.
            stop_loss: Stop-loss price per unit.
            current_positions_value: Total value of currently open positions (USD).
            direction: "long" or "short".

        Returns:
            PositionSize with quantity, size_usd, risk_usd, and stop_distance.
        """
        if entry_price <= 0:
            logger.warning("Invalid entry_price={}, returning zero position", entry_price)
            return PositionSize(quantity=0, size_usd=0, risk_usd=0, stop_distance=0)

        # Calculate stop distance as fraction of entry
        if direction == "long":
            stop_distance = (entry_price - stop_loss) / entry_price
        else:
            stop_distance = (stop_loss - entry_price) / entry_price

        if stop_distance <= 0:
            logger.warning(
                "Invalid stop distance (entry={}, sl={}, dir={}), using default {}%",
                entry_price, stop_loss, direction, self._config.default_stop_loss_pct,
            )
            stop_distance = self._config.default_stop_loss_pct / 100

        # Maximum risk in USD for this trade
        risk_usd = equity * (self._config.max_risk_per_trade_pct / 100)

        # Raw position size from risk
        raw_size_usd = risk_usd / stop_distance

        # Apply Kelly fraction (quarter-Kelly by default)
        sized_usd = raw_size_usd * self._config.kelly_fraction

        # Enforce capital deployment limit
        max_deploy = equity * (self._config.max_capital_deployed_pct / 100)
        remaining_deploy = max(0, max_deploy - current_positions_value)
        sized_usd = min(sized_usd, remaining_deploy)

        # Enforce min/max size limits
        sized_usd = clamp(sized_usd, self._config.min_position_size_usd, self._config.max_position_size_usd)

        # Calculate quantity
        quantity = sized_usd / entry_price

        logger.debug(
            "Position sizing: equity={:.2f}, entry={:.6f}, sl={:.6f}, "
            "stop_dist={:.4f}%, risk_usd={:.2f}, size_usd={:.2f}, qty={:.6f}",
            equity, entry_price, stop_loss, stop_distance * 100,
            risk_usd, sized_usd, quantity,
        )

        return PositionSize(
            quantity=quantity,
            size_usd=sized_usd,
            risk_usd=risk_usd,
            stop_distance=stop_distance,
        )
