import logging
import os
import re
from typing import Any

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from dotenv import load_dotenv

from tradingagents.trade_journal import TradeJournal

load_dotenv()

logger = logging.getLogger(__name__)

EXECUTABLE_RATINGS: dict[str, OrderSide] = {
    "Buy": OrderSide.BUY,
    "Overweight": OrderSide.BUY,
    "Underweight": OrderSide.SELL,
    "Sell": OrderSide.SELL,
}


def _parse_field(text: str, field: str) -> str | None:
    m = re.search(
        rf"\*{{0,2}}{re.escape(field)}\*{{0,2}}\s*:\s*(.+?)(?:\n|$)",
        text,
        re.IGNORECASE,
    )
    return m.group(1).strip() if m else None


def _parse_qty(raw: str, equity: float | None = None) -> int | None:
    """Extract integer quantity. Supports '%' of equity if provided."""
    raw = raw.strip().lower().replace(",", "")
    m_pct = re.search(r"(\d+(?:\.\d+)?)\s*%", raw)
    if m_pct and equity:
        pct = float(m_pct.group(1))
        return max(1, int(equity * pct / 100))
    m_num = re.search(r"\d+", raw)
    return int(m_num.group()) if m_num else None


def _positions_summary(positions: list) -> str:
    if not positions:
        return "📭 No open positions"
    lines = [f"<b>Open Positions: {len(positions)}</b>"]
    for p in positions:
        side = "🟢" if float(p.qty) > 0 else "🔴"
        upnl = float(p.unrealized_pl)
        upnl_str = f"+${upnl:.2f}" if upnl >= 0 else f"-${abs(upnl):.2f}"
        lines.append(
            f"{side} {p.symbol}: {abs(float(p.qty))}× @ ${float(p.avg_entry_price):.2f} "
            f"| P&L {upnl_str}"
        )
    return "\n".join(lines)


