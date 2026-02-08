"""Scene management tools — full CRUD, prose operations, and evaluation."""

from __future__ import annotations

from fastmcp import FastMCP

from prose_mcp.client import safe_get, safe_post, safe_put, safe_delete, LONG_TIMEOUT


def register_scene_tools(mcp: FastMCP) -> None:

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_list_scenes(project_id: str, chapter_id: str | None = None) -> dict:
        """List all scenes in a project, optionally filtered by chapter.

        Returns scene IDs, titles, outlines, canon status, and word counts.

        Args:
            project_id: Project ID
            chapter_id: Optional chapter ID to filter by
        """
        params = {}
        if chapter_id is not None:
            params["chapter_id"] = chapter_id
        return await safe_get(f"/api/projects/{project_id}/scenes", params=params or None)

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_get_scene(project_id: str, scene_id: str) -> dict:
        """Get full details for a single scene including outline, metadata, and prose status.

        Args:
            project_id: Project ID
            scene_id: Scene ID
        """
        return await safe_get(f"/api/projects/{project_id}/scenes/{scene_id}")

    @mcp.tool()
    async def prose_create_scene(
        project_id: str,
        title: str,
        outline: str,
        chapter_id: str,
        scene_number: int | None = None,
        character_ids: list[str] | None = None,
        world_context_ids: list[str] | None = None,
        previous_scene_ids: list[str] | None = None,
        tags: list[str] | None = None,
        additional_notes: str | None = None,
        tone: str | None = None,
        pov: str | None = None,
        target_length: str | None = None,
        setting: str | None = None,
        generation_notes: str | None = None,
    ) -> dict:
        """Create a new scene in a project.

        Args:
            project_id: Project ID
            title: Scene title
            outline: Scene outline (minimum 10 characters)
            chapter_id: Chapter this scene belongs to
            scene_number: Position in chapter (auto-assigned if omitted)
            character_ids: Characters appearing in this scene
            world_context_ids: World context documents relevant to this scene
            previous_scene_ids: Scenes that precede this one (for continuity)
            tags: Tags for categorization
            additional_notes: Extra notes for generation
            tone: Desired tone (e.g. 'tense', 'lighthearted')
            pov: Point of view character or style
            target_length: Target word count descriptor
            setting: Scene setting/location
            generation_notes: Specific instructions for AI generation
        """
        body: dict = {"title": title, "outline": outline, "chapter_id": chapter_id}
        if scene_number is not None:
            body["scene_number"] = scene_number
        if character_ids is not None:
            body["character_ids"] = character_ids
        if world_context_ids is not None:
            body["world_context_ids"] = world_context_ids
        if previous_scene_ids is not None:
            body["previous_scene_ids"] = previous_scene_ids
        if tags is not None:
            body["tags"] = tags
        if additional_notes is not None:
            body["additional_notes"] = additional_notes
        if tone is not None:
            body["tone"] = tone
        if pov is not None:
            body["pov"] = pov
        if target_length is not None:
            body["target_length"] = target_length
        if setting is not None:
            body["setting"] = setting
        if generation_notes is not None:
            body["generation_notes"] = generation_notes
        return await safe_post(f"/api/projects/{project_id}/scenes", json=body)

    @mcp.tool()
    async def prose_update_scene(
        project_id: str,
        scene_id: str,
        title: str | None = None,
        outline: str | None = None,
        chapter_id: str | None = None,
        scene_number: int | None = None,
        character_ids: list[str] | None = None,
        world_context_ids: list[str] | None = None,
        tags: list[str] | None = None,
        additional_notes: str | None = None,
        tone: str | None = None,
        pov: str | None = None,
        target_length: str | None = None,
        setting: str | None = None,
        generation_notes: str | None = None,
    ) -> dict:
        """Update an existing scene's metadata. Only provided fields are changed.

        Args:
            project_id: Project ID
            scene_id: Scene ID
            title: New title
            outline: New outline
            chapter_id: Move scene to a different chapter
            scene_number: New position in chapter
            character_ids: Updated character list
            world_context_ids: Updated world context list
            tags: Updated tags
            additional_notes: Updated notes
            tone: Updated tone
            pov: Updated POV
            target_length: Updated target length
            setting: Updated setting
            generation_notes: Updated generation notes
        """
        body: dict = {}
        if title is not None:
            body["title"] = title
        if outline is not None:
            body["outline"] = outline
        if chapter_id is not None:
            body["chapter_id"] = chapter_id
        if scene_number is not None:
            body["scene_number"] = scene_number
        if character_ids is not None:
            body["character_ids"] = character_ids
        if world_context_ids is not None:
            body["world_context_ids"] = world_context_ids
        if tags is not None:
            body["tags"] = tags
        if additional_notes is not None:
            body["additional_notes"] = additional_notes
        if tone is not None:
            body["tone"] = tone
        if pov is not None:
            body["pov"] = pov
        if target_length is not None:
            body["target_length"] = target_length
        if setting is not None:
            body["setting"] = setting
        if generation_notes is not None:
            body["generation_notes"] = generation_notes
        return await safe_put(f"/api/projects/{project_id}/scenes/{scene_id}", json=body)

    @mcp.tool()
    async def prose_delete_scene(project_id: str, scene_id: str) -> dict:
        """Delete a scene. WARNING: This permanently removes the scene. A backup
        is created automatically before deletion.

        Args:
            project_id: Project ID
            scene_id: Scene ID to delete
        """
        return await safe_delete(f"/api/projects/{project_id}/scenes/{scene_id}")

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_get_scene_prose(project_id: str, scene_id: str) -> dict:
        """Get the prose text for a scene along with metadata.

        Args:
            project_id: Project ID
            scene_id: Scene ID
        """
        return await safe_get(f"/api/projects/{project_id}/scenes/{scene_id}/prose")

    @mcp.tool()
    async def prose_save_scene_prose(project_id: str, scene_id: str, prose: str) -> dict:
        """Save prose text to a scene. Creates a backup of the previous version.

        Args:
            project_id: Project ID
            scene_id: Scene ID
            prose: The prose text to save
        """
        return await safe_post(
            f"/api/projects/{project_id}/scenes/{scene_id}/save-prose",
            json={"prose": prose},
        )

    @mcp.tool()
    async def prose_evaluate_scene(
        project_id: str,
        scene_id: str,
        model: str | None = None,
        revision_mode: str | None = None,
    ) -> dict:
        """Get an AI critique of a scene's prose WITHOUT entering the revision loop.

        Use this for a standalone evaluation. For generation with revision,
        use prose_start_generation instead.

        Args:
            project_id: Project ID
            scene_id: Scene ID
            model: Optional LLM model override
            revision_mode: 'full' (detailed critique) or 'polish' (light edits only)
        """
        body: dict = {}
        if model is not None:
            body["model"] = model
        if revision_mode is not None:
            body["revision_mode"] = revision_mode
        return await safe_post(
            f"/api/projects/{project_id}/scenes/{scene_id}/evaluate",
            json=body if body else None,
            timeout=LONG_TIMEOUT,
        )

    @mcp.tool()
    async def prose_enable_edit_mode(project_id: str, scene_id: str) -> dict:
        """Enable edit mode for a scene — imports existing prose for AI revision.

        Use this when you want to revise existing prose through the generation
        pipeline rather than generating from scratch.

        Args:
            project_id: Project ID
            scene_id: Scene ID (must have existing prose)
        """
        return await safe_post(f"/api/projects/{project_id}/scenes/{scene_id}/edit-mode")

    @mcp.tool()
    async def prose_disable_edit_mode(project_id: str, scene_id: str) -> dict:
        """Exit edit mode for a scene without applying changes.

        Args:
            project_id: Project ID
            scene_id: Scene ID
        """
        return await safe_delete(f"/api/projects/{project_id}/scenes/{scene_id}/edit-mode")

    @mcp.tool()
    async def prose_revise_scene_selection(
        project_id: str,
        scene_id: str,
        selection_start: int,
        selection_end: int,
        selection_text: str,
        instructions: str | None = None,
        model: str | None = None,
        quick_action: str | None = None,
    ) -> dict:
        """Revise a selected portion of scene prose using AI. Returns a preview
        of the revised text without saving it.

        Args:
            project_id: Project ID
            scene_id: Scene ID
            selection_start: Character index where selection starts
            selection_end: Character index where selection ends
            selection_text: The selected text to revise
            instructions: Optional specific revision instructions
            model: Optional LLM model override
            quick_action: Preset action — 'shorten', 'lengthen', 'rephrase',
                          'more_vivid', 'more_tension', or 'simplify'
        """
        body: dict = {
            "selection_start": selection_start,
            "selection_end": selection_end,
            "selection_text": selection_text,
        }
        if instructions is not None:
            body["instructions"] = instructions
        if model is not None:
            body["model"] = model
        if quick_action is not None:
            body["quick_action"] = quick_action
        return await safe_post(
            f"/api/projects/{project_id}/scenes/{scene_id}/revise-selection",
            json=body,
            timeout=LONG_TIMEOUT,
        )
