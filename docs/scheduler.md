# Scheduler

The `TradingScheduler` runs automated daily trading sessions.

## How It Works

The scheduler runs as a daemon, checking every 60 seconds whether it's time to execute. When the configured time is reached, it runs the full TradingAgents pipeline for each ticker in the watchlist.

## Usage

```bash
# Run scheduler with default settings (08:00 UTC, tickers: NVDA,AAPL,SPY)
python main.py schedule

# Custom tickers and time
python main.py schedule --tickers AAPL,MSFT,GOOGL --hour 9 --minute 30

# With Docker
docker compose up -d tradingagents
```

## Configuration

```bash
python main.py schedule \
  --tickers NVDA,AAPL,MSFT,GOOGL,AMZN \  # Comma-separated tickers
  --hour 8 \                               # Run hour (UTC)
  --minute 0                               # Run minute (UTC)
```

## What Happens Each Run

1. Scheduler detects it's time to run (once per day)
2. Sends Telegram: `"Starting daily run for 3 tickers"`
3. For each ticker:
   - Runs TradingAgents pipeline
   - Sends Telegram notification with analysis result
   - On error: sends error notification
4. Sends Telegram: `"Daily run completed: 3 tickers processed"`
5. Waits until next day

## Telegram Notifications

The scheduler sends these notifications:

- **Startup**: `"Scheduler started"`
- **Daily Run**: `"Starting daily run for N tickers"`
- **Each Result**: Full analysis signal card
- **On Error**: Error details with ticker
- **Completion**: `"Daily run completed: N tickers processed"`
- **Shutdown**: `"Scheduler stopped"`
