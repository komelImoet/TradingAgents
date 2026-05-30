import logging
import time
from datetime import datetime, timezone
from typing import Optional

from tradingagents.brokers.alpaca_broker import AlpacaBroker
from tradingagents.circuit_breaker import CircuitBreaker
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.monitor import PositionMonitor
from tradingagents.notifiers.telegram_notifier import TelegramNotifier
from tradingagents.default_config import DEFAULT_CONFIG

logger = logging.getLogger(__name__)


def _is_market_open() -> bool:
    """Return False on weekends."""
    return datetime.now(timezone.utc).weekday() < 5


class TradingScheduler:
    def __init__(
        self,
        tickers: list[str],
        config: Optional[dict] = None,
        interval_hours: int = 3,
    ):
        self.tickers = tickers
        self.config = config or DEFAULT_CONFIG.copy()
        self.interval_hours = interval_hours

        self.circuit_breaker = CircuitBreaker()
        self.notifier = TelegramNotifier()
        self.broker = AlpacaBroker(
            notifier=self.notifier if self.notifier.enabled else None,
            circuit_breaker=self.circuit_breaker,
        )
        self.monitor = PositionMonitor(
            broker=self.broker,
            notifier=self.notifier,
            circuit_breaker=self.circuit_breaker,
        )
        self._last_run_ts: float = 0.0
        self._running = False

    def _should_run(self) -> bool:
        if not _is_market_open():
            return False

        elapsed = time.time() - self._last_run_ts
        return elapsed >= self.interval_hours * 3600

    def _run_pipeline(self) -> None:
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        self.notifier.send_info(
            "Scheduler", f"Running analysis for {len(self.tickers)} ticker(s)"
        )

        for ticker in self.tickers:
            try:
                logger.info("Running JatayuCore for %s at %s", ticker, now_str)

                notifiers = []
                if self.notifier.enabled:
                    notifiers.append(self.notifier)
                if self.broker.enabled:
                    notifiers.append(self.broker)

                ta = TradingAgentsGraph(
                    debug=False,
                    config=self.config,
                    notifiers=notifiers,
                )
                _, signal = ta.propagate(ticker, datetime.now(timezone.utc).strftime("%Y-%m-%d"))

                logger.info("Completed %s — signal: %s", ticker, signal)

            except Exception as e:
                logger.error("Failed to process %s: %s", ticker, e)
                self.notifier.send_error(ticker, str(e))

        self._last_run_ts = time.time()
        next_run = datetime.fromtimestamp(
            self._last_run_ts + self.interval_hours * 3600, tz=timezone.utc
        )
        self.notifier.send_info(
            "Scheduler",
            f"Run completed. Next run ~{next_run.strftime('%H:%M UTC')} "
            f"({self.interval_hrs_summary()})",
        )

    def interval_hrs_summary(self) -> str:
        h = self.interval_hours
        return f"every {h}h" if h < 24 else f"every {h//24}d"

    def start(self) -> None:
        self._running = True
        self.monitor.start()
        self.notifier.send_info(
            "JatayuCore",
            f"Scheduler started — {self.interval_hrs_summary()} for {', '.join(self.tickers)}",
        )
        logger.info(
            "Scheduler started: %s for %s",
            self.interval_hrs_summary(), ", ".join(self.tickers),
        )

        try:
            while self._running:
                if self._should_run():
                    self._run_pipeline()
                time.sleep(60)
        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        self._running = False
        self.monitor.stop()
        self.notifier.send_info("JatayuCore", "Scheduler stopped")
        logger.info("Scheduler stopped")
