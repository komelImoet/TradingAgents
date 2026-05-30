# Docker Deployment

Deploy the entire TradingAgents stack with Docker Compose.

## Services

| Service | Description | Based On |
|---------|-------------|----------|
| `tradingagents` | Python scheduler (daily runs) | `Dockerfile` (Python) |
| `mt5-engine` | Rust execution engine | `mt5-execution-engine/Dockerfile` |
| `ollama` | Local LLM (optional) | `ollama/ollama` |

## Quick Start

```bash
# Clone and enter
git clone https://github.com/komelImoet/TradingAgents.git
cd TradingAgents

# Configure
cp .env.example .env
# Edit .env with your API keys and Telegram settings

# Start the stack
docker compose up -d

# View logs
docker compose logs -f tradingagents
docker compose logs -f mt5-engine
```

## Configuration

Set environment variables in `.env`:

```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# LLM Provider
OPENAI_API_KEY=sk-...

# Scheduler tickers (used by docker-compose)
TICKERS=AAPL,MSFT,GOOGL
```

## Docker Compose Reference

```yaml
services:
  tradingagents:
    build: .
    env_file: .env
    volumes:
      - tradingagents_data:/home/appuser/.tradingagents
    command: python main.py schedule --tickers "${TICKERS:-NVDA,AAPL,SPY}"
    restart: unless-stopped

  mt5-engine:
    build:
      context: ./mt5-execution-engine
      dockerfile: Dockerfile
    env_file: .env
    volumes:
      - tradingagents_data:/home/appuser/.tradingagents
    restart: unless-stopped
    network_mode: "host"
```

## Volumes

| Volume | Path | Purpose |
|--------|------|---------|
| `tradingagents_data` | `/home/appuser/.tradingagents` | Shared state between Python & Rust |

## Local LLM (Ollama)

```bash
# Start with Ollama
docker compose --profile ollama up -d

# Pull a model
docker compose exec ollama ollama pull llama3

# The tradingagents-ollama service will use it automatically
```

## Production Considerations

1. **Secrets**: Use Docker secrets or a secrets manager instead of `.env` for production
2. **Logging**: Configure log aggregation (e.g., Loki, DataDog)
3. **Monitoring**: Add healthcheck endpoints
4. **Backup**: Regularly backup `tradingagents_data` volume
5. **Network**: The Rust engine needs `host` networking or access to the host's MT5 terminal
