"""
Main trading bot loop — BTC/XRP spread arbitrage on Kraken.
"""

import os
import time
import logging
import yaml
from pathlib import Path
from dotenv import load_dotenv

from kraken_client import KrakenClient
from strategy import SpreadStrategy, StrategyConfig, Signal
from risk_manager import RiskManager, RiskConfig

load_dotenv()

# ─── Logging ──────────────────────────────────────────────────────────────────
log_dir = Path("/app/logs") if Path("/app/logs").exists() else Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / "bot.log"),
    ],
)
logger = logging.getLogger(__name__)


def load_config(path: str = "config.yaml") -> dict:
    config_path = Path(path)
    if not config_path.exists():
        config_path = Path("/app/config.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_portfolio_value(client: KrakenClient, btc_price: float, xrp_price: float) -> float:
    balance = client.fetch_balance()
    usd = balance.get("USD", {}).get("free", 0)
    btc = balance.get("XBT", {}).get("free", 0) or balance.get("BTC", {}).get("free", 0)
    xrp = balance.get("XRP", {}).get("free", 0)
    return usd + btc * btc_price + xrp * xrp_price


def execute_signal(
    signal: Signal,
    client: KrakenClient,
    risk: RiskManager,
    btc_price: float,
    xrp_price: float,
    portfolio_value: float,
):
    size_usd = risk.position_size_usd(portfolio_value)

    if signal == Signal.BUY_XRP_SELL_BTC:
        btc_amount = size_usd / btc_price
        xrp_amount = size_usd / xrp_price
        min_btc = client.get_min_order_size("BTC/USD")
        min_xrp = client.get_min_order_size("XRP/USD")
        if btc_amount < min_btc or xrp_amount < min_xrp:
            logger.warning("Position too small for minimums, skipping.")
            return
        logger.info(f"SIGNAL: BUY XRP + SELL BTC | size=${size_usd:.2f}")
        client.create_market_order("BTC/USD", "sell", btc_amount)
        client.create_market_order("XRP/USD", "buy", xrp_amount)
        risk.open_trade()

    elif signal == Signal.BUY_BTC_SELL_XRP:
        btc_amount = size_usd / btc_price
        xrp_amount = size_usd / xrp_price
        min_btc = client.get_min_order_size("BTC/USD")
        min_xrp = client.get_min_order_size("XRP/USD")
        if btc_amount < min_btc or xrp_amount < min_xrp:
            logger.warning("Position too small for minimums, skipping.")
            return
        logger.info(f"SIGNAL: BUY BTC + SELL XRP | size=${size_usd:.2f}")
        client.create_market_order("XRP/USD", "sell", xrp_amount)
        client.create_market_order("BTC/USD", "buy", btc_amount)
        risk.open_trade()

    elif signal == Signal.EXIT:
        logger.info("SIGNAL: EXIT — closing position")
        balance = client.fetch_balance()
        btc = balance.get("XBT", {}).get("free", 0) or balance.get("BTC", {}).get("free", 0)
        xrp = balance.get("XRP", {}).get("free", 0)
        min_btc = client.get_min_order_size("BTC/USD")
        min_xrp = client.get_min_order_size("XRP/USD")
        if btc > min_btc:
            client.create_market_order("BTC/USD", "sell", btc)
        if xrp > min_xrp:
            client.create_market_order("XRP/USD", "sell", xrp)
        risk.close_trade()
        risk.reset_signal() if hasattr(risk, "reset_signal") else None


def main():
    logger.info("=" * 60)
    logger.info("  BTC/XRP Spread Arbitrage Bot — Kraken")
    logger.info("=" * 60)

    cfg = load_config()
    paper = cfg.get("paper_mode", True)
    interval = cfg.get("interval_seconds", 60)

    logger.info(f"Mode: {'PAPER (simulation)' if paper else '⚠ LIVE TRADING'}")
    logger.info(f"Interval: {interval}s")

    api_key = os.getenv("KRAKEN_API_KEY", "")
    api_secret = os.getenv("KRAKEN_API_SECRET", "")

    if not paper and (not api_key or not api_secret):
        logger.error("KRAKEN_API_KEY and KRAKEN_API_SECRET are required for live trading.")
        return

    client = KrakenClient(api_key, api_secret, paper_mode=paper)

    strategy = SpreadStrategy(StrategyConfig(
        window=cfg.get("window", 60),
        entry_z=cfg.get("entry_z", 2.0),
        exit_z=cfg.get("exit_z", 0.5),
    ))

    risk = RiskManager(RiskConfig(
        max_position_pct=cfg.get("max_position_pct", 20.0),
        max_daily_loss_pct=cfg.get("max_daily_loss_pct", 5.0),
        max_open_trades=cfg.get("max_open_trades", 1),
    ))

    # Warm up with historical candles
    logger.info("Fetching historical data to warm up strategy...")
    try:
        btc_candles = client.fetch_ohlcv("BTC/USD", "1m", limit=strategy.config.window + 10)
        xrp_candles = client.fetch_ohlcv("XRP/USD", "1m", limit=strategy.config.window + 10)
        for (_, _, _, _, btc_close, _), (_, _, _, _, xrp_close, _) in zip(btc_candles, xrp_candles):
            strategy.update(btc_close, xrp_close)
        logger.info("Warm-up complete.")
    except Exception as e:
        logger.warning(f"Could not warm up from history: {e}")

    # Initialize portfolio
    btc_ticker = client.fetch_ticker("BTC/USD")
    xrp_ticker = client.fetch_ticker("XRP/USD")
    portfolio = get_portfolio_value(client, btc_ticker["last"], xrp_ticker["last"])
    risk.set_initial_portfolio(portfolio)

    logger.info(f"Starting portfolio value: ${portfolio:,.2f}")
    logger.info("Bot is running. Press Ctrl+C to stop.\n")

    while True:
        try:
            btc_ticker = client.fetch_ticker("BTC/USD")
            xrp_ticker = client.fetch_ticker("XRP/USD")
            btc_price = btc_ticker["last"]
            xrp_price = xrp_ticker["last"]

            portfolio_value = get_portfolio_value(client, btc_price, xrp_price)

            if not risk.evaluate(portfolio_value):
                time.sleep(interval)
                continue

            signal = strategy.update(btc_price, xrp_price)

            if signal != Signal.NONE:
                execute_signal(signal, client, risk, btc_price, xrp_price, portfolio_value)
                strategy.reset_signal()

            pnl_pct = (portfolio_value - risk.initial_portfolio) / risk.initial_portfolio * 100
            logger.info(f"Portfolio: ${portfolio_value:,.2f} | PnL: {pnl_pct:+.2f}%")

        except KeyboardInterrupt:
            logger.info("Bot stopped by user.")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)

        time.sleep(interval)


if __name__ == "__main__":
    main()
