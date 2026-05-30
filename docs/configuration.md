# Configuration

## Environment Variables

Create a `.env` file in the project root:

```bash
# === LLM Providers (set at least one) ===
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...
GOOGLE_API_KEY=...

# === Telegram Notifications ===
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklmNOPqrstUVwxyz
TELEGRAM_CHAT_ID=123456789
```

## TradingAgents Configuration

The default configuration is defined in `tradingagents/default_config.py`:

```python
DEFAULT_CONFIG = {
    # LLM settings
    "llm_provider": "openai",
    "deep_think_llm": "gpt-5.4",
    "quick_think_llm": "gpt-5.4-mini",

    # Output language
    "output_language": "English",

    # Debate rounds
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,

    # Data vendors
    "data_vendors": {
        "core_stock_apis": "yfinance",
        "technical_indicators": "yfinance",
        "fundamental_data": "yfinance",
        "news_data": "yfinance",
    },
}
```

Override in `main.py`:

```python
config = DEFAULT_CONFIG.copy()
config["deep_think_llm"] = "gpt-4o"
config["max_debate_rounds"] = 3
```

## MT5 Execution Engine Configuration

Located in `mt5-execution-engine/config/default.toml`:

```toml
[watcher]
# Directory where TradingAgents writes JSON state logs
log_dir = "~/.tradingagents/logs"
debounce_ms = 1000

[mt5]
# MT5 account credentials
mt5_login = 0
mt5_password = ""
mt5_server = ""

[risk]
# Max % of equity per position
max_position_pct = 10.0
# Max total exposure
max_total_exposure_pct = 50.0
# Minimum rating for execution (Buy, Overweight, Hold, Underweight, Sell)
min_rating = "Hold"
# Require stop-loss
require_stop_loss = true
# Default stop-loss % from entry
default_stop_loss_pct = 5.0

[execution]
max_slippage_pct = 0.5
retry_attempts = 3
retry_delay_ms = 1000
position_poll_interval_ms = 5000
```

## CLI Options

### Single Run

```bash
python main.py run [TICKER] [OPTIONS]

Arguments:
  ticker                   Ticker symbol (default: NVDA)

Options:
  --date, -d YYYY-MM-DD   Trade date
  --quiet, -q             Suppress debug output
```

### Scheduler

```bash
python main.py schedule [OPTIONS]

Options:
  --tickers, -t STRING    Comma-separated tickers (default: NVDA,AAPL,SPY)
  --hour INT              Run hour UTC (default: 8)
  --minute INT            Run minute UTC (default: 0)
```
