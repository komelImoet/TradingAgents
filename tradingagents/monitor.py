import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any

from tradingagents.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class PositionMonitor:
    """Background monitor for stop-loss, position summaries, heartbeat, daily P&L.

    Runs in a daemon thread so it doesn't block scheduler shutdown.
    """

    def __init__(
        self,
        broker,
        notifier,
        circuit_breaker: CircuitBreaker | None = None,
        sl_check_interval: int = 60,
        summary_interval: int = 3600,
        heartbeat_interval: int = 7200,
    ):
        self.broker = broker
        self.notifier = notifier
        self.circuit_breaker = circuit_breaker
        self.sl_check_interval = sl_check_interval
        self.summary_interval = summary_interval
        self.heartbeat_interval = heartbeat_interval
        self._stop = threading.Event()
        self._last_summary = 0.0
        self._last_heartbeat = 0.0
        self._daily_report_date = None
        self._thread: threading.Thread | None = None

    @property
    def enabled(self) -> bool:
        return self.broker.enabled and self.notifier.enabled

    def start(self):
        if not self.enabled:
            logger.info("PositionMonitor: broker or notifier disabled, not starting")
            return
        self._thread = threading.Thread(target=self._loop, daemon=True, name="pos-monitor")
        self._thread.start()
        logger.info("PositionMonitor started")

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("PositionMonitor stopped")

    def _loop(self):
        while not self._stop.is_set():
            now = time.time()
            try:
                self._check_stop_loss()
                self._check_summary(now)
                self._check_heartbeat(now)
                self._check_daily_report()
            except Exception as e:
                logger.error("PositionMonitor error: %s", e)
            self._stop.wait(self.sl_check_interval)

    def _check_stop_loss(self):
        try:
            positions = self.broker.get_positions()
        except Exception as e:
            logger.warning("PositionMonitor: cannot fetch positions: %s", e)
            return

        for p in positions:
            ticker = p.symbol
            qty = float(p.qty)
            avg_entry = float(p.avg_entry_price)
            current = float(p.current_price)
            side = "long" if qty > 0 else "short"

            if side != "long":
                continue

            # 5% stop loss from entry
            sl_price = avg_entry * 0.95
            if current <= sl_price:
                logger.warning(
                    "SL triggered for %s: entry=%.2f current=%.2f sl=%.2f",
                    ticker, avg_entry, current, sl_price,
                )
                try:
                    self.broker.client.close_position(ticker)
                    if self.notifier:
                        self.notifier._send(
                            f"<b>Stop Loss Triggered</b>\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"🔴 <b>Ticker:</b> {ticker}\n"
                            f"<b>Entry:</b> ${avg_entry:.2f}\n"
                            f"<b>Current:</b> ${current:.2f}\n"
                            f"<b>Loss:</b> {((current - avg_entry) / avg_entry * 100):.1f}%"
                        )

                    if self.circuit_breaker:
                        tripped = self.circuit_breaker.register_sl()
                        remaining = self.circuit_breaker.remaining()
                        if self.notifier:
                            cnt = self.circuit_breaker.sl_count()
                            self.notifier._send(
                                f"<b>Circuit Breaker</b>\n"
                                f"━━━━━━━━━━━━━━━━━━\n"
                                f"🔴 SL #{cnt} recorded today\n"
                                f"⏳ Remaining SL allowance: {remaining}\n"
                                f"{'⛔ TRADING HALTED — max SL reached' if tripped else '✅ Trading continues'}"
                            )
                except Exception as e:
                    logger.error("SL close failed for %s: %s", ticker, e)
        return

    def _check_summary(self, now: float):
        if now - self._last_summary < self.summary_interval:
            return
        self._last_summary = now

        try:
            summary = self.broker.positions_summary()
            if self.notifier:
                self.notifier._send(f"<b>Position Summary</b>\n━━━━━━━━━━━━━━━━━━\n{summary}")
        except Exception as e:
            logger.warning("PositionMonitor: summary failed: %s", e)

    def _check_heartbeat(self, now: float):
        if now - self._last_heartbeat < self.heartbeat_interval:
            return
        self._last_heartbeat = now

        try:
            info = self.broker.account_info()
            if self.notifier:
                self.notifier._send(
                    f"<b>JatayuCore Heartbeat</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"💚 <b>Status:</b> Running\n"
                    f"💰 <b>Equity:</b> ${info['equity']:.2f}\n"
                    f"💵 <b>Cash:</b> ${info['cash']:.2f}"
                )
        except Exception as e:
            logger.warning("PositionMonitor: heartbeat failed: %s", e)

    def _check_daily_report(self):
        today = datetime.now(timezone.utc).date()
        if self._daily_report_date == today:
            return
        self._daily_report_date = today

        try:
            info = self.broker.account_info()
            if self.notifier:
                self.notifier._send(
                    f"<b>Daily P&L Report</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📅 <b>Date:</b> {today}\n"
                    f"💰 <b>Equity:</b> ${info['equity']:.2f}\n"
                    f"💵 <b>Cash:</b> ${info['cash']:.2f}\n"
                    f"⚡ <b>Buying Power:</b> ${info['buying_power']:.2f}"
                )
        except Exception as e:
            logger.warning("PositionMonitor: daily report failed: %s", e)
