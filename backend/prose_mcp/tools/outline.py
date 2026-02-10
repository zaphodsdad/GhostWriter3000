"""Outline generation and management tools."""

from __future__ import annotations

from fastmcp import FastMCP

from prose_mcp.client import safe_get, safe_post, LONG_TIMEOUT

# Outline generation can take a while — multiple LLM calls for acts/chapters/scenes/beats
OUTLINE_TIMEOUT = LONG_TIMEOUT


def register_outline_tools(mcp: FastMCP) -> None:

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_estimate_outline_cost(scope: str = "standard") -> dict:
        """Get a cost estimate for auto-generating a story outline.

        Returns estimated token counts and dollar costs before committing
        to generation. Use this to show costs to the user before they confirm.

        Args:
            scope: Generation scope — 'quick' (9 scenes, ~27 beats),
                   'standard' (15 scenes, ~60 beats), or
                   'detailed' (24 scenes, ~120 beats)
        """
        return await safe_get(
            "/api/projects/auto-generate/estimate",
            params={"scope": scope},
        )

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_get_outline_scopes() -> dict:
        """Get available outline generation scopes with descriptions and cost estimates.

        Returns a list of scopes (quick, standard, detailed) with their
        configurations, estimated token counts, and costs.
        """
        return await safe_get("/api/projects/auto-generate/scopes")

    @mcp.tool()
    async def prose_generate_outline(
        project_id: str,
        seed: str,
        scope: str = "standard",
        mode: str = "full",
        genre: str | None = None,
        character_names: list[str] | None = None,
        budget_limit: float | None = None,
        level: str | None = None,
        context: dict | None = None,
    ) -> dict:
        """Auto-generate a story outline from a seed premise using LLM.

        Two modes available:
        - 'full': Generate complete outline in one operation (acts → chapters → scenes → beats).
          Best for CYOABot and automated workflows.
        - 'staged': Generate one level at a time. Call repeatedly with level='acts',
          then 'chapters', 'scenes', 'beats'. Allows review between levels.
          Best for the prose-pipeline UI where writers want to review each level.

        The generated outline is NOT automatically applied to the project. Call
        prose_apply_outline to create the actual acts/chapters/scenes/beats.

        Args:
            project_id: Project ID (must exist)
            seed: Story premise or concept (e.g. 'Humanity dying off while insects gain sentience')
            scope: 'quick' (9 scenes), 'standard' (15 scenes), or 'detailed' (24 scenes)
            mode: 'full' (one-shot) or 'staged' (level by level)
            genre: Optional genre (e.g. 'sci-fi', 'literary fiction', 'horror')
            character_names: Optional list of character names to include
            budget_limit: Max spend in dollars (generation stops if reached)
            level: Required for staged mode — 'acts', 'chapters', 'scenes', or 'beats'
            context: Required for staged mode — previously approved structure from earlier levels
        """
        body: dict = {"seed": seed, "scope": scope, "mode": mode}
        if genre is not None:
            body["genre"] = genre
        if character_names is not None:
            body["character_names"] = character_names
        if budget_limit is not None:
            body["budget_limit"] = budget_limit
        if level is not None:
            body["level"] = level
        if context is not None:
            body["context"] = context
        return await safe_post(
            f"/api/projects/{project_id}/auto-generate",
            json=body,
            timeout=OUTLINE_TIMEOUT,
        )

    @mcp.tool()
    async def prose_apply_outline(
        project_id: str,
        outline: dict,
        clear_existing: bool = False,
    ) -> dict:
        """Apply a generated outline to a project, creating acts/chapters/scenes/beats.

        Takes the output from prose_generate_outline and creates the actual
        project structure. Creates a backup snapshot before making changes.

        Args:
            project_id: Project ID
            outline: The generated outline structure (from prose_generate_outline)
            clear_existing: If true, removes existing acts/chapters/scenes first.
                           WARNING: This is destructive. A backup is created regardless.
        """
        url = f"/api/projects/{project_id}/auto-generate/apply"
        if clear_existing:
            url += "?clear_existing=true"
        return await safe_post(url, json=outline)

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_get_outline(project_id: str) -> dict:
        """Get the full outline structure for a project — acts, chapters, scenes, and beats.

        Returns a hierarchical view of the project structure with status info:
        total scenes, how many have prose, how many are canon. Useful for
        understanding what's been written and what remains.

        Args:
            project_id: Project ID
        """
        # Fetch acts, chapters, and scenes in sequence
        # (acts/chapters are fast file reads, not LLM calls)
        acts = await safe_get(f"/api/projects/{project_id}/acts/")
        chapters = await safe_get(f"/api/projects/{project_id}/chapters/")
        scenes = await safe_get(f"/api/projects/{project_id}/scenes/")

        # Build summary stats
        scene_list = scenes if isinstance(scenes, list) else []
        total_scenes = len(scene_list)
        scenes_with_prose = sum(
            1 for s in scene_list
            if s.get("prose") or s.get("original_prose")
        )
        scenes_canon = sum(1 for s in scene_list if s.get("is_canon"))

        return {
            "acts": acts if isinstance(acts, list) else [],
            "chapters": chapters if isinstance(chapters, list) else [],
            "scenes": scene_list,
            "total_scenes": total_scenes,
            "scenes_with_prose": scenes_with_prose,
            "scenes_canon": scenes_canon,
            "scenes_remaining": total_scenes - scenes_with_prose,
        }

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_get_next_scene(project_id: str) -> dict:
        """Get the next ungenerated scene in outline order.

        Returns the first scene (by chapter number, then scene number) that
        has no prose and is not canon. Includes beats and all metadata needed
        to start generation.

        Returns {"none": true} when all scenes have been generated.

        Args:
            project_id: Project ID
        """
        return await safe_get(
            f"/api/projects/{project_id}/scenes/next-ungenerated"
        )
