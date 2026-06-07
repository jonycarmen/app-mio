"""
Pairs trading / spread arbitrage strategy for BTC and XRP.

Logic:
  1. Calculate log-ratio = log(BTC_price / XRP_price)
  2. Compute rolling Z-score of the ratio
  3. Z-score > +threshold  → BTC overvalued vs XRP  → sell BTC, buy XRP
  4. Z-score < -threshold  → XRP overvalued vs BTC  → sell XRP, buy BTC
  5. |Z-score| < exit_threshold → close position
"""

import numpy as np
import pandas as pd
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class Signal(Enum):
    NONE = "none"
    BUY_XRP_SELL_BTC = "buy_xrp_sell_btc"
    BUY_BTC_SELL_XRP = "buy_btc_sell_xrp"
    EXIT = "exit"


@dataclass
class StrategyConfig:
    window: int = 60          # candles for rolling mean/std
    entry_z: float = 2.0      # Z-score to open position
    exit_z: float = 0.5       # Z-score to close position
    max_drawdown_pct: float = 5.0   # stop-loss: % portfolio drop


class SpreadStrategy:
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.ratios: list[float] = []
        self.current_signal = Signal.NONE

    def update(self, btc_price: float, xrp_price: float) -> Signal:
        ratio = np.log(btc_price / xrp_price)
        self.ratios.append(ratio)

        if len(self.ratios) < self.config.window:
            logger.debug(f"Warming up: {len(self.ratios)}/{self.config.window} candles")
            return Signal.NONE

        series = pd.Series(self.ratios[-self.config.window:])
        mean = series.mean()
        std = series.std()

        if std == 0:
            return Signal.NONE

        z = (ratio - mean) / std
        logger.info(f"BTC=${btc_price:,.2f} XRP=${xrp_price:.4f} ratio={ratio:.4f} Z={z:.3f}")

        # Exit open position
        if self.current_signal != Signal.NONE and abs(z) < self.config.exit_z:
            self.current_signal = Signal.EXIT
            return Signal.EXIT

        # Open new position
        if self.current_signal == Signal.NONE or self.current_signal == Signal.EXIT:
            if z > self.config.entry_z:
                self.current_signal = Signal.BUY_XRP_SELL_BTC
                return Signal.BUY_XRP_SELL_BTC
            elif z < -self.config.entry_z:
                self.current_signal = Signal.BUY_BTC_SELL_XRP
                return Signal.BUY_BTC_SELL_XRP

        return Signal.NONE

    def reset_signal(self):
        self.current_signal = Signal.NONE
