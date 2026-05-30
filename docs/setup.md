# Installation

## Prerequisites

- Python 3.10+
- Rust toolchain (for mt5-execution-engine)
- MetaTrader 5 (Windows, for live execution)
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

## Python Setup

```bash
# Clone the repository
git clone https://github.com/komelImoet/TradingAgents.git
cd TradingAgents

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install the package
pip install -e .
```

### LLM Provider

Set up at least one LLM provider in `.env`:

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Or DeepSeek
DEEPSEEK_API_KEY=sk-...

# Or Anthropic
ANTHROPIC_API_KEY=sk-...

# Or Google Gemini
GOOGLE_API_KEY=...
```

## Rust Engine Setup

```bash
cd mt5-execution-engine

# Build
cargo build --release

# Run (dry-run mode)
./target/release/mt5-execution-engine --dry-run

# Run with custom config
./target/release/mt5-execution-engine --config /path/to/config.toml
```

## Telegram Bot Setup

1. Create a bot with [@BotFather](https://t.me/botfather)
2. Get your bot token
3. Get your chat ID (message @userinfobot)
4. Add to `.env`:

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklmNOPqrstUVwxyz
TELEGRAM_CHAT_ID=123456789
```

## Docker Setup

```bash
# Full stack
docker compose up -d tradingagents mt5-engine

# With Ollama (local LLM)
docker compose --profile ollama up -d
```

## Verify Installation

```bash
# Run a single analysis
python main.py run NVDA --date 2024-05-10

# Expected output:
# Buy (or one of Buy/Overweight/Hold/Underweight/Sell)
```
