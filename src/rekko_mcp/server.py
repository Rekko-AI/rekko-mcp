"""Rekko AI MCP server — thin proxy to api.rekko.ai.

Every tool proxies to the corresponding Feed API endpoint. No local state,
no analysis logic, no proprietary methodology. Intelligence stays behind
the API paywall.

Auth: set REKKO_API_KEY env var (get one at https://rekko.ai).
"""
from __future__ import annotations

import json
import os

import httpx
from fastmcp import FastMCP
from mcp.types import ToolAnnotations
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

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


@mcp.prompt()
def research_workflow() -> str:
    """Step-by-step workflow for researching and trading a prediction market."""
    return (
        "1. Use list_markets to browse current prediction markets\n"
        "2. Use screen_markets to find high-value candidates (action='analyze')\n"
        "3. Use get_strategy on promising markets for a full AI analysis with causal decomposition\n"
        "4. Check get_execution_guidance for spread and slippage before trading\n"
        "5. Use place_shadow_trade to paper trade, or chain to an execution skill for live trades\n"
        "6. Use get_portfolio and get_performance to track results\n"
        "7. Use check_resolutions periodically to settle resolved markets"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_client() -> httpx.AsyncClient:
    api_key = os.environ.get("REKKO_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "REKKO_API_KEY is not set. Get an API key at https://rekko.ai "
            "or subscribe via https://rapidapi.com/rekko-ai-rekko-ai-default/api/rekko-ai-prediction-market-intelligence"
        )
    return httpx.AsyncClient(
        base_url=os.environ.get("REKKO_API_URL", REKKO_API_BASE),
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=300.0,
    )


async def _request(method: str, path: str, **kwargs) -> str:
    async with _get_client() as client:
        resp = await client.request(method, path, **kwargs)
        if resp.status_code == 402:
            return json.dumps({
                "error": "payment_required",
                "detail": "This endpoint requires a paid API key. "
                "Upgrade at https://rekko.ai or https://rapidapi.com/rekko-ai-rekko-ai-default/api/rekko-ai-prediction-market-intelligence",
            })
        resp.raise_for_status()
        return resp.text


# Shared annotation sets
_READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=True)
_READ_IDEM = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)
_WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True)
_WRITE_SLOW = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True)


# ---------------------------------------------------------------------------
# Market intelligence
# ---------------------------------------------------------------------------


@mcp.tool(annotations=_READ)
async def list_markets(
    source: str = Field("", description="Filter by platform: 'kalshi', 'polymarket', or '' for all"),
    limit: int = Field(30, description="Maximum number of markets to return (1-100)"),
) -> str:
    """List current prediction markets from Kalshi and Polymarket."""
    params: dict = {"limit": limit}
    if source:
        params["source"] = source
    return await _request("GET", "/v1/markets", params=params)


@mcp.tool(annotations=_READ)
async def get_market(
    market_id: str = Field(description="Platform-specific market identifier (e.g. Kalshi ticker or Polymarket slug)"),
    source: str = Field("", description="Platform hint: 'kalshi', 'polymarket', or '' to search both"),
) -> str:
    """Get detailed information about a specific prediction market."""
    if source:
        return await _request("GET", f"/v1/markets/{source}/{market_id}")
    return await _request("GET", "/v1/markets", params={"query": market_id, "limit": 1})


@mcp.tool(annotations=_READ)
async def search_markets(
    query: str = Field(description="Search query string to match against market titles"),
    limit: int = Field(20, description="Maximum number of results to return"),
) -> str:
    """Search prediction markets by keyword in market title."""
    return await _request("GET", "/v1/markets", params={"query": query, "limit": limit})


@mcp.tool(annotations=_READ_IDEM)
async def get_market_history(
    platform: str = Field(description="Platform: 'kalshi' or 'polymarket'"),
    market_id: str = Field(description="Platform-specific market identifier"),
    period: str = Field("7d", description="History window: '48h', '7d', or '30d'"),
    max_points: int = Field(48, description="Maximum data points to return"),
) -> str:
    """Get price history for a prediction market over a configurable period."""
    return await _request(
        "GET",
        f"/v1/markets/{platform}/{market_id}/history",
        params={"period": period, "max_points": max_points},
    )


@mcp.tool(annotations=_READ)
async def get_resolution(
    platform: str = Field(description="Platform: 'kalshi' or 'polymarket'"),
    market_id: str = Field(description="Platform-specific market identifier"),
) -> str:
    """Get resolution intelligence for a market — time urgency, mechanism, theta estimate."""
    return await _request("GET", f"/v1/markets/{platform}/{market_id}/resolution")


@mcp.tool(annotations=_READ)
async def get_execution_guidance(
    platform: str = Field(description="Platform: 'kalshi' or 'polymarket'"),
    market_id: str = Field(description="Platform-specific market identifier"),
) -> str:
    """Get execution guidance for a market — spread analysis, slippage estimate, order recommendation."""
    return await _request("GET", f"/v1/markets/{platform}/{market_id}/execution")


