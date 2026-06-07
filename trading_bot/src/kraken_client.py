"""
Kraken API client wrapper using ccxt.
"""

import ccxt
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class KrakenClient:
    def __init__(self, api_key: str, api_secret: str, paper_mode: bool = False):
        self.paper_mode = paper_mode
        self.exchange = ccxt.kraken({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        })

    def fetch_ticker(self, symbol: str) -> dict:
        return self.exchange.fetch_ticker(symbol)

    def fetch_ohlcv(self, symbol: str, timeframe: str = "1m", limit: int = 100) -> list:
        return self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    def fetch_balance(self) -> dict:
        if self.paper_mode:
            return {"USD": {"free": 2500.0}, "BTC": {"free": 0.0}, "XRP": {"free": 0.0}}
        return self.exchange.fetch_balance()

    def create_market_order(self, symbol: str, side: str, amount: float) -> Optional[dict]:
        if self.paper_mode:
            ticker = self.fetch_ticker(symbol)
            price = ticker["last"]
            logger.info(f"[PAPER] {side.upper()} {amount:.6f} {symbol} @ ${price:,.4f}")
            return {"id": "paper", "status": "closed", "price": price, "amount": amount}
        try:
            order = self.exchange.create_market_order(symbol, side, amount)
            logger.info(f"ORDER {side.upper()} {amount:.6f} {symbol} → id={order['id']}")
            return order
        except ccxt.InsufficientFunds as e:
            logger.error(f"Insufficient funds: {e}")
        except ccxt.NetworkError as e:
            logger.error(f"Network error: {e}")
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error: {e}")
        return None

    def get_min_order_size(self, symbol: str) -> float:
        """Return Kraken minimum order sizes."""
        minimums = {
            "BTC/USD": 0.0001,
            "XRP/USD": 10.0,
        }
        return minimums.get(symbol, 0.001)
