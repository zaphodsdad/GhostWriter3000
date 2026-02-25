"""GhostWriter 3000 MCP Server — FastMCP setup and tool registration."""

from __future__ import annotations

import logging

from fastmcp import FastMCP

mcp = FastMCP(
    name="GhostWriter 3000 MCP",
    instructions=(
        "Provides tools to manage AI-powered prose generation projects. "
        "Supports full project lifecycle: story structure (acts, chapters, beats), "
        "content management (characters, world, scenes), prose generation with "
        "critique-revision loops, style guides, and series memory for maintaining "
        "continuity across books. "
        "Generation is asynchronous — use prose_start_generation to kick off, "
        "then prose_get_generation to poll for completion."
    ),
    version="0.2.0",
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
    from prose_mcp.tools.structure import register_structure_tools
    from prose_mcp.tools.scenes import register_scene_tools
    from prose_mcp.tools.characters import register_character_tools
    from prose_mcp.tools.world import register_world_tools
    from prose_mcp.tools.generation import register_generation_tools
    from prose_mcp.tools.memory import register_memory_tools
    from prose_mcp.tools.extraction import register_extraction_tools
    from prose_mcp.tools.style import register_style_tools
    from prose_mcp.tools.outline import register_outline_tools

    register_project_tools(mcp)
    logger.info("Project tools registered")

    register_structure_tools(mcp)
    logger.info("Structure tools registered")

    register_scene_tools(mcp)
    logger.info("Scene tools registered")

    register_character_tools(mcp)
    logger.info("Character tools registered")

    register_world_tools(mcp)
    logger.info("World tools registered")

    register_generation_tools(mcp)
    logger.info("Generation tools registered")

    register_memory_tools(mcp)
    logger.info("Memory tools registered")

    register_extraction_tools(mcp)
    logger.info("Extraction tools registered")

    register_style_tools(mcp)
    logger.info("Style tools registered")

    register_outline_tools(mcp)
    logger.info("Outline tools registered")

    logger.info("All GhostWriter 3000 MCP tools registered")