# ---------------------------------------------------------------------------
# Screening & discovery
# ---------------------------------------------------------------------------


@mcp.tool(annotations=_READ)
async def screen_markets(
    market_ids: list[str] | None = Field(None, description="Optional list of specific market IDs to screen"),
    platform: str = Field("", description="Filter by platform: 'kalshi', 'polymarket', or '' for all"),
    min_volume_24h: float = Field(0.0, description="Minimum 24h volume filter in USD"),
    min_score: float = Field(0.0, description="Minimum composite score filter (0.0-1.0)"),
    limit: int = Field(50, description="Maximum number of results to return"),
) -> str:
    """Batch screen markets by score, volume, or specific IDs. Returns scored markets with action recommendation."""
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


@mcp.tool(annotations=_READ_IDEM)
async def get_calibration(
    category: str = Field("", description="Filter by category (e.g. 'crypto', 'politics') or '' for all"),
    period: str = Field("all", description="Time period: '7d', '30d', '90d', or 'all'"),
    mode: str = Field("shadow", description="Trading mode: 'shadow' or 'live'"),
) -> str:
    """Get signal accuracy and calibration metrics — Brier score, hit rates, total signals."""
    params: dict = {"period": period, "mode": mode}
    if category:
        params["category"] = category
    return await _request("GET", "/v1/calibration", params=params)


# ---------------------------------------------------------------------------
# Deep research (async pattern)
# ---------------------------------------------------------------------------


@mcp.tool(annotations=_WRITE_SLOW)
async def analyze_market(
    bet_text: str = Field(description="Description of the bet or market question to analyze"),
    platform: str = Field("", description="Source platform hint: 'kalshi', 'polymarket', or ''"),
) -> str:
    """Start a deep research analysis pipeline. Returns an analysis_id — poll with check_analysis_status."""
    body: dict = {"bet_text": bet_text}
    if platform:
        body["platform"] = platform
    return await _request("POST", "/v1/insights", json=body)


@mcp.tool(annotations=_READ_IDEM)
async def check_analysis_status(
    analysis_id: str = Field(description="Analysis identifier returned by analyze_market"),
) -> str:
    """Check the current status of a running or completed analysis."""
    return await _request("GET", f"/v1/insights/{analysis_id}/status")


@mcp.tool(annotations=_READ)
async def get_analysis(
    analysis_id: str = Field(description="Analysis identifier for a completed analysis"),
) -> str:
    """Retrieve the full structured analysis result including probability, edge, scenarios, and recommendation."""
    return await _request("GET", f"/v1/insights/{analysis_id}")


@mcp.tool(annotations=_READ)
async def list_analyses(
    limit: int = Field(20, description="Maximum number of analyses to return"),
) -> str:
    """List recent analyses with summary information."""
    return await _request("GET", "/v1/analyses", params={"limit": limit})


# ---------------------------------------------------------------------------
# Strategy & portfolio
# ---------------------------------------------------------------------------


@mcp.tool(annotations=_WRITE_SLOW)
async def get_strategy(
    market_query: str = Field(description="Description of the bet or market question to analyze"),
    risk_limit: float = Field(0.0, description="Reserved for position sizing constraints"),
) -> str:
    """Run a full analysis and return a strategy signal with causal decomposition (30-90 seconds)."""
    body: dict = {"market_query": market_query}
    if risk_limit > 0:
        body["risk_limit"] = risk_limit
    return await _request("POST", "/v1/signals", json=body)


@mcp.tool(annotations=_WRITE_SLOW)
async def get_portfolio_strategy(
    market_query: str = Field(description="Description of the bet or market question to analyze"),
    portfolio: list[dict] | None = Field(None, description="Current positions: list of {ticker, side, size_usd}"),
    bankroll_usd: float = Field(10000.0, description="Total bankroll in USD for position sizing"),
    max_position_pct: float = Field(0.05, description="Maximum fraction of bankroll per position (0.01-0.50)"),
) -> str:
    """Get a portfolio-aware strategy signal with correlation analysis and hedge recommendations."""
    body: dict = {
        "market_query": market_query,
        "bankroll_usd": bankroll_usd,
        "max_position_pct": max_position_pct,
    }
    if portfolio:
        body["portfolio"] = portfolio
    return await _request("POST", "/v1/signals/portfolio", json=body)


@mcp.tool(annotations=_READ)
async def get_consensus(
    market_id: str = Field(description="Platform-specific market identifier"),
    platform: str = Field("kalshi", description="Platform: 'kalshi' or 'polymarket'"),
    period: str = Field("7d", description="Lookback period: '48h', '7d', or '30d'"),
) -> str:
    """Get consensus probability from aggregated agent trades."""
    return await _request(
        "GET",
        f"/v1/markets/{platform}/{market_id}/consensus",
        params={"period": period},
    )


