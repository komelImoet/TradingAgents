# Architecture

## System Design

```
                         ┌─────────────────────────────┐
                         │      Scheduler (Python)      │
                         │  Runs daily at configurable  │
                         │  time via TradingScheduler   │
                         └─────────────┬───────────────┘
                                       │
                         ┌─────────────▼───────────────┐
                         │      TradingAgentsGraph      │
                         │                              │
                         │  ┌──────────────────────┐   │
                         │  │   Analyst Team       │   │
                         │  │  ┌──────┐ ┌──────┐   │   │
                         │  │  │Market│ │ News │   │   │
                         │  │  └──┬───┘ └──┬───┘   │   │
                         │  │  ┌──────┐ ┌──────┐   │   │
                         │  │  │Social│ │Fund. │   │   │
                         │  │  └──────┘ └──────┘   │   │
                         │  └──────────────────────┘   │
                         │            │                │
                         │  ┌──────────────────────┐   │
                         │  │   Research Team      │   │
                         │  │  ┌──────┐ ┌──────┐   │   │
                         │  │  │ Bull │ │ Bear │   │   │
                         │  │  └──┬───┘ └──┬───┘   │   │
                         │  │  └──────────────────────┘   │
                         │            │                │
                         │  ┌──────────────────────┐   │
                         │  │   Risk Management    │   │
                         │  │  ┌────────┐ ┌──────┐ │   │
                         │  │  │Conservative│Agr.│ │   │
                         │  │  └────────┘ └──────┘ │   │
                         │  │      ┌──────┐        │   │
                         │  │      │Neut.│        │   │
                         │  │      └──────┘        │   │
                         │  └──────────────────────┘   │
                         │            │                │
                         │  ┌──────────────────────┐   │
                         │  │   Trader Agent       │   │
                         │  └──────────┬───────────┘   │
                         │             │               │
                         │  ┌──────────────────────┐   │
                         │  │ Portfolio Manager    │   │
                         │  └──────────┬───────────┘   │
                         └─────────────┼───────────────┘
                                       │
                            JSON state log file
                                       │
                         ┌─────────────▼───────────────┐
                         │   mt5-execution-engine      │
                         │                              │
                         │  ┌────────┐  ┌──────────┐   │
                         │  │ Watcher │─►│  Parser  │   │
                         │  └────────┘  └────┬─────┘   │
                         │             ┌────▼─────┐   │
                         │             │   Risk   │   │
                         │             │ Manager  │   │
                         │             └────┬─────┘   │
                         │             ┌────▼─────┐   │
                         │             │  Order   │   │
                         │             │ Manager  │   │
                         │             └────┬─────┘   │
                         │             ┌────▼─────┐   │
                         │             │Connector  │   │
                         │             │ (JSON-RPC)│   │
                         │             └──────────┘   │
                         └─────────────┼───────────────┘
                                       │
                         ┌─────────────▼───────────────┐
                         │   MT5 Terminal (Windows)    │
                         │   + Telegram Bot (MQL EA)   │
                         └─────────────────────────────┘
```

## Component Details

### Python Layer (TradingAgents)

The Python framework uses **LangGraph** to orchestrate a directed acyclic graph of agent nodes. Each agent is an LLM-powered node with access to specific tools (data vendors, analysis functions).

**Agents:**
- **Market Analyst** — Technical indicators, price action
- **News Analyst** — Latest news sentiment
- **Social Media Analyst** — Social sentiment analysis
- **Fundamentals Analyst** — Financial statements, ratios
- **Bull/Bear Researchers** — Debate investment thesis
- **Risk Managers** — Conservative/Neutral/Aggressive risk analysis
- **Trader** — Concrete transaction proposal
- **Portfolio Manager** — Final decision and rating

**Output:** JSON state files written to `~/.tradingagents/logs/<TICKER>/TradingAgentsStrategy_logs/`

### Rust Layer (mt5-execution-engine)

The Rust engine is a high-performance, real-time execution bridge:

- **File Watcher** — Monitors the JSON output directory for new decisions
- **Parser** — Extracts structured data from LLM-generated markdown
- **Risk Manager** — Pre-execution validation (rating threshold, exposure, duplicates)
- **Order Manager** — Full lifecycle tracking (pending → submitted → filled/rejected)
- **Position Tracker** — Real-time position monitoring
- **MT5 Connector** — JSON-RPC bridge via Python sidecar
- **Telegram Notifier** — Event-driven alerts at every stage

## Data Flow

1. **Scheduler** triggers daily analysis at configured time
2. **TradingAgents** runs the pipeline for each ticker
3. **JSON state** is written to disk
4. **Rust engine** detects new file via `inotify`
5. **Risk validation** checks rating, exposure, duplicates
6. **Order execution** via JSON-RPC to MT5 sidecar
7. **Telegram notifications** at every stage from both layers
