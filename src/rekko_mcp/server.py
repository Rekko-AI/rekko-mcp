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


# ---------------------------------------------------------------------------
# Market intelligence
# ---------------------------------------------------------------------------


@mcp.tool()
async def list_markets(source: str = "", limit: int = 30) -> str:
    """List current prediction markets from Kalshi and Polymarket.

    Args:
        source: Filter by platform: "kalshi", "polymarket", or "" for all.
        limit: Maximum number of markets to return (1-100).
    """
    params: dict = {"limit": limit}
    if source:
        params["source"] = source
    return await _request("GET", "/v1/markets", params=params)


@mcp.tool()
async def get_market(market_id: str, source: str = "") -> str:
    """Get detailed information about a specific prediction market.

    Args:
        market_id: Platform-specific market identifier (e.g. Kalshi ticker or Polymarket slug).
        source: Platform hint: "kalshi", "polymarket", or "" to search both.
    """
    if source:
        return await _request("GET", f"/v1/markets/{source}/{market_id}")
    return await _request("GET", "/v1/markets", params={"query": market_id, "limit": 1})


@mcp.tool()
async def search_markets(query: str, limit: int = 20) -> str:
    """Search prediction markets by keyword in market title.

    Args:
        query: Search query string to match against market titles.
        limit: Maximum number of results to return.
    """
    return await _request("GET", "/v1/markets", params={"query": query, "limit": limit})


@mcp.tool()
async def get_market_history(
    platform: str, market_id: str, period: str = "7d", max_points: int = 48
) -> str:
    """Get price history for a prediction market over a configurable period.

    Args:
        platform: Platform: "kalshi" or "polymarket".
        market_id: Platform-specific market identifier.
        period: History window: "48h", "7d", or "30d".
        max_points: Maximum data points to return.
    """
    return await _request(
        "GET",
        f"/v1/markets/{platform}/{market_id}/history",
        params={"period": period, "max_points": max_points},
    )


@mcp.tool()
async def get_resolution(platform: str, market_id: str) -> str:
    """Get resolution intelligence for a market — time urgency, mechanism, theta estimate.

    Args:
        platform: Platform: "kalshi" or "polymarket".
        market_id: Platform-specific market identifier.
    """
    return await _request("GET", f"/v1/markets/{platform}/{market_id}/resolution")


@mcp.tool()
async def get_execution_guidance(platform: str, market_id: str) -> str:
    """Get execution guidance for a market — spread analysis, slippage estimate, order recommendation.

    Args:
        platform: Platform: "kalshi" or "polymarket".
        market_id: Platform-specific market identifier.
    """
    return await _request("GET", f"/v1/markets/{platform}/{market_id}/execution")


# ---------------------------------------------------------------------------
# Screening & discovery
# ---------------------------------------------------------------------------