# ---------------------------------------------------------------------------
# Arbitrage
# ---------------------------------------------------------------------------


@mcp.tool(annotations=_READ)
async def get_arbitrage(
    min_spread: float = Field(0.02, description="Minimum spread threshold (0.0-1.0). Default 0.02 (2%)"),
) -> str:
    """Get cross-platform arbitrage opportunities between Kalshi and Polymarket (cached)."""
    return await _request("GET", "/v1/arbitrage", params={"min_spread": min_spread})


@mcp.tool(annotations=_READ)
async def get_arbitrage_live(
    min_spread: float = Field(0.02, description="Minimum spread threshold (0.0-1.0). Default 0.02 (2%)"),
) -> str:
    """Run a fresh cross-platform arbitrage scan (10-30 seconds)."""
    return await _request("GET", "/v1/arbitrage/live", params={"min_spread": min_spread})


# ---------------------------------------------------------------------------
# Correlation
# ---------------------------------------------------------------------------


@mcp.tool(annotations=_READ)
async def get_correlation(
    market_ids: list[str] = Field(description="List of market IDs to correlate (minimum 2)"),
    platform: str = Field("kalshi", description="Platform: 'kalshi' or 'polymarket'"),
    period: str = Field("7d", description="Lookback period: '48h', '7d', or '30d'"),
) -> str:
    """Compute cross-market correlation graph for portfolio diversification analysis."""
    return await _request(
        "POST",
        "/v1/correlation",
        json={"market_ids": market_ids, "platform": platform, "period": period},
    )


# ---------------------------------------------------------------------------
# Trading
# ---------------------------------------------------------------------------


@mcp.tool(annotations=_WRITE)
async def place_shadow_trade(
    ticker: str = Field(description="Market ticker symbol (e.g. 'KXBTC-100K')"),
    side: str = Field(description="Trade direction: 'yes' or 'no'"),
    size_usd: float = Field(description="Trade size in USD"),
) -> str:
    """Place a paper (shadow) trade on a prediction market for tracking purposes."""
    return await _request(
        "POST",
        "/v1/trades/shadow",
        json={"ticker": ticker, "side": side, "size_usd": size_usd},
    )


@mcp.tool(annotations=_WRITE)
async def report_trade(
    market_id: str = Field(description="Platform-specific market identifier"),
    platform: str = Field(description="Platform: 'kalshi' or 'polymarket'"),
    side: str = Field(description="Trade direction: 'yes' or 'no'"),
    size_usd: float = Field(description="Trade size in USD"),
    price: float = Field(description="Execution price (0.0-1.0)"),
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


@mcp.tool(annotations=_READ)
async def get_portfolio(
    mode: str = Field("shadow", description="Portfolio mode: 'shadow' for paper trades, 'live' for real trades"),
) -> str:
    """Get current portfolio positions and performance summary."""
    return await _request("GET", "/v1/portfolio", params={"mode": mode})


@mcp.tool(annotations=_READ_IDEM)
async def get_performance(
    mode: str = Field("shadow", description="Portfolio mode: 'shadow' for paper trades, 'live' for real trades"),
) -> str:
    """Get aggregate trading performance statistics."""
    return await _request("GET", "/v1/performance", params={"mode": mode})


@mcp.tool(annotations=_WRITE)
async def check_resolutions() -> str:
    """Check all open trades for market resolution and update P&L."""
    return await _request("POST", "/v1/trades/resolve")


# ---------------------------------------------------------------------------
# Data refresh
# ---------------------------------------------------------------------------


@mcp.tool(annotations=_WRITE)
async def run_scraper(
    source: str = Field(description="Which scraper to run: 'kalshi', 'polymarket', or 'arbitrage'"),
) -> str:
    """Fetch fresh market data from a platform scraper."""
    return await _request("POST", "/v1/scrapers/run", json={"source": source})


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------


@mcp.tool(annotations=_WRITE)
async def create_webhook(
    url: str = Field(description="HTTPS URL to receive POST notifications"),
    events: list[str] = Field(description="Event types: 'whale_alert', 'price_shift', 'analysis_complete'"),
    secret: str = Field("", description="Optional shared secret for HMAC signature verification"),
) -> str:
    """Register a webhook for real-time event notifications."""
    body: dict = {"url": url, "events": events}
    if secret:
        body["secret"] = secret
    return await _request("POST", "/v1/webhooks", json=body)


@mcp.tool(annotations=_READ)
async def list_webhooks() -> str:
    """List registered webhooks."""
    return await _request("GET", "/v1/webhooks")


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True))
async def delete_webhook(
    webhook_id: str = Field(description="Webhook identifier returned by create_webhook"),
) -> str:
    """Remove a registered webhook."""
    return await _request("DELETE", f"/v1/webhooks/{webhook_id}")
