"""Rekko AI MCP server — prediction market intelligence via api.rekko.ai."""

__version__ = "0.1.0"


def main() -> None:
    """Entry point for the rekko-mcp console script."""
    from rekko_mcp.server import mcp

    mcp.run()