@mcp.tool()
async def screen_markets(
    market_ids: list[str] | None = None,
    platform: str = "",
    min_volume_24h: float = 0.0,
    min_score: float = 0.0,
    limit: int = 50,
) -> str:
    """Batch screen markets by score, volume, or specific IDs.

    Returns scored markets with an action recommendation: "analyze", "watch", or "skip".

    Args:
        market_ids: Optional list of specific market IDs to screen.
        platform: Filter by platform: "kalshi", "polymarket", or "" for all.
        min_volume_24h: Minimum 24h volume filter.
        min_score: Minimum composite score filter.
        limit: Maximum number of results to return.
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


@mcp.tool()
async def get_calibration(
    category: str = "", period: str = "all", mode: str = "shadow"
) -> str:
    """Get signal accuracy and calibration metrics — Brier score, hit rates, total signals.

    Args:
        category: Filter by category (e.g. "crypto", "politics") or "" for all.
        period: Time period: "7d", "30d", "90d", or "all".
        mode: Trading mode: "shadow" or "live".
    """
    params: dict = {"period": period, "mode": mode}
    if category:
        params["category"] = category
    return await _request("GET", "/v1/calibration", params=params)


# ---------------------------------------------------------------------------
# Deep research (async pattern)
# ---------------------------------------------------------------------------


@mcp.tool()
async def analyze_market(bet_text: str, platform: str = "") -> str:
    """Start a deep research analysis pipeline for a prediction market bet.

    Returns immediately with an analysis_id. Poll with check_analysis_status
    every 5 seconds until complete, then retrieve results with get_analysis.

    Args:
        bet_text: Description of the bet or market question to analyze.
        platform: Source platform hint: "kalshi", "polymarket", or "".
    """
    body: dict = {"bet_text": bet_text}
    if platform:
        body["platform"] = platform
    return await _request("POST", "/v1/insights", json=body)


@mcp.tool()
async def check_analysis_status(analysis_id: str) -> str:
    """Check the current status of a running or completed analysis.

    Args:
        analysis_id: Analysis identifier returned by analyze_market.
    """
    return await _request("GET", f"/v1/insights/{analysis_id}/status")


@mcp.tool()
async def get_analysis(analysis_id: str) -> str:
    """Retrieve the full structured analysis result for a completed analysis.

    Includes probability estimate, edge assessment, scenarios, key factors,
    risks, and trading recommendation.

    Args:
        analysis_id: Analysis identifier for a completed analysis.
    """
    return await _request("GET", f"/v1/insights/{analysis_id}")


@mcp.tool()
async def list_analyses(limit: int = 20) -> str:
    """List recent analyses with summary information.

    Args:
        limit: Maximum number of analyses to return.
    """
    return await _request("GET", "/v1/analyses", params={"limit": limit})


# ---------------------------------------------------------------------------
# Strategy & portfolio
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_strategy(market_query: str, risk_limit: float = 0.0) -> str:
    """Run a full analysis and return a strategy signal with causal decomposition.

    This is a blocking call that takes 30-90 seconds. For async control, use
    analyze_market + check_analysis_status + get_analysis instead.

    Args:
        market_query: Description of the bet or market question to analyze.
        risk_limit: Reserved for position sizing constraints.
    """
    body: dict = {"market_query": market_query}
    if risk_limit > 0:
        body["risk_limit"] = risk_limit
    return await _request("POST", "/v1/signals", json=body)


@mcp.tool()
async def get_portfolio_strategy(
    market_query: str,
    portfolio: list[dict] | None = None,
    bankroll_usd: float = 10000.0,
    max_position_pct: float = 0.05,
) -> str:
    """Get a portfolio-aware strategy signal with position context and correlation analysis.

    Args:
        market_query: Description of the bet or market question to analyze.
        portfolio: Optional list of current positions (dicts with ticker, side, size_usd).
        bankroll_usd: Total bankroll in USD for position sizing.
        max_position_pct: Maximum fraction of bankroll per position.
    """
    body: dict = {
        "market_query": market_query,
        "bankroll_usd": bankroll_usd,
        "max_position_pct": max_position_pct,
    }
    if portfolio:
        body["portfolio"] = portfolio
    return await _request("POST", "/v1/signals/portfolio", json=body)


@mcp.tool()
async def get_consensus(
    market_id: str, platform: str = "kalshi", period: str = "7d"
) -> str:
    """Get consensus probability from aggregated agent trades.

    Args:
        market_id: Platform-specific market identifier.
        platform: Platform: "kalshi" or "polymarket".
        period: Lookback period: "48h", "7d", or "30d".
    """
    return await _request(
        "GET",
        f"/v1/markets/{platform}/{market_id}/consensus",
        params={"period": period},
    )


# ---------------------------------------------------------------------------
# Arbitrage
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_arbitrage(min_spread: float = 0.02) -> str:
    """Get cross-platform arbitrage opportunities between Kalshi and Polymarket (cached).

    Args:
        min_spread: Minimum spread threshold (0.0-1.0). Default 0.02 (2%).
    """
    return await _request("GET", "/v1/arbitrage", params={"min_spread": min_spread})


@mcp.tool()
async def get_arbitrage_live(min_spread: float = 0.02) -> str:
    """Run a fresh cross-platform arbitrage scan (may take 10-30 seconds).

    Args:
        min_spread: Minimum spread threshold (0.0-1.0). Default 0.02 (2%).
    """
    return await _request("GET", "/v1/arbitrage/live", params={"min_spread": min_spread})


# ---------------------------------------------------------------------------
# Correlation
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_correlation(
    market_ids: list[str], platform: str = "kalshi", period: str = "7d"
) -> str:
    """Compute cross-market correlation graph for portfolio diversification analysis.

    Args:
        market_ids: List of market IDs to correlate (minimum 2).
        platform: Platform: "kalshi" or "polymarket".
        period: Lookback period: "48h", "7d", or "30d".
    """
    return await _request(
        "POST",
        "/v1/correlation",
        json={"market_ids": market_ids, "platform": platform, "period": period},
    )


# ---------------------------------------------------------------------------
# Trading
# ---------------------------------------------------------------------------


@mcp.tool()
async def place_shadow_trade(ticker: str, side: str, size_usd: float) -> str:
    """Place a paper (shadow) trade on a prediction market for tracking purposes.

    Args:
        ticker: Market ticker symbol (e.g. "KXBTC-100K").
        side: Trade direction: "yes" or "no".
        size_usd: Trade size in USD.
    """
    return await _request(
        "POST",
        "/v1/trades/shadow",
        json={"ticker": ticker, "side": side, "size_usd": size_usd},
    )


@mcp.tool()
async def report_trade(
    market_id: str, platform: str, side: str, size_usd: float, price: float
) -> str:
    """Report a trade for consensus probability aggregation.

    Args:
        market_id: Platform-specific market identifier.
        platform: Platform: "kalshi" or "polymarket".
        side: Trade direction: "yes" or "no".
        size_usd: Trade size in USD.
        price: Execution price (0.0-1.0).
    """
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


@mcp.tool()
async def get_portfolio(mode: str = "shadow") -> str:
    """Get current portfolio positions and performance summary.

    Args:
        mode: Portfolio mode: "shadow" for paper trades, "live" for real trades.
    """
    return await _request("GET", "/v1/portfolio", params={"mode": mode})


@mcp.tool()
async def get_performance(mode: str = "shadow") -> str:
    """Get aggregate trading performance statistics.

    Args:
        mode: Portfolio mode: "shadow" for paper trades, "live" for real trades.
    """
    return await _request("GET", "/v1/performance", params={"mode": mode})


@mcp.tool()
async def check_resolutions() -> str:
    """Check all open trades for market resolution and update P&L."""
    return await _request("POST", "/v1/trades/resolve")


# ---------------------------------------------------------------------------
# Data refresh
# ---------------------------------------------------------------------------


@mcp.tool()
async def run_scraper(source: str) -> str:
    """Fetch fresh market data from a platform scraper.

    Args:
        source: Which scraper to run: "kalshi", "polymarket", or "arbitrage".
    """
    return await _request("POST", "/v1/scrapers/run", json={"source": source})


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------


@mcp.tool()
async def create_webhook(url: str, events: list[str], secret: str = "") -> str:
    """Register a webhook for real-time event notifications.

    Args:
        url: HTTPS URL to receive POST notifications.
        events: Event types: "whale_alert", "price_shift", "analysis_complete".
        secret: Optional shared secret for HMAC signature verification.
    """
    body: dict = {"url": url, "events": events}
    if secret:
        body["secret"] = secret
    return await _request("POST", "/v1/webhooks", json=body)


@mcp.tool()
async def list_webhooks() -> str:
    """List registered webhooks."""
    return await _request("GET", "/v1/webhooks")


@mcp.tool()
async def delete_webhook(webhook_id: str) -> str:
    """Remove a registered webhook.

    Args:
        webhook_id: Webhook identifier returned by create_webhook.
    """
    return await _request("DELETE", f"/v1/webhooks/{webhook_id}")
