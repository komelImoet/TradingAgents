# Contributing

## Development Setup

```bash
git clone https://github.com/komelImoet/TradingAgents.git
cd TradingAgents
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Code Style

- Python: Follow PEP 8
- Rust: Follow `rustfmt` defaults
- Keep code concise — no unnecessary comments
- Use type hints in Python

## Testing

```bash
# Python tests
pytest

# Rust tests
cd mt5-execution-engine && cargo test
```

## Pull Request Process

1. Fork the repo
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a PR with a clear description

## Project Structure

```
TradingAgents/
├── main.py                         # CLI entry point
├── tradingagents/
│   ├── agents/                     # Agent definitions
│   │   ├── analysts/               # Market, news, social, fundamentals
│   │   ├── researchers/            # Bull/bear debate
│   │   ├── risk_mgmt/              # Conservative/neutral/aggressive
│   │   ├── trader/                 # Transaction proposal
│   │   └── managers/               # Research & portfolio managers
│   ├── graph/                      # LangGraph pipeline
│   │   ├── trading_graph.py        # Main orchestrator
│   │   ├── signal_processing.py    # Rating extraction
│   │   └── ...
│   ├── notifiers/                  # External notifications
│   │   └── telegram_notifier.py    # Telegram integration
│   ├── scheduler.py                # Automated daily runs
│   ├── dataflows/                  # Data providers
│   ├── llm_clients/                # LLM provider clients
│   └── default_config.py           # Configuration defaults
├── mt5-execution-engine/           # Rust execution bridge
│   ├── src/
│   │   ├── main.rs                 # Engine entry point
│   │   ├── telegram.rs             # Telegram integration
│   │   ├── watcher.rs              # File system watcher
│   │   ├── parser.rs               # Decision parser
│   │   ├── risk.rs                 # Risk manager
│   │   ├── order.rs                # Order lifecycle
│   │   ├── position.rs             # Position tracker
│   │   └── connector.rs            # MT5 JSON-RPC bridge
│   └── sidecar/
│       └── mt5_sidecar.py          # Python MT5 bridge
├── docker-compose.yml              # Docker orchestration
└── docs/                           # Documentation (mkdocs)
```
