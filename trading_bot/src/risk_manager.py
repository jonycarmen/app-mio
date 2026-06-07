"""
Risk management: position sizing, stop-loss, daily loss limit.
"""

import logging
from dataclasses import dataclass, field
from datetime import date

logger = logging.getLogger(__name__)


@dataclass
class RiskConfig:
    max_position_pct: float = 20.0    # max % of portfolio per trade
    max_daily_loss_pct: float = 5.0   # halt trading if daily loss exceeds this
    max_open_trades: int = 1          # only 1 pair trade at a time


class RiskManager:
    def __init__(self, config: RiskConfig):
        self.config = config
        self.initial_portfolio: float = 0.0
        self.peak_portfolio: float = 0.0
        self.daily_start_value: float = 0.0
        self.today: date = date.today()
        self.open_trades: int = 0
        self.halted: bool = False

    def set_initial_portfolio(self, value: float):
        self.initial_portfolio = value
        self.peak_portfolio = value
        self.daily_start_value = value
        logger.info(f"Portfolio initialized: ${value:,.2f}")

    def check_daily_reset(self, portfolio_value: float):
        today = date.today()
        if today != self.today:
            self.today = today
            self.daily_start_value = portfolio_value
            self.halted = False
            logger.info(f"New trading day. Portfolio: ${portfolio_value:,.2f}")

    def evaluate(self, portfolio_value: float) -> bool:
        """Returns True if trading is allowed."""
        self.check_daily_reset(portfolio_value)

        if self.halted:
            logger.warning("Trading HALTED — daily loss limit reached.")
            return False

        if self.daily_start_value > 0:
            daily_loss_pct = (self.daily_start_value - portfolio_value) / self.daily_start_value * 100
            if daily_loss_pct >= self.config.max_daily_loss_pct:
                self.halted = True
                logger.error(f"HALT: daily loss {daily_loss_pct:.2f}% exceeds limit {self.config.max_daily_loss_pct}%")
                return False

        if self.open_trades >= self.config.max_open_trades:
            logger.debug("Max open trades reached, waiting for exit.")
            return False

        return True

    def position_size_usd(self, portfolio_value: float) -> float:
        """How much USD to allocate per side of the trade."""
        size = portfolio_value * (self.config.max_position_pct / 100)
        logger.info(f"Position size: ${size:,.2f} ({self.config.max_position_pct}% of ${portfolio_value:,.2f})")
        return size

    def open_trade(self):
        self.open_trades += 1

    def close_trade(self):
        self.open_trades = max(0, self.open_trades - 1)
