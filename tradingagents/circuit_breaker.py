import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_SL_HITS = 2
STATE_DIR = Path(os.getenv("TRADINGAGENTS_RESULTS_DIR", os.path.expanduser("~/.tradingagents")))
STATE_PATH = STATE_DIR / "circuit_breaker.json"


class CircuitBreaker:
    """Stop trading after N stop-loss hits. Auto-resets daily."""

    def __init__(self, max_hits: int = MAX_SL_HITS):
        self.max_hits = max_hits
        self._state = self._load()

    # -- public API ------------------------------------------------

    def register_sl(self) -> bool:
        """Record an SL hit. Returns True if circuit *just* tripped."""
        self._state["sl_count"] += 1
        today = str(datetime.now(timezone.utc).date())
        self._state["date"] = today
        tripped = self._state["sl_count"] >= self.max_hits
        if tripped:
            self._state["triggered"] = True
        self._save()
        return tripped

    def is_triggered(self) -> bool:
        self._maybe_reset()
        return self._state.get("triggered", False)

    def sl_count(self) -> int:
        self._maybe_reset()
        return self._state.get("sl_count", 0)

    def remaining(self) -> int:
        return max(0, self.max_hits - self.sl_count())

    def reset(self):
        """Manually reset (e.g. via Telegram command or daily)."""
        self._state = {"sl_count": 0, "triggered": False, "date": None}
        self._save()
        logger.info("CircuitBreaker manually reset")

    # -- internal --------------------------------------------------

    def _maybe_reset(self):
        today = str(datetime.now(timezone.utc).date())
        if self._state.get("date") != today:
            self.reset()

    def _load(self) -> dict:
        try:
            if STATE_PATH.exists():
                data = json.loads(STATE_PATH.read_text())
                logger.info("CircuitBreaker loaded: %s", data)
                return data
        except Exception as e:
            logger.warning("CircuitBreaker: failed to load: %s", e)
        return {"sl_count": 0, "triggered": False, "date": None}

    def _save(self):
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            STATE_PATH.write_text(json.dumps(self._state, indent=2))
        except Exception as e:
            logger.warning("CircuitBreaker: failed to save: %s", e)