class AlpacaBroker:
    """Places trades on Alpaca based on agent decisions.

    Supports Buy/Overweight (long) and Sell/Underweight (close long).
    Implements the ``send_decision`` protocol used by notifiers.
    """

    def __init__(
        self,
        api_key: str | None = None,
        secret_key: str | None = None,
        paper: bool = True,
        notifier=None,
        circuit_breaker=None,
        trade_journal: TradeJournal | None = None,
        slippage_bps: int = 5,
    ):
        self.api_key = api_key or os.getenv("ALPACA_API_KEY", "")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY", "")
        self.paper = paper
        self.notifier = notifier
        self.circuit_breaker = circuit_breaker
        self.journal = trade_journal or TradeJournal()
        self.slippage_bps = slippage_bps

        if not self.api_key or not self.secret_key:
            logger.warning("ALPACA_API_KEY or ALPACA_SECRET_KEY not set — broker disabled")
            return

        self._client: TradingClient | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.secret_key)

    @property
    def client(self) -> TradingClient:
        if self._client is None:
            self._client = TradingClient(
                api_key=self.api_key,
                secret_key=self.secret_key,
                paper=self.paper,
            )
        return self._client

    def account_info(self) -> dict:
        info = self.client.get_account()
        return {
            "equity": float(info.equity),
            "cash": float(info.cash),
            "buying_power": float(info.buying_power),
            "status": info.status,
        }

    def get_positions(self) -> list:
        return self.client.get_all_positions()

    def positions_summary(self) -> str:
        return _positions_summary(self.get_positions())

    def has_position(self, ticker: str) -> bool:
        ticker = ticker.upper()
        try:
            self.client.get_open_position(ticker)
            return True
        except Exception:
            return False

    def close_position(self, ticker: str) -> bool:
        try:
            self.client.close_position(ticker)
            return True
        except Exception as e:
            logger.error("Close position failed for %s: %s", ticker, e)
            return False

    def send_decision(self, state: dict[str, Any]) -> bool:
        if not self.enabled:
            return False

        if self.circuit_breaker and self.circuit_breaker.is_triggered():
            logger.warning("CircuitBreaker active — skipping trade")
            if self.notifier:
                self.notifier._send(
                    f"<b>Alpaca Skip</b>\n━━━━━━━━━━━━━━━━━━\n"
                    f"<b>Reason:</b> Circuit breaker active — max SL hit today"
                )
            return False

        ticker = state.get("company_of_interest", "")
        final_text = state.get("final_trade_decision", "")
        trader_text = state.get("trader_investment_decision", "")

        rating = (_parse_field(final_text, "Rating") or "Hold").strip()
        side = EXECUTABLE_RATINGS.get(rating)
        if side is None:
            logger.info("Alpaca: %s rating %s → skip", ticker, rating)
            return False

        info = self.account_info()
        equity = info["equity"]

        if side == OrderSide.BUY:
            if self.has_position(ticker):
                logger.info("Alpaca: %s → already have position, skip Buy", ticker)
                if self.notifier:
                    self.notifier._send(
                        f"<b>Alpaca Skip</b>\n━━━━━━━━━━━━━━━━━━\n"
                        f"<b>Ticker:</b> {ticker}\n"
                        f"<b>Reason:</b> Already have position"
                    )
                return False

            sizing_raw = _parse_field(trader_text, "Position Sizing") or ""
            qty = _parse_qty(sizing_raw, equity)

            if qty is None:
                # fallback: 1% of equity
                qty = max(1, int(equity * 0.01))
                logger.warning("Alpaca: fallback sizing 1%% for %s = %d", ticker, qty)

            return self._place_order(ticker, qty, side)

        if side == OrderSide.SELL:
            if not self.has_position(ticker):
                logger.info("Alpaca: %s → no position to sell", ticker)
                return False
            return self._close_and_notify(ticker)

        return False

    def _get_current_price(self, ticker: str) -> float | None:
        try:
            trade = self.client.get_latest_trade(ticker)
            return float(trade.price)
        except Exception as e:
            logger.warning("Cannot fetch price for %s: %s", ticker, e)
            return None

    def _place_order(self, ticker: str, qty: int, side: OrderSide) -> bool:
        try:
            price = self._get_current_price(ticker)
            if price is None:
                logger.error("Alpaca: no price for %s — cannot place limit order", ticker)
                return False

            if side == OrderSide.BUY:
                limit_price = round(price * (1 + self.slippage_bps / 10000), 2)
            else:
                limit_price = round(price * (1 - self.slippage_bps / 10000), 2)

            order_req = LimitOrderRequest(
                symbol=ticker,
                qty=qty,
                side=side,
                limit_price=limit_price,
                time_in_force=TimeInForce.DAY,
            )
            order = self.client.submit_order(order_req)
            fill_price = float(order.filled_avg_price or limit_price)
            self.journal.record_entry(ticker, side.name.lower(), qty, fill_price, order.id)

            side_icon = "🟢" if side == OrderSide.BUY else "🔴"
            msg = (
                f"<b>Alpaca Order Placed</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{side_icon} <b>Side:</b> {side.name}\n"
                f"<b>Ticker:</b> {ticker}\n"
                f"<b>Qty:</b> {qty}\n"
                f"<b>Limit:</b> ${limit_price:.2f}\n"
                f"<b>Fill:</b> ${fill_price:.2f}\n"
                f"<b>Order:</b> #{order.id}"
            )
            if self.notifier:
                self.notifier._send(msg)
            logger.info("Alpaca: %s %d × %s → order #%s @ %.2f", side.name, qty, ticker, order.id, fill_price)
            return True
        except Exception as e:
            logger.error("Alpaca order failed for %s: %s", ticker, e)
            if self.notifier:
                self.notifier.send_error(ticker, f"Order failed: {e}")
            return False

    def _close_and_notify(self, ticker: str) -> bool:
        try:
            orders = self.client.close_position(ticker)
            fill_price = None
            if orders:
                order = orders[0] if isinstance(orders, list) else orders
                fill_price = float(getattr(order, "filled_avg_price", 0) or 0)
            if fill_price and fill_price > 0:
                self.journal.record_exit(ticker, fill_price, reason="signal")
            else:
                price = self._get_current_price(ticker) or 0
                self.journal.record_exit(ticker, price, reason="signal")
            msg = (
                f"<b>Alpaca Position Closed</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🔴 <b>Ticker:</b> {ticker}\n"
                f"<b>Fill:</b> ${fill_price:.2f}\n"
                f"<b>Reason:</b> Sell/Underweight signal"
            )
            if self.notifier:
                self.notifier._send(msg)
            logger.info("Alpaca: closed %s @ %.2f", ticker, fill_price or 0)
            return True
        except Exception as e:
            logger.error("Alpaca close failed for %s: %s", ticker, e)
            if self.notifier:
                self.notifier.send_error(ticker, f"Close failed: {e}")
            return False
