"""Rekko AI MCP server — thin proxy to api.rekko.ai.

Every tool proxies to the corresponding Feed API endpoint. No local state,
no analysis logic, no proprietary methodology. Intelligence stays behind
the API paywall.

Auth: set REKKO_API_KEY env var (get one at https://rekko.ai).
"""

from __future__ import annotations

import json
import os
from typing import Annotated

import httpx
from fastmcp import FastMCP
from pydantic import Field

REKKO_API_BASE = "https://api.rekko.ai"

mcp = FastMCP(
    "rekko",
    instructions=(
        "Rekko AI provides prediction market intelligence for Kalshi, "
        "Polymarket, and Robinhood — deep causal research, arbitrage detection, "
        "screening, and strategy signals. Use these tools to browse markets, "
        "trigger analysis pipelines, scan for arbitrage, and get actionable "
        "trading signals."
    ),
)


def _get_client() -> httpx.AsyncClient:
    api_key = os.environ.get("REKKO_API_KEY", "")
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return httpx.AsyncClient(
        base_url=os.environ.get("REKKO_API_URL", REKKO_API_BASE),
        headers=headers,
        timeout=300.0,
    )


_UPGRADE_MSG = (
    "Set REKKO_API_KEY to access this tool. "
    "Get a free key at https://rekko.ai/dashboard"
)


async def _request(method: str, path: str, **kwargs) -> str:
    try:
        async with _get_client() as client:
            resp = await client.request(method, path, **kwargs)
            if resp.status_code in (401, 403):
                return json.dumps({
                    "error": "auth_required",
                    "detail": _UPGRADE_MSG,
                })
            if resp.status_code == 402:
                return json.dumps({
                    "error": "payment_required",
                    "detail": "This endpoint requires a paid API key. "
                    "Upgrade at https://rekko.ai or https://rapidapi.com/rekko-ai-rekko-ai-default/api/rekko-ai-prediction-market-intelligence",
                })
            if resp.status_code == 404:
                return json.dumps({
                    "error": "not_found",
                    "detail": f"Resource not found: {method} {path}",
                })
            if resp.status_code == 422:
                body = resp.text
                return json.dumps({
                    "error": "validation_error",
                    "detail": f"Invalid request parameters: {body[:500]}",
                })
            if resp.status_code == 429:
                return json.dumps({
                    "error": "rate_limited",
                    "detail": "Too many requests. Wait a moment and try again.",
                })
            if resp.status_code >= 500:
                return json.dumps({
                    "error": "server_error",
                    "detail": f"Rekko API returned {resp.status_code}. Try again shortly.",
                })
            resp.raise_for_status()
            return resp.text
    except httpx.ConnectError:
        return json.dumps({
            "error": "connection_error",
            "detail": "Could not connect to api.rekko.ai. Check your network connection.",
        })
    except httpx.TimeoutException:
        return json.dumps({
            "error": "timeout",
            "detail": "Request to Rekko API timed out. The analysis may still be running — try checking status.",
        })


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


@mcp.prompt()
def analyze_bet(market_question: str) -> str:
    """Analyze a prediction market bet end-to-end: research, strategy signal, and trade recommendation."""
    return (
        f"Analyze this prediction market bet: {market_question}\n\n"
        "1. Use market.data.search to find the market\n"
        "2. Use market.data.history and market.data.resolution for context\n"
        "3. Use research.signal.signal for a full analysis with position sizing\n"
        "4. Summarize: probability, edge, recommended action, and size"
    )


@mcp.prompt()
def find_arbitrage(min_spread: str = "3") -> str:
    """Scan for cross-platform arbitrage opportunities between Kalshi and Polymarket."""
    return (
        f"Find prediction market arbitrage opportunities with at least {min_spread}% spread.\n\n"
        "1. Use market.arb.live to run a fresh cross-platform scan\n"
        "2. For the top 3 opportunities, use market.data.get on each side to verify prices are current\n"
        "3. For the most promising opportunity, use market.data.history on both platforms to check if the spread is persistent or closing\n"
        "4. Present a table: market, Kalshi price, Polymarket price, spread %, and whether to act now or wait"
    )


