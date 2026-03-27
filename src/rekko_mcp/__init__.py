"""Rekko AI MCP server — prediction market intelligence via api.rekko.ai."""

__version__ = "0.5.2"


def main() -> None:
    """Entry point for the rekko-mcp console script.

    Supports two transports:
      - stdio (default): local execution via `uvx rekko-mcp`
      - streamable-http: hosted mode via `rekko-mcp --http`

    Set PORT env var to control the HTTP port (default 8000).
    """
    import os
    import sys

    from rekko_mcp.server import mcp

    if "--http" in sys.argv or os.environ.get("MCP_TRANSPORT") == "http":
        port = int(os.environ.get("PORT", "8000"))
        mcp.run(
            transport="streamable-http",
            host="0.0.0.0",
            port=port,
        )
    else:
        mcp.run()
