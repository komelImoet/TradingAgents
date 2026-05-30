import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

STATE_DIR = Path(os.getenv("TRADINGAGENTS_RESULTS_DIR", os.path.expanduser("~/.tradingagents")))
STATE_PATH = STATE_DIR / "trade_journal.json"


class TradeJournal:
    """Persistent trade log: entry/exit, P&L, win rate, performance metrics."""

    def __init__(self):
        self._data = self._load()
        self._next_id = self._data.get("next_id", 1)

    # -- trades ----------------------------------------------------

    def record_entry(
        self, ticker: str, side: str, qty: int, price: float, order_id: str
    ) -> int:
        trade_id = self._next_id
        self._next_id += 1
        entry = {
            "id": trade_id,
            "ticker": ticker.upper(),
            "side": side,
            "qty": qty,
            "entry_price": price,
            "entry_time": datetime.now(timezone.utc).isoformat(),
            "order_id": order_id,
            "status": "open",
            "exit_price": None,
            "exit_time": None,
            "pnl": None,
            "pnl_pct": None,
            "reason": None,
        }
        self._data["trades"].append(entry)
        self._data["next_id"] = self._next_id
        self._save()
        logger.info("TradeJournal: entry #%d %s %d×%s @ %.2f", trade_id, side, qty, ticker, price)
        return trade_id

    def record_exit(
        self, ticker: str, price: float, reason: str = "signal"
    ) -> dict | None:
        ticker = ticker.upper()
        for t in reversed(self._data["trades"]):
            if t["ticker"] == ticker and t["status"] == "open":
                t["status"] = "closed"
                t["exit_price"] = price
                t["exit_time"] = datetime.now(timezone.utc).isoformat()
                t["reason"] = reason

                entry = t["entry_price"]
                qty = t["qty"]
                if t["side"] == "buy":
                    t["pnl"] = round((price - entry) * qty, 2)
                    t["pnl_pct"] = round((price - entry) / entry * 100, 2)
                else:
                    t["pnl"] = round((entry - price) * qty, 2)
                    t["pnl_pct"] = round((entry - price) / entry * 100, 2)

                self._recompute_stats()
                self._save()
                logger.info(
                    "TradeJournal: exit #%d %s P&L %.2f (%.2f%%)",
                    t["id"], ticker, t["pnl"], t["pnl_pct"],
                )
                return t
        return None

    # -- stats -----------------------------------------------------

    @property
    def stats(self) -> dict:
        return dict(self._data["stats"])

    @property
    def open_count(self) -> int:
        return sum(1 for t in self._data["trades"] if t["status"] == "open")

    @property
    def recent_trades(self, n: int = 10) -> list:
        closed = [t for t in self._data["trades"] if t["status"] == "closed"]
        return closed[-n:]

    def summary_text(self) -> str:
        s = self.stats
        lines = [
            f"<b>Trade Journal — Performance</b>",
            f"━━━━━━━━━━━━━━━━━━",
            f"📊 <b>Total Trades:</b> {s['total_trades']}",
            f"{'🟢' if s['win_rate'] >= 50 else '🔴'} <b>Win Rate:</b> {s['win_rate']:.1f}%  ({s['wins']}W / {s['losses']}L)",
            f"💰 <b>Total P&L:</b> ${s['total_pnl']:.2f}",
            f"📈 <b>Avg Win:</b> ${s['avg_win']:.2f}  | <b>Avg Loss:</b> ${s['avg_loss']:.2f}",
            f"🏆 <b>Best:</b> ${s['best_trade']:.2f}  | <b>Worst:</b> ${s['worst_trade']:.2f}",
            f"⬇️ <b>Max Drawdown:</b> {s['max_drawdown_pct']:.1f}%",
            f"📂 <b>Open Positions:</b> {self.open_count}",
        ]
        recent = self.recent_trades(3)
        if recent:
            lines.append("")
            lines.append(f"<b>Last {len(recent)} Trades:</b>")
            for t in recent:
                icon = "🟢" if (t["pnl"] or 0) >= 0 else "🔴"
                lines.append(
                    f"  {icon} #{t['id']} {t['ticker']} {t['side'].upper()} "
                    f"| {t['pnl']:+.2f} ({t['pnl_pct']:+.1f}%)"
                )
        return "\n".join(lines)

    # -- internal --------------------------------------------------

    def _recompute_stats(self):
        closed = [t for t in self._data["trades"] if t["status"] == "closed"]
        pnls = [t["pnl"] for t in closed if t["pnl"] is not None]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        total_pnl = sum(pnls) if pnls else 0.0
        total_trades = len(closed)
        win_rate = (len(wins) / total_trades * 100) if total_trades else 0.0

        # max drawdown: largest peak-to-trough in cumulative P&L
        cum = 0.0
        peak = 0.0
        max_dd = 0.0
        for p in pnls:
            cum += p
            if cum > peak:
                peak = cum
            dd = peak - cum
            if dd > max_dd:
                max_dd = dd

        max_dd_pct = (max_dd / peak * 100) if peak > 0 else 0.0

        self._data["stats"] = {
            "total_trades": total_trades,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(win_rate, 1),
            "total_pnl": round(total_pnl, 2),
            "avg_win": round(sum(wins) / len(wins), 2) if wins else 0.0,
            "avg_loss": round(sum(losses) / len(losses), 2) if losses else 0.0,
            "best_trade": round(max(pnls), 2) if pnls else 0.0,
            "worst_trade": round(min(pnls), 2) if pnls else 0.0,
            "max_drawdown_pct": round(max_dd_pct, 1),
        }

    def _load(self) -> dict:
        try:
            if STATE_PATH.exists():
                data = json.loads(STATE_PATH.read_text())
                logger.info("TradeJournal loaded: %d trades", len(data.get("trades", [])))
                return data
        except Exception as e:
            logger.warning("TradeJournal: load failed: %s", e)
        return {"next_id": 1, "trades": [], "stats": self._empty_stats()}

    def _save(self):
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            STATE_PATH.write_text(json.dumps(self._data, indent=2, default=str))
        except Exception as e:
            logger.warning("TradeJournal: save failed: %s", e)

    @staticmethod
    def _empty_stats() -> dict:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
            "max_drawdown_pct": 0.0,
        }
