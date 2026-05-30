# MT5 Execution Engine

The `mt5-execution-engine` is a high-performance Rust bridge that monitors TradingAgents' JSON output and executes trades in MetaTrader 5.

## Architecture

```
┌─────────────────────────────────────────┐
│           mt5-execution-engine          │
│                                         │
│  ┌──────────┐   ┌──────────┐           │
│  │ Watcher   │──►│  Parser  │           │
│  │ (inotify) │   └────┬─────┘           │
│  └──────────┘        │                 │
│               ┌──────▼──────┐          │
│               │ Risk Manager│          │
│               │  - Rating   │          │
│               │  - Exposure │          │
│               │  - Duplicate│          │
│               │  - Stop Loss│          │
│               └──────┬──────┘          │
│               ┌──────▼──────┐          │
│               │Order Manager│          │
│               │  - Lifecycle│          │
│               │  - Retries  │          │
│               └──────┬──────┘          │
│               ┌──────▼──────┐          │
│               │   Connector │          │
│               │ (JSON-RPC)  │          │
│               └──────┬──────┘          │
│               ┌──────▼──────┐          │
│               │  Telegram   │          │
│               │  Notifier   │          │
│               └─────────────┘          │
└─────────────────┬───────────────────────┘
                  │
         JSON-RPC (stdin/stdout)
                  │
┌─────────────────▼───────────────────────┐
│         Python Sidecar                   │
│     (mt5_sidecar.py)                     │
│                                          │
│  ┌────────────┐  ┌───────────────┐      │
│  │ MetaTrader5│  │  JSON-RPC     │      │
│  │  Library   │  │  Handler      │      │
│  └────────────┘  └───────────────┘      │
└─────────────────┬───────────────────────┘
                  │
         MT5 Terminal (Windows)
```

## How It Works

1. **File Watcher** — Uses `inotify` (Linux) or `kqueue` (macOS) to monitor the TradingAgents log directory for new `full_states_log_*.json` files
2. **Parser** — Extracts structured fields (rating, action, prices, sizing) from the LLM-generated markdown using regex
3. **Risk Manager** — Validates each decision:
   - Rating threshold check (e.g., skip Hold/Underweight)
   - Duplicate position prevention
   - Stop-loss enforcement
   - Exposure limits
4. **Order Manager** — Tracks full lifecycle (Pending → Submitted → Filled/Rejected)
5. **Connector** — Communicates with MT5 via JSON-RPC through a Python sidecar process
6. **Position Tracker** — Periodically syncs open positions and account state

## CLI Options

```bash
# Run with default config
mt5-execution-engine

# Run with custom config
mt5-execution-engine --config /path/to/config.toml

# Dry-run mode (validate but don't execute)
mt5-execution-engine --dry-run
```

## Risk Rules

| Rule | Config | Default |
|------|--------|---------|
| Minimum Rating | `risk.min_rating` | Hold |
| Max Position % | `risk.max_position_pct` | 10% |
| Max Total Exposure | `risk.max_total_exposure_pct` | 50% |
| Require Stop Loss | `risk.require_stop_loss` | true |
| Default Stop Loss % | `risk.default_stop_loss_pct` | 5% |
| Max Slippage | `execution.max_slippage_pct` | 0.5% |
| Retry Attempts | `execution.retry_attempts` | 3 |

## Telegram Notifications

The engine sends notifications for:

- Decision received (with rating and action details)
- Risk check result (approved/rejected with reason)
- Order executed (filled with ticket and price)
- Order failed (with error message)
- Periodic position summary (every hour)
- Health check status (on failure/reconnect)
- Engine errors

## Sidecar

The Python sidecar (`sidecar/mt5_sidecar.py`) handles the actual MT5 interaction:

- `connect` — Initialize MT5 terminal connection
- `send_order` — Place market/limit orders
- `get_positions` — Fetch open positions
- `get_account_info` — Fetch equity and balance
- `close_position` — Close positions by ticket
- `ping` — Health check
- `shutdown` — Clean shutdown
