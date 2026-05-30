import argparse
import sys

from dotenv import load_dotenv

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.notifiers.telegram_notifier import TelegramNotifier
from tradingagents.scheduler import TradingScheduler

load_dotenv()


def build_config() -> dict:
    config = DEFAULT_CONFIG.copy()
    config["deep_think_llm"] = "gpt-5.4-mini"
    config["quick_think_llm"] = "gpt-5.4-mini"
    config["max_debate_rounds"] = 1
    config["data_vendors"] = {
        "core_stock_apis": "yfinance",
        "technical_indicators": "yfinance",
        "fundamental_data": "yfinance",
        "news_data": "yfinance",
    }
    return config


def cmd_run(args: argparse.Namespace) -> None:
    config = build_config()
    notifier = TelegramNotifier()
    notifiers = [notifier] if notifier.enabled else []

    ta = TradingAgentsGraph(
        debug=not args.quiet,
        config=config,
        notifiers=notifiers,
    )

    trade_date = args.date or "2024-05-10"
    final_state, signal = ta.propagate(args.ticker, trade_date)
    print(signal)


def cmd_scheduler(args: argparse.Namespace) -> None:
    config = build_config()
    tickers = args.tickers.split(",") if args.tickers else ["NVDA", "AAPL", "SPY"]

    scheduler = TradingScheduler(
        tickers=tickers,
        config=config,
        run_hour=args.hour,
        run_minute=args.minute,
    )
    scheduler.start()


def main() -> None:
    parser = argparse.ArgumentParser(description="TradingAgents")
    sub = parser.add_subparsers(dest="command", required=True)

    # Single run
    run_p = sub.add_parser("run", help="Run single analysis")
    run_p.add_argument("ticker", nargs="?", default="NVDA")
    run_p.add_argument("--date", "-d", help="Trade date (YYYY-MM-DD)")
    run_p.add_argument("--quiet", "-q", action="store_true", help="Suppress debug output")
    run_p.set_defaults(func=cmd_run)

    # Scheduler
    sched_p = sub.add_parser("schedule", help="Run scheduler daemon")
    sched_p.add_argument("--tickers", "-t", help="Comma-separated tickers")
    sched_p.add_argument("--hour", type=int, default=8, help="Run hour (UTC)")
    sched_p.add_argument("--minute", type=int, default=0, help="Run minute (UTC)")
    sched_p.set_defaults(func=cmd_scheduler)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