@mcp.prompt()
def screen_top_markets(category: str = "") -> str:
    """Find the best prediction markets to trade right now based on volume, movement, and opportunity."""
    cat_filter = f' in the "{category}" category' if category else ""
    return (
        f"Find the most actionable prediction markets{cat_filter}.\n\n"
        "1. Use market.data.screen to get scored markets sorted by opportunity\n"
        "2. Filter to markets with action='analyze' (skip 'watch' and 'skip')\n"
        "3. For the top 3, use market.data.history to check recent price movement\n"
        "4. Present a ranked list with: title, current price, 24h volume, score, and a one-line thesis on why it's interesting"
    )


@mcp.prompt()
def portfolio_review() -> str:
    """Review trading performance and get recommendations for next moves."""
    return (
        "Review my prediction market trading performance and suggest next moves.\n\n"
        "1. Use analytics.performance to get aggregate stats (win rate, ROI, total P&L)\n"
        "2. Use market.data.list to see the current top markets\n"
        "3. Summarize performance and recommend the most actionable opportunities"
    )


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@mcp.resource("rekko://platforms")
def platforms_resource() -> str:
    """Supported prediction market platforms and their capabilities."""
    return json.dumps({
        "platforms": [
            {
                "name": "Kalshi",
                "id": "kalshi",
                "type": "regulated",
                "regulator": "CFTC",
                "data": True,
                "url": "https://kalshi.com",
            },
            {
                "name": "Polymarket",
                "id": "polymarket",
                "type": "decentralized",
                "chain": "Polygon",
                "data": True,
                "url": "https://polymarket.com",
            },
            {
                "name": "Robinhood",
                "id": "robinhood",
                "type": "brokerage",
                "data": True,
                "url": "https://robinhood.com/prediction-markets",
                "note": "Data only — no public trading API",
            },
        ],
        "arbitrage": {
            "supported_pairs": ["kalshi-polymarket", "kalshi-robinhood"],
            "min_spread_default": 0.02,
        },
    })


@mcp.resource("rekko://pricing")
def pricing_resource() -> str:
    """API pricing tiers and rate limits."""
    return json.dumps({
        "currency": "USDC",
        "free_plan": {
            "price": "$0/month",
            "includes": {"listing": 100, "insight": 10},
            "rate_limit": "30 req/min",
            "signup": "https://rekko.ai/dashboard",
        },
        "pro_plan": {
            "price": "$49/month",
            "includes": {"listing": 10000, "insight": 500, "strategy": 50, "deep": 10},
            "rate_limit": "120 req/min",
            "upgrade": "https://rekko.ai/dashboard",
        },
        "tiers": {
            "listing": {"per_call": "$0.01", "endpoints": ["markets", "history", "search"]},
            "insight": {"per_call": "$0.10", "endpoints": ["analysis", "screening", "resolution"]},
            "strategy": {"per_call": "$2.00", "endpoints": ["signals", "execution", "consensus"]},
            "deep": {"per_call": "$5.00", "endpoints": ["arbitrage", "correlation", "webhooks"]},
        },
        "x402": {
            "enabled": True,
            "network": "Base L2",
            "asset": "USDC",
            "note": "Pay-per-call with no account needed",
        },
    })


# ---------------------------------------------------------------------------
# market.data.*  — browse, search, and inspect prediction markets
# ---------------------------------------------------------------------------


