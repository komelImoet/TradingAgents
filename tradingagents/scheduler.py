import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.notifiers.telegram_notifier import TelegramNotifier
from tradingagents.default_config import DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class TradingScheduler:
    def __init__(
        self,
        tickers: list[str],
        config: Optional[dict] = None,
        run_hour: int = 8,
        run_minute: int = 0,
        run_timezone: str = "UTC",
    ):
        self.tickers = tickers
        self.config = config or DEFAULT_CONFIG.copy()
        self.run_hour = run_hour
        self.run_minute = run_minute
        self.run_timezone = run_timezone

        self.notifier = TelegramNotifier()
        self.last_run_date = None
        self._running = False

    def _should_run(self) -> bool:
        now = datetime.now(timezone.utc)
        today = now.date()

        if self.last_run_date == today:
            return False

        target_seconds = self.run_hour * 3600 + self.run_minute * 60
        current_seconds = now.hour * 3600 + now.minute * 60 + now.second

        return current_seconds >= target_seconds

    def _run_pipeline(self) -> None:
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.notifier.send_info("Scheduler", f"Starting daily run for {len(self.tickers)} tickers")

        for ticker in self.tickers:
            try:
                logger.info("Running TradingAgents for %s on %s", ticker, today_str)

                ta = TradingAgentsGraph(
                    debug=False,
                    config=self.config,
                    notifiers=[self.notifier] if self.notifier.enabled else [],
                )
                final_state, signal = ta.propagate(ticker, today_str)

                logger.info(
                    "Completed %s on %s — signal: %s",
                    ticker, today_str, signal
                )

            except Exception as e:
                logger.error("Failed to process %s: %s", ticker, e)
                self.notifier.send_error(ticker, str(e))

        self.notifier.send_info("Scheduler", f"Daily run completed: {len(self.tickers)} tickers processed")
        self.last_run_date = datetime.now(timezone.utc).date()

    def start(self) -> None:
        self._running = True
        self.notifier.send_health("Scheduler started")

        logger.info(
            "Scheduler started: daily at %02d:%02d UTC for %s",
            self.run_hour, self.run_minute, ", ".join(self.tickers)
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
        self.notifier.send_health("Scheduler stopped")
        logger.info("Scheduler stopped")
