"""Standalone entry point for Prose Pipeline MCP Server.

Usage:
    # stdio transport (Claude Desktop)
    python -m prose_mcp.main

    # SSE transport (LXC 304 deployment)
    TRANSPORT=sse SERVER_PORT=8092 python -m prose_mcp.main

    # Streamable HTTP transport
    TRANSPORT=streamable-http SERVER_PORT=8092 python -m prose_mcp.main
"""

from __future__ import annotations

import logging
import os


def main() -> None:
    from prose_mcp.server import mcp, register_all_tools

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    register_all_tools()

    transport = os.getenv("TRANSPORT", "stdio")
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "8001"))

    if transport == "sse":
        mcp.run(transport="sse", host=host, port=port)
    elif transport == "streamable-http":
        mcp.run(transport="streamable-http", host=host, port=port, path="/mcp")
    else:
        mcp.run()  # stdio


if __name__ == "__main__":
    main()
