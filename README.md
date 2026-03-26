# Rekko MCP

[![PyPI](https://img.shields.io/pypi/v/rekko-mcp)](https://pypi.org/project/rekko-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Prediction market intelligence for AI coding assistants. Deep causal research, arbitrage detection, screening, and strategy signals for **Kalshi**, **Polymarket**, and **Robinhood**.

## Install

```bash
# Zero-install via uvx
uvx rekko-mcp

# Or install from PyPI
pip install rekko-mcp
```

### Claude Code

```bash
claude mcp add rekko -- uvx rekko-mcp
```

Or add to `.mcp.json`:

```json
{
  "mcpServers": {
    "rekko": {
      "command": "uvx",
      "args": ["rekko-mcp"],
      "env": {
        "REKKO_API_KEY": "rk_free_your_key_here"
      }
    }
  }
}
```

### Cursor / Windsurf

Add to your MCP configuration with the same `uvx rekko-mcp` command and `REKKO_API_KEY` env var.

## Setup

1. Get an API key at [rekko.ai](https://rekko.ai/dashboard) (free tier available)
2. Set your key: `export REKKO_API_KEY=rk_free_...`
3. Start using — tools appear as `mcp__rekko__*` automatically

## Example prompts

- "What are the top prediction markets right now?"
- "Analyze the Fed rate decision market on Kalshi"
- "Find arbitrage opportunities above 3% spread"
- "Screen the top 50 Kalshi markets and analyze anything actionable"
- "Show my shadow portfolio performance"

## What you get

**25 MCP tools** integrated natively into your AI assistant:

| Category | Tools |
|----------|-------|
| Market intelligence | `list_markets`, `get_market`, `search_markets`, `get_market_history`, `get_resolution`, `get_execution_guidance` |
| Screening | `screen_markets`, `get_calibration` |
| Deep research | `analyze_market`, `check_analysis_status`, `get_analysis`, `list_analyses` |
| Strategy | `get_strategy`, `get_portfolio_strategy`, `get_consensus` |
| Arbitrage | `get_arbitrage`, `get_arbitrage_live` |
| Correlation | `get_correlation` |
| Trading | `place_shadow_trade`, `report_trade`, `get_portfolio`, `get_performance`, `check_resolutions` |
| Data | `run_scraper` |
| Webhooks | `create_webhook`, `list_webhooks`, `delete_webhook` |

## Pricing

| Tier | Price/call | What you get |
|------|-----------|--------------|
| Free | $0.00 | Calibration metrics, health check |
| Listing | $0.01 | Browse and search markets, price history |
| Insight | $0.10 | Start analyses, screen markets, resolution intelligence |
| Strategy | $2.00 | Strategy signals, portfolio-aware sizing, consensus |
| Deep | $5.00 | Arbitrage scanning, correlation analysis, webhooks |

Full pricing details at [docs.rekko.ai/pricing](https://docs.rekko.ai/pricing).

## Chaining with execution skills

Rekko provides the intelligence — chain with execution skills for trading:

- **PolyClaw** — execute trades on Polymarket
- **Kalshi Trader** — execute trades on Kalshi

Example flow: Rekko analysis → strategy signal → PolyClaw executes the trade.

## Links

- [docs.rekko.ai](https://docs.rekko.ai) — Full documentation
- [API Reference](https://docs.rekko.ai/api-reference/introduction) — Direct API access
- [RapidAPI](https://rapidapi.com/rekko-ai-rekko-ai-default/api/rekko-ai-prediction-market-intelligence) — Marketplace subscription
- [Discord](https://discord.gg/qTPEk9aAZg) — Community
