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
    async def prose_extract_scene_memory(
        series_id: str,
        book_id: str,
        scene_id: str,
        prose: str,
        scene_title: str | None = None,
        chapter_title: str | None = None,
        book_number: int | None = None,
        chapter_number: int | None = None,
        scene_number: int | None = None,
        character_names: list[str] | None = None,
        model: str | None = None,
    ) -> dict:
        """Extract memory facts from a scene using LLM analysis.

        Runs AI extraction on the scene prose to identify character state
        changes, world facts, and plot events. Results are saved to the
        series memory layer automatically. Call this after accepting a
        new scene as canon.

        Args:
            series_id: Series ID the scene belongs to
            book_id: Book/project ID containing the scene
            scene_id: Scene ID
            prose: Full prose text of the scene
            scene_title: Scene title for context
            chapter_title: Chapter title for context
            book_number: Book number in the series
            chapter_number: Chapter number within the book
            scene_number: Scene number within the chapter
            character_names: Known character names for better extraction
            model: Optional LLM model override
        """
        body: dict = {
            "book_id": book_id,
            "scene_id": scene_id,
            "prose": prose,
        }
        if scene_title is not None:
            body["scene_title"] = scene_title
        if chapter_title is not None:
            body["chapter_title"] = chapter_title
        if book_number is not None:
            body["book_number"] = book_number
        if chapter_number is not None:
            body["chapter_number"] = chapter_number
        if scene_number is not None:
            body["scene_number"] = scene_number
        if character_names is not None:
            body["character_names"] = character_names
        if model is not None:
            body["model"] = model
        return await safe_post(
            f"/api/series/{series_id}/memory/extract-from-scene",
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
