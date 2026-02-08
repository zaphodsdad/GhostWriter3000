"""Prose Pipeline MCP Server — FastMCP setup and tool registration."""

from __future__ import annotations

import logging

from fastmcp import FastMCP

mcp = FastMCP(
    name="Prose Pipeline MCP",
    instructions=(
        "Provides tools to manage AI-powered prose generation projects. "
        "Supports project and series management, character and world building, "
        "scene generation with critique-revision loops, and series memory "
        "for maintaining continuity across books. "
        "Generation is asynchronous — use prose_start_generation to kick off, "
        "then prose_get_generation to poll for completion."
    ),
    version="0.1.0",
)

logger = logging.getLogger("prose_mcp")

_registered = False


def register_all_tools() -> None:
    """Register all tool modules with the MCP server (idempotent)."""
    global _registered
    if _registered:
        return
    _registered = True

    from prose_mcp.tools.projects import register_project_tools
    from prose_mcp.tools.content import register_content_tools
    from prose_mcp.tools.generation import register_generation_tools
    from prose_mcp.tools.memory import register_memory_tools
    from prose_mcp.tools.extraction import register_extraction_tools

    register_project_tools(mcp)
    logger.info("Project tools registered")

    register_content_tools(mcp)
    logger.info("Content tools registered")

    register_generation_tools(mcp)
    logger.info("Generation tools registered")

    register_memory_tools(mcp)
    logger.info("Memory tools registered")

    register_extraction_tools(mcp)
    logger.info("Extraction tools registered")

    logger.info("All prose-pipeline MCP tools registered")
