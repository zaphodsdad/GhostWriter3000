"""Series memory tools for continuity tracking across books."""

from __future__ import annotations

from fastmcp import FastMCP

from prose_mcp.client import safe_get, safe_post, LONG_TIMEOUT


def register_memory_tools(mcp: FastMCP) -> None:

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_get_memory(series_id: str) -> dict:
        """Get the complete memory state for a series.

        Returns all accumulated extractions and generated summaries including
        character states, world facts, timeline events, and causal chains.
        This is the full memory — use prose_get_memory_context for a compact
        version suitable for LLM prompts.

        Args:
            series_id: Series ID
        """
        return await safe_get(f"/api/series/{series_id}/memory")

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_get_memory_context(series_id: str) -> dict:
        """Get compact memory summaries ready for injection into LLM prompts.

        Returns only the generated summaries (character_states, world_state,
        timeline) in a format optimized for context assembly. Use this when
        building prompts that need series knowledge.

        Args:
            series_id: Series ID
        """
        return await safe_get(f"/api/series/{series_id}/memory/context")

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_check_staleness(series_id: str) -> dict:
        """Check which memory summaries need regeneration.

        Returns flags indicating whether character states, world state,
        or timeline summaries are out of date relative to the latest
        scene extractions.

        Args:
            series_id: Series ID
        """
        return await safe_get(f"/api/series/{series_id}/memory/staleness")

    @mcp.tool()
    async def prose_check_continuity(
        series_id: str,
        prose_text: str,
        scene_context: str | None = None,
        model: str | None = None,
    ) -> dict:
        """Check prose for continuity issues against series memory.

        Uses LLM to detect contradictions with established character states,
        world facts, and timeline. Essential before accepting new prose as
        canon in a series with existing memory.

        Args:
            series_id: Series ID
            prose_text: Prose text to check for contradictions
            scene_context: Optional scene outline for additional context
            model: Optional LLM model override
        """
        body: dict = {"prose_text": prose_text}
        if scene_context is not None:
            body["scene_context"] = scene_context
        if model is not None:
            body["model"] = model
        return await safe_post(
            f"/api/series/{series_id}/memory/check-continuity",
            json=body,
            timeout=LONG_TIMEOUT,
        )

    @mcp.tool()
    async def prose_generate_summaries(
        series_id: str,
        model: str | None = None,
    ) -> dict:
        """Generate all memory summaries from accumulated scene extractions.

        Uses LLM to synthesize character states, world state, and timeline
        from raw extraction data. Call this after marking multiple scenes
        as canon to refresh the series memory.

        Args:
            series_id: Series ID
            model: Optional LLM model override
        """
        body: dict = {}
        if model is not None:
            body["model"] = model
        return await safe_post(
            f"/api/series/{series_id}/memory/generate-summaries",
            json=body if body else None,
            timeout=LONG_TIMEOUT,
        )
