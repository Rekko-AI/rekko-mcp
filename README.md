# rekko-mcp

[![rekko-mcp MCP server](https://glama.ai/mcp/servers/Rekko-AI/rekko-mcp/badges/card.svg)](https://glama.ai/mcp/servers/Rekko-AI/rekko-mcp)

Prediction market intelligence for AI coding assistants. 24 MCP tools for market data, deep analysis, trading signals, arbitrage detection, and screening across **Kalshi**, **Polymarket**, and **Robinhood**.

## Install

```bash
uvx rekko-mcp
# or
pip install rekko-mcp
```

Requires Python 3.11+ and a [Rekko API key](https://rekko.ai/dashboard) (free tier available).

## Configure

**Claude Code:**

```bash
claude plugin install rekko
```

Or add to `.mcp.json`:

```json
{
  "mcpServers": {
    "rekko": {
      "command": "uvx",
      "args": ["rekko-mcp"],
      "env": { "REKKO_API_KEY": "rk_free_your_key_here" }
    }
  }
}
```

**Cursor** — same `.mcp.json` format in `.cursor/mcp.json`.

## What You Get

- **Market data** — browse, search, and get price history across Kalshi, Polymarket, and Robinhood
- **Deep analysis** — multi-stage AI research pipeline with probability estimates and causal decomposition (30-90s)
- **Trading signals** — edge assessment, confidence scoring, Kelly criterion position sizing
- **Arbitrage** — cross-platform spread detection between Kalshi and Polymarket
- **Screening** — batch score markets by volume, movement, and opportunity
- **Performance** — trading track record and calibration metrics
- **Webhooks** — real-time alerts for price shifts and whale trades
- **Quickstart** — working code snippets for Python, curl, and MCP config to get started in under 5 minutes

## Quick Examples

```
"What are the top prediction markets right now?"
"Analyze the Fed rate decision market on Kalshi"
"Find arbitrage opportunities above 3% spread"
"Screen the top 50 Kalshi markets and analyze anything actionable"
"Show me a quickstart for Python"
```

## Tutorials

- [Prediction Market API Comparison](https://rekko.ai/docs/guides/prediction-market-api-comparison) — Kalshi vs Polymarket vs Robinhood APIs compared
- [Build a Trading Bot with Python](https://rekko.ai/docs/guides/build-trading-bot-python) — End-to-end bot with screening, analysis, and signals
- [Kalshi API Guide](https://rekko.ai/docs/guides/kalshi-api-guide) — RSA-PSS auth, endpoints, and adding AI analysis
- [Polymarket API Guide](https://rekko.ai/docs/guides/polymarket-api-guide) — CLOB, py-clob-client, and AI-powered analysis
- [MCP Trading Workflow](https://rekko.ai/docs/guides/mcp-trading-workflow) — Natural language market research from your IDE
- [Cross-Platform Arbitrage](https://rekko.ai/docs/guides/prediction-market-arbitrage) — Find price gaps between platforms
- [Kelly Criterion Sizing](https://rekko.ai/docs/guides/kelly-criterion-position-sizing) — Optimal position sizing

## Pricing

| Tier | Per call | Includes |
|------|----------|----------|
| Free | $0.00 | Calibration, health check |
| Listing | $0.01 | Market data, price history |
| Insight | $0.10 | Analysis, screening, resolution |
| Strategy | $2.00 | Signals, portfolio sizing, consensus |
| Deep | $5.00 | Arbitrage, correlation, webhooks |

Free plan: 100 listing + 10 insight calls/month. [Upgrade to Pro](https://rekko.ai/dashboard) for higher limits.

## Links

- [rekko.ai](https://rekko.ai) — Home
- [Documentation](https://rekko.ai/docs) — Full API reference and tutorials
- [OpenAPI Spec](https://api.rekko.ai/openapi.json) — Machine-readable API schema
- [RapidAPI](https://rapidapi.com/rekko-ai-rekko-ai-default/api/rekko-ai-prediction-market-intelligence) — Marketplace listing
