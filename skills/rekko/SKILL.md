---
name: rekko
description: Prediction market intelligence from Rekko AI. Auto-loads when prediction markets, Kalshi, Polymarket, Robinhood, arbitrage, trading signals, market analysis, or probability estimates are discussed. Provides tool guidance, response interpretation, workflow patterns, and risk guardrails.
---

# Rekko — Prediction Market Intelligence

Rekko AI provides deep causal research for prediction markets on Kalshi, Polymarket, and Robinhood. It is the intelligence layer ("the brain") that sits alongside execution skills:

- **PolyClaw** — executes trades on Polymarket
- **Kalshi Trader** — executes trades on Kalshi
- **Rekko** (this skill) — provides the WHY behind market movements

You consume finished insights; Rekko handles all research internally.

## Getting Started

Tools appear as `mcp__rekko__*` when the plugin is installed. Requires `REKKO_API_KEY` — get one at [rekko.ai](https://rekko.ai) or [RapidAPI](https://rapidapi.com/rekko-ai-rekko-ai-default/api/rekko-ai-prediction-market-intelligence).

## Tools

### Market Intelligence

| Tool | Description | Key Parameters |
|---|---|---|
| `list_markets` | Browse current prediction markets | `source` ("kalshi", "polymarket", "robinhood", ""), `limit` (1-100) |
| `get_market` | Get details for a single market | `market_id`, `source` (platform hint) |
| `search_markets` | Search markets by keyword | `query`, `limit` |
| `get_market_history` | Price history with configurable period | `platform`, `market_id`, `period` ("48h", "7d", "30d"), `max_points` |
| `get_resolution` | Resolution intelligence for a market | `platform`, `market_id` — returns time urgency, mechanism, theta estimate |
| `get_execution_guidance` | Execution guidance (spread, slippage, timing) | `platform`, `market_id` — returns order recommendation |

### Screening & Discovery

| Tool | Description | Key Parameters |
|---|---|---|
| `screen_markets` | Batch screen markets by score, volume, or IDs | `market_ids[]`, `platform`, `min_volume_24h`, `min_score`, `limit` |
| `get_calibration` | Signal accuracy and calibration metrics | `category`, `period` ("7d", "30d", "all"), `mode` ("shadow", "live") |

### Deep Research (async pattern)

Analysis takes 30-90 seconds. Use the three-step async pattern:

1. **`analyze_market`** — starts the pipeline, returns an `analysis_id` immediately
   - `bet_text`: describe the market question
   - `platform`: optional platform hint
2. **`check_analysis_status`** — poll with the `analysis_id` every 5 seconds until `status` is `"complete"`
3. **`get_analysis`** — retrieve the full structured result once complete

For convenience, `get_strategy` runs the entire flow as a single blocking call (30-90s).

### Strategy & Portfolio

| Tool | Description | Key Parameters |
|---|---|---|
| `get_strategy` | Full analysis + strategy signal (blocking, 30-90s) | `market_query`, `risk_limit` |
| `get_portfolio_strategy` | Portfolio-aware strategy with position context | `market_query`, `portfolio[]`, `bankroll_usd`, `max_position_pct` |
| `get_consensus` | Consensus probability from aggregated agent trades | `market_id`, `platform`, `period` |

### Arbitrage

| Tool | Description | Key Parameters |
|---|---|---|
| `get_arbitrage` | Cross-platform arbitrage opportunities (cached) | `min_spread` (default 0.02 = 2%) |
| `get_arbitrage_live` | Fresh arbitrage scan (10-30s) | `min_spread` |

### Correlation

| Tool | Description | Key Parameters |
|---|---|---|
| `get_correlation` | Cross-market correlation graph | `market_ids[]`, `platform`, `period` ("48h", "7d", "30d") |

### Trading

| Tool | Description | Key Parameters |
|---|---|---|
| `place_shadow_trade` | Paper trade for tracking | `ticker`, `side` ("yes"/"no"), `size_usd` |
| `report_trade` | Report a trade for consensus aggregation | `market_id`, `platform`, `side`, `size_usd`, `price` |
| `get_portfolio` | Positions and P&L | `mode` ("shadow" or "live") |
| `get_performance` | Aggregate stats (win rate, ROI) | `mode` |
| `check_resolutions` | Settle resolved markets, update P&L | (none) |

### Data Refresh

| Tool | Description | Key Parameters |
|---|---|---|
| `run_scraper` | Fetch fresh market data | `source` ("kalshi", "polymarket", "robinhood", or "arbitrage") |

### Webhooks

| Tool | Description | Key Parameters |
|---|---|---|
| `create_webhook` | Register a webhook for async notifications | `url`, `events[]`, `secret` |
| `list_webhooks` | List registered webhooks | (none) |
| `delete_webhook` | Remove a webhook | `webhook_id` |

## Interpreting Responses

### Recommendation

- **`BUY_YES`** — market underprices the YES outcome, buy YES contracts
- **`BUY_NO`** — market overprices the YES outcome, buy NO contracts
- **`NO_TRADE`** — no actionable edge detected

### Edge

`edge = estimated_probability - market_price`

- **Positive edge** means the market underprices YES (potential BUY_YES)
- **Negative edge** means the market overprices YES (potential BUY_NO)
- Magnitude indicates signal strength (e.g. +0.12 = 12 percentage points of estimated mispricing)

### Confidence

`confidence` ranges from 0.0 to 1.0:

- **0.0 - 0.3** — low confidence, limited data or high uncertainty
- **0.3 - 0.6** — moderate confidence, reasonable evidence base
- **0.6 - 0.8** — high confidence, strong evidence
- **0.8 - 1.0** — very high confidence, near-certain factors identified

### Causal Decomposition

Strategy signals include a `causal` object. Each factor has:

- **`claim`** — the factor statement
- **`direction`** — `supports_yes`, `supports_no`, or `neutral`
- **`weight`** — relative importance (top-level factors sum to ~1.0)
- **`prior`** — base rate probability before evidence
- **`posterior`** — updated probability after evidence
- **`evidence`** — source references supporting this factor

### Arb Score

Arbitrage opportunities include a `score` from 0 to 100:

- **0-30** — minor spread, may not cover fees
- **30-60** — moderate opportunity, worth monitoring
- **60-80** — strong opportunity, actionable
- **80-100** — exceptional spread with good liquidity

Composite: 40% spread magnitude, 20% liquidity, 20% match confidence, 20% execution feasibility.

### Screen Result

`screen_markets` returns scored markets with:

- **`score`** — composite of volume, movement, and signal quality
- **`action`** — `"analyze"` (worth a strategy call), `"watch"` (monitor), or `"skip"` (low value)

Use this to filter before calling the more expensive `get_strategy` tool.

### Execution Guidance

- **`recommendation`** — `"LIMIT_ORDER"`, `"MARKET_ORDER"`, or `"WAIT"`
- **`current_spread`** — current bid-ask spread
- **`estimated_slippage_pct`** — expected slippage for a typical order size

### Resolution Intelligence

- **`time_urgency`** — `"critical"` (< 24h), `"high"` (1-3d), `"medium"` (3-14d), `"low"` (> 14d)
- **`resolution_mechanism`** — how the market resolves (e.g. "scheduled_data_release", "event_outcome")
- **`theta_estimate`** — estimated daily time decay rate

### Consensus View

- **`consensus_probability`** — weighted average probability from reported trades
- **`sample_size`** — number of trades aggregated
- **`divergence_signal`** — `"crowd_agrees"`, `"crowd_disagrees"`, `"strong_divergence"`, or `"neutral"`

### Correlation Graph

- **`pairs`** — list of `{market_a, market_b, correlation, relationship}` entries
- **`clusters`** — groups of correlated markets
- **`concentration_warnings`** — alerts if requested markets are highly correlated

### Calibration Metrics

- **`brier_score`** — lower is better (0.0 = perfect, 0.25 = random)
- **`confidence_buckets`** — hit rate grouped by confidence level
- **`total_signals`** — number of signals in the measurement period

## Workflow Patterns

### Pattern A: Research then Execute

```
1. list_markets(source="kalshi", limit=30)
2. get_strategy(market_query="Will the Fed cut rates at the March 2026 meeting?")
3. IF recommendation == "BUY_YES" AND confidence > 0.5:
     -> chain to Kalshi Trader: buy YES at target_price
4. place_shadow_trade(ticker, side, size_usd)  # track in Rekko portfolio
```

### Pattern B: Arbitrage Discovery

```
1. get_arbitrage(min_spread=0.03)
2. FOR each opportunity with score > 60:
     a. Buy YES on the cheaper platform via the appropriate execution skill
     b. place_shadow_trade() to track the position
3. check_resolutions() periodically to settle
```

### Pattern C: Smart Screening

Screen first, then analyze only high-value candidates (saves 80-90% on strategy costs):

```
1. screen_markets(platform="kalshi", min_volume_24h=50000, min_score=50, limit=50)
2. FOR each result WHERE action == "analyze":
     get_strategy(market_query=title)
3. IF recommendation != "NO_TRADE" AND confidence > 0.5:
     -> execute via Kalshi Trader or PolyClaw
```

### Pattern D: Portfolio-Aware Trading

```
1. get_portfolio(mode="shadow")
2. get_portfolio_strategy(
     market_query="...",
     portfolio=current_positions,
     bankroll_usd=10000,
     max_position_pct=0.05
   )
3. IF recommendation != "NO_TRADE":
     get_correlation(market_ids=[new_market, ...existing_ids])
     IF concentration_warnings is empty: -> execute trade
```

### Pattern E: Heartbeat Loop

Run on a schedule to stay informed:

```
EVERY 30 MINUTES:
  1. run_scraper(source="kalshi")
  2. run_scraper(source="polymarket")
  3. list_markets(limit=10)
  4. get_arbitrage(min_spread=0.02)
  5. FOR promising markets: get_strategy(market_query=title)
  6. check_resolutions()
```

### Pattern F: Consensus-Enhanced Trading

```
1. get_strategy(market_query="...")
2. IF recommendation == "BUY_YES":
     -> execute trade
     report_trade(market_id, platform, side, size_usd, price)
3. LATER:
     get_consensus(market_id, platform)
     IF divergence_signal == "crowd_disagrees": reconsider position
```

## Chaining to Execution Skills

Rekko provides the intelligence; execution skills handle order placement:

- **PolyClaw** — pass `recommendation`, `target_price`, `size_pct` for Polymarket execution
- **Kalshi Trader** — pass `ticker`, `side`, `target_price` for Kalshi order placement

Signal output format is designed to chain directly into these skills.

## Risk Limits

When using Rekko signals for trading, enforce these guardrails:

- **Max 5% of bankroll per position** — even when `size_pct` suggests higher
- **Shadow trade before live** — validate strategies with paper trades first
- **Never trade without edge** — if `recommendation` is `NO_TRADE`, respect it
- **Check freshness** — signals have an `expires_at` timestamp; do not trade stale signals
- **Diversify** — use `get_correlation` to check concentration risk before adding positions
- **Check execution guidance** — call `get_execution_guidance` before large orders to avoid slippage
- **Respect consensus divergence** — if `divergence_signal` is `"crowd_disagrees"`, reconsider
- **Check calibration periodically** — use `get_calibration` to verify signal accuracy
- **Settle regularly** — call `check_resolutions()` to keep P&L accurate

## Pricing

| Tier | Price/call | Example tools |
|---|---|---|
| Free | $0.00 | `get_calibration` |
| Listing | $0.01 | `list_markets`, `search_markets`, `get_market_history` |
| Insight | $0.10 | `analyze_market`, `screen_markets`, `get_resolution` |
| Strategy | $2.00 | `get_strategy`, `get_portfolio_strategy`, `get_consensus`, `report_trade` |
| Deep | $5.00 | `get_arbitrage`, `get_correlation`, `create_webhook` |

Check current rates at `get_calibration` (free) or visit [rekko.ai](https://rekko.ai).
