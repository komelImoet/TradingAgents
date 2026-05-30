import logging
import os
import re
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def parse_field(text: str, field: str) -> Optional[str]:
    m = re.search(
        rf"\*{{0,2}}{re.escape(field)}\*{{0,2}}\s*:\s*(.+?)(?:\n|$)",
        text,
        re.IGNORECASE,
    )
    return m.group(1).strip() if m else None


class TelegramNotifier:
    def __init__(self, bot_token: str | None = None, chat_id: str | None = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
        if not self.bot_token or not self.chat_id:
            logger.warning(
                "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set — notifier disabled"
            )

    @property
    def enabled(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def _send(self, text: str) -> bool:
        if not self.enabled:
            return False
        try:
            resp = requests.post(
                TELEGRAM_API.format(token=self.bot_token),
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"},
                timeout=15,
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error("Telegram send failed: %s", e)
            return False

    def send_decision(self, state: dict[str, Any]) -> bool:
        if not self.enabled:
            return False

        ticker = state.get("company_of_interest", "?")
        trade_date = state.get("trade_date", "?")
        final_text = state.get("final_trade_decision", "")
        trader_text = state.get("trader_investment_decision", "")

        rating = parse_field(final_text, "Rating") or "N/A"
        exec_summary = parse_field(final_text, "Executive Summary") or ""
        thesis = parse_field(final_text, "Investment Thesis") or ""
        action = parse_field(trader_text, "Action") or ""
        entry = parse_field(trader_text, "Entry Price") or ""
        sl = parse_field(trader_text, "Stop Loss") or ""
        sizing = parse_field(trader_text, "Position Sizing") or ""
        horizon = parse_field(final_text, "Time Horizon") or ""
        price_target = parse_field(final_text, "Price Target") or ""

        rating_icon = {"Buy": "🟢", "Overweight": "🔵", "Hold": "🟡", "Underweight": "🟠", "Sell": "🔴"}
        icon = rating_icon.get(rating, "⚪")

        lines = [
            f"<b>TradingAgents Signal</b>",
            f"━━━━━━━━━━━━━━━━━━",
            f"{icon} <b>Rating:</b> {rating}",
            f"<b>Ticker:</b> {ticker}",
            f"<b>Date:</b> {trade_date}",
        ]

        if action:
            lines.append(f"<b>Action:</b> {action}")
        if entry:
            lines.append(f"<b>Entry:</b> {entry}")
        if sl:
            lines.append(f"<b>Stop Loss:</b> {sl}")
        if price_target:
            lines.append(f"<b>Price Target:</b> {price_target}")
        if sizing:
            lines.append(f"<b>Sizing:</b> {sizing}")
        if horizon:
            lines.append(f"<b>Horizon:</b> {horizon}")

        if exec_summary:
            lines.extend(["", f"<b>Summary:</b>", exec_summary])
        if thesis:
            lines.extend(["", f"<b>Thesis:</b>", thesis[:500]])

        return self._send("\n".join(lines))

    def send_error(self, ticker: str, message: str) -> bool:
        return self._send(
            f"<b>TradingAgents Error</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<b>Ticker:</b> {ticker}\n"
            f"<b>Error:</b> {message}"
        )

    def send_info(self, title: str, body: str) -> bool:
        return self._send(
            f"<b>{title}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{body}"
        )
