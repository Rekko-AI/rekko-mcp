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
        "Rekko AI provides prediction market intelligence for Kalshi and "
        "Polymarket — deep causal research, arbitrage detection, screening, "
        "and strategy signals. Use these tools to browse markets, run analysis "
        "pipelines, scan for arbitrage, manage a shadow portfolio, and get "
        "actionable trading signals."
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
        resp.raise_for_status()
        return resp.text


# ---------------------------------------------------------------------------
# markets.*  — browse, search, and inspect prediction markets
# ---------------------------------------------------------------------------


@mcp.tool(
    name="markets.list",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def list_markets(
    source: Annotated[str, Field(description='Filter by platform: "kalshi", "polymarket", or "" for all.')] = "",
    limit: Annotated[int, Field(description="Maximum number of markets to return (1-100).")] = 30,
) -> str:
    """List current prediction markets from Kalshi and Polymarket."""
    params: dict = {"limit": limit}
    if source:
        params["source"] = source
    return await _request("GET", "/v1/markets", params=params)


@mcp.tool(
    name="markets.get",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_market(
    market_id: Annotated[str, Field(description="Platform-specific market identifier (e.g. Kalshi ticker or Polymarket slug).")],
    source: Annotated[str, Field(description='Platform hint: "kalshi", "polymarket", or "" to search both.')] = "",
) -> str:
    """Get detailed information about a specific prediction market."""
    if source:
        return await _request("GET", f"/v1/markets/{source}/{market_id}")
    return await _request("GET", "/v1/markets", params={"query": market_id, "limit": 1})


@mcp.tool(
    name="markets.search",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def search_markets(
    query: Annotated[str, Field(description="Search query string to match against market titles.")],
    limit: Annotated[int, Field(description="Maximum number of results to return.")] = 20,
) -> str:
    """Search prediction markets by keyword in market title."""
    return await _request("GET", "/v1/markets", params={"query": query, "limit": limit})


@mcp.tool(
    name="markets.history",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_market_history(
    platform: Annotated[str, Field(description='Platform: "kalshi" or "polymarket".')],
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
    name="markets.resolution",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_resolution(
    platform: Annotated[str, Field(description='Platform: "kalshi" or "polymarket".')],
    market_id: Annotated[str, Field(description="Platform-specific market identifier.")],
) -> str:
    """Get resolution intelligence for a market — time urgency, mechanism, theta estimate."""
    return await _request("GET", f"/v1/markets/{platform}/{market_id}/resolution")


@mcp.tool(
    name="markets.execution",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_execution_guidance(
    platform: Annotated[str, Field(description='Platform: "kalshi" or "polymarket".')],
    market_id: Annotated[str, Field(description="Platform-specific market identifier.")],
) -> str:
    """Get execution guidance for a market — spread analysis, slippage estimate, order recommendation."""
    return await _request("GET", f"/v1/markets/{platform}/{market_id}/execution")


@mcp.tool(
    name="markets.screen",
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


@mcp.tool(
    name="markets.scrape",
    annotations={"readOnlyHint": False, "openWorldHint": True},
)
async def run_scraper(
    source: Annotated[str, Field(description='Which scraper to run: "kalshi", "polymarket", or "arbitrage".')],
) -> str:
    """Fetch fresh market data from a platform scraper."""
    return await _request("POST", "/v1/scrapers/run", json={"source": source})


# ---------------------------------------------------------------------------
# analysis.*  — deep research pipelines
# ---------------------------------------------------------------------------


@mcp.tool(
    name="analysis.start",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def analyze_market(
    bet_text: Annotated[str, Field(description="Description of the bet or market question to analyze.")],
    platform: Annotated[str, Field(description='Source platform hint: "kalshi", "polymarket", or "".')] = "",
) -> str:
    """Start a deep research analysis pipeline for a prediction market bet.

    Returns immediately with an analysis_id. Poll with analysis.status
    every 5 seconds until complete, then retrieve results with analysis.get.
    """
    body: dict = {"bet_text": bet_text}
    if platform:
        body["platform"] = platform
    return await _request("POST", "/v1/insights", json=body)


@mcp.tool(
    name="analysis.status",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def check_analysis_status(
    analysis_id: Annotated[str, Field(description="Analysis identifier returned by analysis.start.")],
) -> str:
    """Check the current status of a running or completed analysis."""
    return await _request("GET", f"/v1/insights/{analysis_id}/status")


@mcp.tool(
    name="analysis.get",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_analysis(
    analysis_id: Annotated[str, Field(description="Analysis identifier for a completed analysis.")],
) -> str:
    """Retrieve the full structured analysis result for a completed analysis.

    Includes probability estimate, edge assessment, scenarios, key factors,
    risks, and trading recommendation.
    """
    return await _request("GET", f"/v1/insights/{analysis_id}")


@mcp.tool(
    name="analysis.list",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def list_analyses(
    limit: Annotated[int, Field(description="Maximum number of analyses to return.")] = 20,
) -> str:
    """List recent analyses with summary information."""
    return await _request("GET", "/v1/analyses", params={"limit": limit})


# ---------------------------------------------------------------------------
# strategy.*  — signals, portfolio strategy, calibration, consensus
# ---------------------------------------------------------------------------


@mcp.tool(
    name="strategy.signal",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_strategy(
    market_query: Annotated[str, Field(description="Description of the bet or market question to analyze.")],
    risk_limit: Annotated[float, Field(description="Reserved for position sizing constraints.")] = 0.0,
) -> str:
    """Run a full analysis and return a strategy signal with causal decomposition.

    This is a blocking call that takes 30-90 seconds. For async control, use
    analysis.start + analysis.status + analysis.get instead.
    """
    body: dict = {"market_query": market_query}
    if risk_limit > 0:
        body["risk_limit"] = risk_limit
    return await _request("POST", "/v1/signals", json=body)


@mcp.tool(
    name="strategy.portfolio",
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
    return await _request("POST", "/v1/signals/portfolio", json=body)


@mcp.tool(
    name="strategy.calibration",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_calibration(
    category: Annotated[str, Field(description='Filter by category (e.g. "crypto", "politics") or "" for all.')] = "",
    period: Annotated[str, Field(description='Time period: "7d", "30d", "90d", or "all".')] = "all",
    mode: Annotated[str, Field(description='Trading mode: "shadow" or "live".')] = "shadow",
) -> str:
    """Get signal accuracy and calibration metrics — Brier score, hit rates, total signals."""
    params: dict = {"period": period, "mode": mode}
    if category:
        params["category"] = category
    return await _request("GET", "/v1/calibration", params=params)


@mcp.tool(
    name="strategy.consensus",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_consensus(
    market_id: Annotated[str, Field(description="Platform-specific market identifier.")],
    platform: Annotated[str, Field(description='Platform: "kalshi" or "polymarket".')] = "kalshi",
    period: Annotated[str, Field(description='Lookback period: "48h", "7d", or "30d".')] = "7d",
) -> str:
    """Get consensus probability from aggregated agent trades."""
    return await _request(
        "GET",
        f"/v1/markets/{platform}/{market_id}/consensus",
        params={"period": period},
    )


# ---------------------------------------------------------------------------
# arbitrage.*  — cross-platform spread detection and correlation
# ---------------------------------------------------------------------------


@mcp.tool(
    name="arbitrage.get",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_arbitrage(
    min_spread: Annotated[float, Field(description="Minimum spread threshold (0.0-1.0). Default 0.02 (2%).")] = 0.02,
) -> str:
    """Get cross-platform arbitrage opportunities between Kalshi and Polymarket (cached)."""
    return await _request("GET", "/v1/arbitrage", params={"min_spread": min_spread})


@mcp.tool(
    name="arbitrage.live",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_arbitrage_live(
    min_spread: Annotated[float, Field(description="Minimum spread threshold (0.0-1.0). Default 0.02 (2%).")] = 0.02,
) -> str:
    """Run a fresh cross-platform arbitrage scan (may take 10-30 seconds)."""
    return await _request("GET", "/v1/arbitrage/live", params={"min_spread": min_spread})


@mcp.tool(
    name="arbitrage.correlation",
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
# trading.*  — shadow trades, reporting, portfolio, performance
# ---------------------------------------------------------------------------


@mcp.tool(
    name="trading.shadow",
    annotations={"readOnlyHint": False, "openWorldHint": True},
)
async def place_shadow_trade(
    ticker: Annotated[str, Field(description='Market ticker symbol (e.g. "KXBTC-100K").')],
    side: Annotated[str, Field(description='Trade direction: "yes" or "no".')],
    size_usd: Annotated[float, Field(description="Trade size in USD.")],
) -> str:
    """Place a paper (shadow) trade on a prediction market for tracking purposes."""
    return await _request(
        "POST",
        "/v1/trades/shadow",
        json={"ticker": ticker, "side": side, "size_usd": size_usd},
    )


@mcp.tool(
    name="trading.report",
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


@mcp.tool(
    name="trading.portfolio",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_portfolio(
    mode: Annotated[str, Field(description='Portfolio mode: "shadow" for paper trades, "live" for real trades.')] = "shadow",
) -> str:
    """Get current portfolio positions and performance summary."""
    return await _request("GET", "/v1/portfolio", params={"mode": mode})


@mcp.tool(
    name="trading.performance",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_performance(
    mode: Annotated[str, Field(description='Portfolio mode: "shadow" for paper trades, "live" for real trades.')] = "shadow",
) -> str:
    """Get aggregate trading performance statistics."""
    return await _request("GET", "/v1/performance", params={"mode": mode})


@mcp.tool(
    name="trading.resolve",
    annotations={"readOnlyHint": False, "openWorldHint": True},
)
async def check_resolutions() -> str:
    """Check all open trades for market resolution and update P&L."""
    return await _request("POST", "/v1/trades/resolve")


# ---------------------------------------------------------------------------
# webhooks.*  — real-time event notifications
# ---------------------------------------------------------------------------


@mcp.tool(
    name="webhooks.create",
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
    name="webhooks.list",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def list_webhooks() -> str:
    """List registered webhooks."""
    return await _request("GET", "/v1/webhooks")


@mcp.tool(
    name="webhooks.delete",
    annotations={"readOnlyHint": False, "openWorldHint": True},
)
async def delete_webhook(
    webhook_id: Annotated[str, Field(description="Webhook identifier returned by webhooks.create.")],
) -> str:
    """Remove a registered webhook."""
    return await _request("DELETE", f"/v1/webhooks/{webhook_id}")
