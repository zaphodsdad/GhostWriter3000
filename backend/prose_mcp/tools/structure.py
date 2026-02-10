"""Story structure tools — acts, chapters, and beats."""

from __future__ import annotations

from fastmcp import FastMCP

from prose_mcp.client import safe_get, safe_post, safe_put, safe_delete


def register_structure_tools(mcp: FastMCP) -> None:

    # ── Acts ──────────────────────────────────────────────────────────────

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_list_acts(project_id: str) -> dict:
        """List all acts in a project with scene counts and word totals.

        Args:
            project_id: Project ID
        """
        return await safe_get(f"/api/projects/{project_id}/acts/")

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_get_act(project_id: str, act_id: str) -> dict:
        """Get full details for a single act.

        Args:
            project_id: Project ID
            act_id: Act ID
        """
        return await safe_get(f"/api/projects/{project_id}/acts/{act_id}")

    @mcp.tool()
    async def prose_create_act(
        project_id: str,
        title: str,
        description: str | None = None,
        act_number: int | None = None,
        function: str | None = None,
        target_word_count: int | None = None,
    ) -> dict:
        """Create a new act in a project.

        Acts are the top-level structural division (e.g. Act I, Act II, Act III).

        Args:
            project_id: Project ID
            title: Act title (e.g. 'Act I: The Setup')
            description: Optional description of this act's role
            act_number: Position order (auto-assigned if omitted)
            function: Narrative function (e.g. 'setup', 'confrontation', 'resolution')
            target_word_count: Target word count for this act
        """
        body: dict = {"title": title}
        if description is not None:
            body["description"] = description
        if act_number is not None:
            body["act_number"] = act_number
        if function is not None:
            body["function"] = function
        if target_word_count is not None:
            body["target_word_count"] = target_word_count
        return await safe_post(f"/api/projects/{project_id}/acts/", json=body)

    @mcp.tool()
    async def prose_update_act(
        project_id: str,
        act_id: str,
        title: str | None = None,
        description: str | None = None,
        act_number: int | None = None,
        function: str | None = None,
        target_word_count: int | None = None,
    ) -> dict:
        """Update an existing act. Only provided fields are changed.

        Args:
            project_id: Project ID
            act_id: Act ID
            title: New title
            description: New description
            act_number: New position order
            function: New narrative function
            target_word_count: New target word count
        """
        body: dict = {}
        if title is not None:
            body["title"] = title
        if description is not None:
            body["description"] = description
        if act_number is not None:
            body["act_number"] = act_number
        if function is not None:
            body["function"] = function
        if target_word_count is not None:
            body["target_word_count"] = target_word_count
        return await safe_put(f"/api/projects/{project_id}/acts/{act_id}", json=body)

    @mcp.tool()
    async def prose_delete_act(project_id: str, act_id: str) -> dict:
        """Delete an act. WARNING: Chapters in this act will be unassigned,
        not deleted. Scenes within those chapters are preserved.

        Args:
            project_id: Project ID
            act_id: Act ID to delete
        """
        return await safe_delete(f"/api/projects/{project_id}/acts/{act_id}")

    # ── Chapters ──────────────────────────────────────────────────────────

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_list_chapters(project_id: str, act_id: str | None = None) -> dict:
        """List all chapters in a project, optionally filtered by act.

        Args:
            project_id: Project ID
            act_id: Optional act ID to filter by
        """
        params = {}
        if act_id is not None:
            params["act_id"] = act_id
        return await safe_get(f"/api/projects/{project_id}/chapters/", params=params or None)

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_get_chapter(project_id: str, chapter_id: str) -> dict:
        """Get full details for a single chapter.

        Args:
            project_id: Project ID
            chapter_id: Chapter ID
        """
        return await safe_get(f"/api/projects/{project_id}/chapters/{chapter_id}")

    @mcp.tool()
    async def prose_create_chapter(
        project_id: str,
        title: str,
        description: str | None = None,
        notes: str | None = None,
        chapter_number: int | None = None,
        act_id: str | None = None,
        pov_pattern: str | None = None,
        target_word_count: int | None = None,
        function: str | None = None,
    ) -> dict:
        """Create a new chapter in a project.

        Args:
            project_id: Project ID
            title: Chapter title
            description: Optional chapter description
            notes: Optional planning notes
            chapter_number: Position order (auto-assigned if omitted)
            act_id: Act this chapter belongs to
            pov_pattern: POV character or rotation pattern
            target_word_count: Target word count
            function: Narrative function of this chapter
        """
        body: dict = {"title": title}
        if description is not None:
            body["description"] = description
        if notes is not None:
            body["notes"] = notes
        if chapter_number is not None:
            body["chapter_number"] = chapter_number
        if act_id is not None:
            body["act_id"] = act_id
        if pov_pattern is not None:
            body["pov_pattern"] = pov_pattern
        if target_word_count is not None:
            body["target_word_count"] = target_word_count
        if function is not None:
            body["function"] = function
        return await safe_post(f"/api/projects/{project_id}/chapters/", json=body)

    @mcp.tool()
    async def prose_update_chapter(
        project_id: str,
        chapter_id: str,
        title: str | None = None,
        description: str | None = None,
        notes: str | None = None,
        chapter_number: int | None = None,
        act_id: str | None = None,
        pov_pattern: str | None = None,
        target_word_count: int | None = None,
        function: str | None = None,
    ) -> dict:
        """Update an existing chapter. Only provided fields are changed.

        Args:
            project_id: Project ID
            chapter_id: Chapter ID
            title: New title
            description: New description
            notes: New planning notes
            chapter_number: New position order
            act_id: Move chapter to a different act
            pov_pattern: New POV pattern
            target_word_count: New target word count
            function: New narrative function
        """
        body: dict = {}
        if title is not None:
            body["title"] = title
        if description is not None:
            body["description"] = description
        if notes is not None:
            body["notes"] = notes
        if chapter_number is not None:
            body["chapter_number"] = chapter_number
        if act_id is not None:
            body["act_id"] = act_id
        if pov_pattern is not None:
            body["pov_pattern"] = pov_pattern
        if target_word_count is not None:
            body["target_word_count"] = target_word_count
        if function is not None:
            body["function"] = function
        return await safe_put(
            f"/api/projects/{project_id}/chapters/{chapter_id}", json=body
        )

    @mcp.tool()
    async def prose_delete_chapter(project_id: str, chapter_id: str) -> dict:
        """Delete a chapter. WARNING: Will fail if the chapter still has scenes.
        Delete or move scenes first.

        Args:
            project_id: Project ID
            chapter_id: Chapter ID to delete
        """
        return await safe_delete(f"/api/projects/{project_id}/chapters/{chapter_id}")

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_get_chapter_prose(project_id: str, chapter_id: str) -> dict:
        """Get concatenated prose from all canon scenes in a chapter.

        Returns the full chapter text assembled from individual scene prose,
        in scene order. Only includes scenes marked as canon.

        Args:
            project_id: Project ID
            chapter_id: Chapter ID
        """
        return await safe_get(f"/api/projects/{project_id}/chapters/{chapter_id}/prose")

    # ── Beats ─────────────────────────────────────────────────────────────

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_list_beats(project_id: str, scene_id: str) -> dict:
        """List all beats in a scene, ordered by position.

        Beats are granular planning units within a scene — individual
        story moments, actions, or dialogue exchanges.

        Args:
            project_id: Project ID
            scene_id: Scene ID
        """
        return await safe_get(f"/api/projects/{project_id}/scenes/{scene_id}/beats")

    @mcp.tool()
    async def prose_create_beat(
        project_id: str,
        scene_id: str,
        text: str,
        notes: str | None = None,
        tags: list[str] | None = None,
        order: int | None = None,
    ) -> dict:
        """Add a beat to a scene.

        Args:
            project_id: Project ID
            scene_id: Scene ID
            text: The beat description (what happens)
            notes: Optional planning notes
            tags: Optional tags for categorization
            order: Position in the scene (auto-assigned if omitted)
        """
        body: dict = {"text": text}
        if notes is not None:
            body["notes"] = notes
        if tags is not None:
            body["tags"] = tags
        if order is not None:
            body["order"] = order
        return await safe_post(
            f"/api/projects/{project_id}/scenes/{scene_id}/beats", json=body
        )

    @mcp.tool()
    async def prose_update_beat(
        project_id: str,
        scene_id: str,
        beat_id: str,
        text: str | None = None,
        notes: str | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        """Update an existing beat. Only provided fields are changed.

        Args:
            project_id: Project ID
            scene_id: Scene ID
            beat_id: Beat ID
            text: New beat description
            notes: New notes
            tags: New tags
        """
        body: dict = {}
        if text is not None:
            body["text"] = text
        if notes is not None:
            body["notes"] = notes
        if tags is not None:
            body["tags"] = tags
        return await safe_put(
            f"/api/projects/{project_id}/scenes/{scene_id}/beats/{beat_id}", json=body
        )

    @mcp.tool()
    async def prose_delete_beat(project_id: str, scene_id: str, beat_id: str) -> dict:
        """Delete a beat from a scene.

        Args:
            project_id: Project ID
            scene_id: Scene ID
            beat_id: Beat ID to delete
        """
        return await safe_delete(
            f"/api/projects/{project_id}/scenes/{scene_id}/beats/{beat_id}"
        )

    @mcp.tool()
    async def prose_reorder_beats(
        project_id: str, scene_id: str, beat_ids: list[str]
    ) -> dict:
        """Reorder beats within a scene. Provide the complete list of beat IDs
        in the desired order.

        Args:
            project_id: Project ID
            scene_id: Scene ID
            beat_ids: Ordered list of all beat IDs in this scene
        """
        return await safe_post(
            f"/api/projects/{project_id}/scenes/{scene_id}/beats/reorder",
            json={"beat_ids": beat_ids},
        )
