import argparse
import os
import sys

from dotenv import load_dotenv

from tradingagents.brokers.alpaca_broker import AlpacaBroker
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph as JatayuCoreGraph
from tradingagents.notifiers.telegram_notifier import TelegramNotifier
from tradingagents.scheduler import TradingScheduler

load_dotenv()


def build_config() -> dict:
    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = "deepseek"
    config["deep_think_llm"] = "deepseek-chat"
    config["quick_think_llm"] = "deepseek-chat"
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
    broker = AlpacaBroker(notifier=notifier if notifier.enabled else None)
    notifiers: list = []
    if notifier.enabled:
        notifiers.append(notifier)
    if broker.enabled:
        notifiers.append(broker)

    ta = JatayuCoreGraph(
        debug=not args.quiet,
        config=config,
        notifiers=notifiers,
    )

    trade_date = args.date or "2024-05-10"
    final_state, signal = ta.propagate(args.ticker, trade_date)
    print(signal)


def _daemonize():
    pid = os.fork()
    if pid > 0:
        sys.exit(0)
    os.setsid()
    pid = os.fork()
    if pid > 0:
        sys.exit(0)
    sys.stdout.flush()
    sys.stderr.flush()
    with open("/dev/null", "r") as f:
        os.dup2(f.fileno(), sys.stdin.fileno())
    with open("/dev/null", "w") as f:
        os.dup2(f.fileno(), sys.stdout.fileno())
        os.dup2(f.fileno(), sys.stderr.fileno())


def cmd_scheduler(args: argparse.Namespace) -> None:
    if args.daemon:
        _daemonize()

    config = build_config()
    tickers = args.tickers.split(",") if args.tickers else ["NVDA", "AAPL", "SPY"]

    scheduler = TradingScheduler(
        tickers=tickers,
        config=config,
        interval_hours=args.interval,
    )
    scheduler.start()


def main() -> None:
    parser = argparse.ArgumentParser(description="JatayuCore — Multi-Agent AI Trading Framework")
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
    sched_p.add_argument("--interval", type=int, default=3, help="Hours between runs (default: 3)")
    sched_p.add_argument("--daemon", "-D", action="store_true", help="Fork to background")
    sched_p.set_defaults(func=cmd_scheduler)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