@mcp.tool(
    name="market.data.list",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def list_markets(
    source: Annotated[str, Field(description='Filter by platform: "kalshi", "polymarket", or "" for all.')] = "",
    limit: Annotated[int, Field(description="Maximum number of markets to return (1-100).")] = 30,
) -> str:
    """List current prediction markets from Kalshi, Polymarket, and Robinhood."""
    params: dict = {"limit": limit}
    if source:
        params["source"] = source
    return await _request("GET", "/v1/markets", params=params)


@mcp.tool(
    name="market.data.get",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_market(
    platform: Annotated[str, Field(description='Platform: "kalshi", "polymarket", or "robinhood".')],
    market_id: Annotated[str, Field(description="Platform-specific market identifier (e.g. Kalshi ticker or Polymarket slug).")],
) -> str:
    """Get detailed information about a specific prediction market."""
    return await _request("GET", f"/v1/markets/{platform}/{market_id}")


@mcp.tool(
    name="market.data.search",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def search_markets(
    query: Annotated[str, Field(description="Search query string to match against market titles.")],
    limit: Annotated[int, Field(description="Maximum number of results to return.")] = 20,
) -> str:
    """Search prediction markets by keyword in market title."""
    return await _request("GET", "/v1/markets", params={"query": query, "limit": limit})


@mcp.tool(
    name="market.data.history",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_market_history(
    platform: Annotated[str, Field(description='Platform: "kalshi", "polymarket", or "robinhood".')],
    market_id: Annotated[str, Field(description="Platform-specific market identifier.")],
    period: Annotated[str, Field(description='History window: "48h", "7d", or "30d".')] = "7d",
    max_points: Annotated[int, Field(description="Maximum data points to return.")] = 48,
) -> str:
    """Get price history for a prediction market over a configurable period."""
    return await _request(
        "GET",
        f"/v1/markets/{platform}/{market_id}/history",
        params={"period": period, "max_points": max_points},
    )


@mcp.tool(
    name="market.data.resolution",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_resolution(
    platform: Annotated[str, Field(description='Platform: "kalshi", "polymarket", or "robinhood".')],
    market_id: Annotated[str, Field(description="Platform-specific market identifier.")],
) -> str:
    """Get resolution intelligence for a market — time urgency, mechanism, theta estimate."""
    return await _request("GET", f"/v1/markets/{platform}/{market_id}/resolution")


@mcp.tool(
    name="market.data.execution",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_execution_guidance(
    platform: Annotated[str, Field(description='Platform: "kalshi", "polymarket", or "robinhood".')],
    market_id: Annotated[str, Field(description="Platform-specific market identifier.")],
) -> str:
    """Get execution guidance for a market — spread analysis, slippage estimate, order recommendation."""
    return await _request("GET", f"/v1/markets/{platform}/{market_id}/execution")


@mcp.tool(
    name="market.data.screen",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def screen_markets(
    market_ids: Annotated[list[str] | None, Field(description="Optional list of specific market IDs to screen.")] = None,
    platform: Annotated[str, Field(description='Filter by platform: "kalshi", "polymarket", or "" for all.')] = "",
    min_volume_24h: Annotated[float, Field(description="Minimum 24h volume filter.")] = 0.0,
    min_score: Annotated[float, Field(description="Minimum composite score filter.")] = 0.0,
    limit: Annotated[int, Field(description="Maximum number of results to return.")] = 50,
) -> str:
    """Batch screen markets by score, volume, or specific IDs.

    Returns scored markets with an action recommendation: "analyze", "watch", or "skip".
    """
    body: dict = {"limit": limit}
    if market_ids:
        body["market_ids"] = market_ids
    if platform:
        body["platform"] = platform
    if min_volume_24h > 0:
        body["min_volume_24h"] = min_volume_24h
    if min_score > 0:
        body["min_score"] = min_score
    return await _request("POST", "/v1/screen", json=body)


# ---------------------------------------------------------------------------
# research.pipe.*  — deep research analysis pipelines
# ---------------------------------------------------------------------------


@mcp.tool(
    name="research.pipe.start",
    annotations={"readOnlyHint": False, "openWorldHint": True},
)
async def analyze_market(
    platform: Annotated[str, Field(description='Platform: "kalshi", "polymarket", or "robinhood".')],
    market_id: Annotated[str, Field(description="Platform-specific market identifier (e.g. Kalshi ticker or Polymarket slug).")],
) -> str:
    """Start a deep research analysis for a specific prediction market.

    Returns immediately with an analysis_id, platform, and market_id.
    Poll with research.pipe.status every 10 seconds until complete,
    then retrieve results with research.pipe.get.
    """
    return await _request("POST", f"/v1/markets/{platform}/{market_id}/analyze")


@mcp.tool(
    name="research.pipe.status",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def check_analysis_status(
    platform: Annotated[str, Field(description='Platform: "kalshi", "polymarket", or "robinhood".')],
    market_id: Annotated[str, Field(description="Platform-specific market identifier.")],
    analysis_id: Annotated[str, Field(description="Analysis identifier returned by research.pipe.start (rk-...).")],
) -> str:
    """Check the current status of a running or completed analysis."""
    return await _request(
        "GET",
        f"/v1/markets/{platform}/{market_id}/analyze/{analysis_id}/status",
    )


@mcp.tool(
    name="research.pipe.get",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_analysis(
    platform: Annotated[str, Field(description='Platform: "kalshi", "polymarket", or "robinhood".')],
    market_id: Annotated[str, Field(description="Platform-specific market identifier.")],
) -> str:
    """Retrieve the latest analysis result for a market.

    Includes probability estimate, edge assessment, scenarios, key factors,
    risks, and trading recommendation.
    """
    return await _request("GET", f"/v1/markets/{platform}/{market_id}/analysis")


@mcp.tool(
    name="research.pipe.list",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def list_analyses(
    limit: Annotated[int, Field(description="Maximum number of analyses to return.")] = 20,
) -> str:
    """List recent analyses with summary information."""
    return await _request("GET", "/v1/analyses", params={"limit": limit})


# ---------------------------------------------------------------------------
# research.signal.*  — signals, portfolio strategy, calibration, consensus
# ---------------------------------------------------------------------------


@mcp.tool(
    name="research.signal.signal",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_strategy(
    market_query: Annotated[str, Field(description="Description of the bet or market question to analyze.")],
    risk_limit: Annotated[float, Field(description="Reserved for position sizing constraints.")] = 0.0,
) -> str:
    """Run a full analysis and return a strategy signal with causal decomposition.

    This is a blocking call that takes 30-90 seconds. For async control, use
    research.pipe.start + research.pipe.status + research.pipe.get instead.
    """
    body: dict = {"market_query": market_query}
    if risk_limit > 0:
        body["risk_limit"] = risk_limit
    return await _request("POST", "/v1/signals", params={"wait": "true"}, json=body)


@mcp.tool(
    name="research.signal.portfolio",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_portfolio_strategy(
    market_query: Annotated[str, Field(description="Description of the bet or market question to analyze.")],
    portfolio: Annotated[list[dict] | None, Field(description="Optional list of current positions (dicts with ticker, side, size_usd).")] = None,
    bankroll_usd: Annotated[float, Field(description="Total bankroll in USD for position sizing.")] = 10000.0,
    max_position_pct: Annotated[float, Field(description="Maximum fraction of bankroll per position.")] = 0.05,
) -> str:
    """Get a portfolio-aware strategy signal with position context and correlation analysis."""
    body: dict = {
        "market_query": market_query,
        "bankroll_usd": bankroll_usd,
        "max_position_pct": max_position_pct,
    }
    if portfolio:
        body["portfolio"] = portfolio
    return await _request("POST", "/v1/signals/portfolio", params={"wait": "true"}, json=body)


@mcp.tool(
    name="research.signal.calibration",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_calibration(
    category: Annotated[str, Field(description='Filter by category (e.g. "crypto", "politics") or "" for all.')] = "",
    period: Annotated[str, Field(description='Time period: "7d", "30d", "90d", or "all".')] = "all",
) -> str:
    """Get signal accuracy and calibration metrics — Brier score, hit rates, total signals."""
    params: dict = {"period": period}
    if category:
        params["category"] = category
    return await _request("GET", "/v1/calibration", params=params)


@mcp.tool(
    name="research.signal.consensus",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_consensus(
    platform: Annotated[str, Field(description='Platform: "kalshi" or "polymarket".')],
    market_id: Annotated[str, Field(description="Platform-specific market identifier.")],
    period: Annotated[str, Field(description='Lookback period: "24h", "7d", or "30d".')] = "7d",
) -> str:
    """Get consensus probability from aggregated agent trades."""
    return await _request(
        "GET",
        f"/v1/markets/{platform}/{market_id}/consensus",
        params={"period": period},
    )


# ---------------------------------------------------------------------------
# market.arb.*  — cross-platform spread detection and correlation
# ---------------------------------------------------------------------------


@mcp.tool(
    name="market.arb.get",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_arbitrage(
    min_spread: Annotated[float, Field(description="Minimum spread threshold (0.0-1.0). Default 0.02 (2%).")] = 0.02,
) -> str:
    """Get cross-platform arbitrage opportunities between Kalshi and Polymarket (cached)."""
    return await _request("GET", "/v1/arbitrage", params={"min_spread": min_spread})


@mcp.tool(
    name="market.arb.live",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_arbitrage_live(
    min_spread: Annotated[float, Field(description="Minimum spread threshold (0.0-1.0). Default 0.02 (2%).")] = 0.02,
) -> str:
    """Run a fresh cross-platform arbitrage scan (may take 10-30 seconds)."""
    return await _request("GET", "/v1/arbitrage/live", params={"min_spread": min_spread})


@mcp.tool(
    name="market.arb.correlation",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_correlation(
    market_ids: Annotated[list[str], Field(description="List of market IDs to correlate (minimum 2).")],
    platform: Annotated[str, Field(description='Platform: "kalshi" or "polymarket".')] = "kalshi",
    period: Annotated[str, Field(description='Lookback period: "48h", "7d", or "30d".')] = "7d",
) -> str:
    """Compute cross-market correlation graph for portfolio diversification analysis."""
    return await _request(
        "POST",
        "/v1/correlation",
        json={"market_ids": market_ids, "platform": platform, "period": period},
    )


# ---------------------------------------------------------------------------
# analytics.*  — performance tracking and reporting
# ---------------------------------------------------------------------------


@mcp.tool(
    name="analytics.performance",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_performance() -> str:
    """Get aggregate trading performance statistics — win rate, ROI, total P&L."""
    return await _request("GET", "/v1/performance")


@mcp.tool(
    name="analytics.report",
    annotations={"readOnlyHint": False, "openWorldHint": True},
)
async def report_trade(
    market_id: Annotated[str, Field(description="Platform-specific market identifier.")],
    platform: Annotated[str, Field(description='Platform: "kalshi" or "polymarket".')],
    side: Annotated[str, Field(description='Trade direction: "yes" or "no".')],
    size_usd: Annotated[float, Field(description="Trade size in USD.")],
    price: Annotated[float, Field(description="Execution price (0.0-1.0).")],
) -> str:
    """Report a trade for consensus probability aggregation."""
    return await _request(
        "POST",
        "/v1/trades/report",
        json={
            "market_id": market_id,
            "platform": platform,
            "side": side,
            "size_usd": size_usd,
            "price": price,
        },
    )


# ---------------------------------------------------------------------------
# trade.hooks.*  — real-time event notifications
# ---------------------------------------------------------------------------


@mcp.tool(
    name="trade.hooks.create",
    annotations={"readOnlyHint": False, "openWorldHint": True},
)
async def create_webhook(
    url: Annotated[str, Field(description="HTTPS URL to receive POST notifications.")],
    events: Annotated[list[str], Field(description='Event types: "whale_alert", "price_shift", "analysis_complete".')],
    secret: Annotated[str, Field(description="Optional shared secret for HMAC signature verification.")] = "",
) -> str:
    """Register a webhook for real-time event notifications."""
    body: dict = {"url": url, "events": events}
    if secret:
        body["secret"] = secret
    return await _request("POST", "/v1/webhooks", json=body)


@mcp.tool(
    name="trade.hooks.list",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def list_webhooks(
    limit: Annotated[int, Field(description="Maximum number of webhooks to return.")] = 100,
) -> str:
    """List registered webhooks."""
    return await _request("GET", "/v1/webhooks", params={"limit": limit})


@mcp.tool(
    name="trade.hooks.delete",
    annotations={"readOnlyHint": False, "openWorldHint": True},
)
async def delete_webhook(
    webhook_id: Annotated[str, Field(description="Webhook identifier returned by trade.hooks.create.")],
) -> str:
    """Remove a registered webhook."""
    return await _request("DELETE", f"/v1/webhooks/{webhook_id}")


# ---------------------------------------------------------------------------
# help.*  — developer onboarding
# ---------------------------------------------------------------------------


@mcp.tool(
    name="help.quickstart",
    annotations={"readOnlyHint": True, "openWorldHint": False},
)
async def quickstart(
    language: Annotated[str, Field(description='Code example language: "python", "curl", or "mcp_config".')] = "python",
) -> str:
    """Get a quickstart code snippet to make your first Rekko API call.

    Returns a working code example for the specified language that lists
    prediction markets and runs a basic analysis.
    """
    snippets = {
        "python": (
            "# pip install httpx\n"
            "import httpx\n\n"
            "API_KEY = 'your_api_key'  # Get one free at https://rekko.ai/dashboard\n"
            "BASE = 'https://api.rekko.ai/v1'\n"
            "headers = {'Authorization': f'Bearer {API_KEY}'}\n\n"
            "# List top prediction markets\n"
            "markets = httpx.get(f'{BASE}/markets', headers=headers).json()\n"
            "for m in markets[:5]:\n"
            "    print(f\"{m['title']} — {m['yes_price']:.0%} YES ({m['platform']})\")\n\n"
            "# Get details on a specific market\n"
            "market = markets[0]\n"
            "detail = httpx.get(\n"
            "    f\"{BASE}/markets/{market['platform']}/{market['market_id']}\",\n"
            "    headers=headers,\n"
            ").json()\n"
            "print(f\"Current price: {detail['yes_price']:.0%}\")\n"
        ),
        "curl": (
            "# List top prediction markets\n"
            "curl -H 'Authorization: Bearer YOUR_API_KEY' \\\n"
            "  https://api.rekko.ai/v1/markets\n\n"
            "# Get a specific market\n"
            "curl -H 'Authorization: Bearer YOUR_API_KEY' \\\n"
            "  https://api.rekko.ai/v1/markets/kalshi/KXBTC-100K\n\n"
            "# Trigger AI analysis\n"
            "curl -X POST -H 'Authorization: Bearer YOUR_API_KEY' \\\n"
            "  https://api.rekko.ai/v1/markets/kalshi/KXBTC-100K/analyze\n"
        ),
        "mcp_config": (
            "# Add to your Claude Code MCP config (~/.claude.json or .mcp.json):\n"
            "{\n"
            '  "mcpServers": {\n'
            '    "rekko": {\n'
            '      "command": "uvx",\n'
            '      "args": ["rekko-mcp"],\n'
            '      "env": {\n'
            '        "REKKO_API_KEY": "your_api_key"\n'
            "      }\n"
            "    }\n"
            "  }\n"
            "}\n\n"
            "# Then ask Claude: 'List prediction markets' or 'Analyze KXBTC-100K on Kalshi'\n"
            "# Get a free API key at https://rekko.ai/dashboard\n"
        ),
    }
    lang = language.lower().replace(" ", "_")
    if lang not in snippets:
        return json.dumps({
            "error": f"Unknown language '{language}'. Choose: python, curl, mcp_config",
            "available": list(snippets.keys()),
        })
    return json.dumps({
        "language": lang,
        "snippet": snippets[lang],
        "signup_url": "https://rekko.ai/dashboard",
        "docs_url": "https://rekko.ai/docs",
        "platforms": ["kalshi", "polymarket", "robinhood"],
    })
