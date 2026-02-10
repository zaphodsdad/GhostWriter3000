"""Generation workflow tools — start, poll, revise, accept."""

from __future__ import annotations

from fastmcp import FastMCP

from prose_mcp.client import safe_get, safe_post, LONG_TIMEOUT


def register_generation_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def prose_start_generation(
        project_id: str,
        scene_id: str,
        max_iterations: int = 5,
        generation_model: str | None = None,
        critique_model: str | None = None,
        revision_mode: str | None = None,
    ) -> dict:
        """Start AI prose generation for a scene. Returns immediately.

        Generation runs asynchronously (typically 30-60 seconds).
        Use prose_get_generation to poll for completion.

        The pipeline: generate prose -> critique -> await your decision.
        Status progresses: generating -> critiquing -> awaiting_approval.

        Args:
            project_id: Project ID
            scene_id: Scene to generate prose for
            max_iterations: Maximum revision iterations (default 5)
            generation_model: Optional model override for prose generation
            critique_model: Optional model override for critique
            revision_mode: 'full' (default) or 'polish' (light edits only)
        """
        body: dict = {"scene_id": scene_id, "max_iterations": max_iterations}
        if generation_model is not None:
            body["generation_model"] = generation_model
        if critique_model is not None:
            body["critique_model"] = critique_model
        if revision_mode is not None:
            body["revision_mode"] = revision_mode
        return await safe_post(
            f"/api/projects/{project_id}/generations/start",
            json=body,
            timeout=LONG_TIMEOUT,
        )

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_get_generation(project_id: str, generation_id: str) -> dict:
        """Get current state of a generation (use to poll for completion).

        Key response fields:
        - status: generating | critiquing | awaiting_approval | completed | rejected
        - current_prose: The generated/revised prose text
        - current_critique: AI critique of the prose
        - current_iteration: Which revision cycle we're on
        - can_revise: Whether more revisions are allowed

        Args:
            project_id: Project ID
            generation_id: Generation ID from prose_start_generation
        """
        return await safe_get(
            f"/api/projects/{project_id}/generations/{generation_id}"
        )

    @mcp.tool()
    async def prose_approve_and_revise(
        project_id: str,
        generation_id: str,
        instructions: str | None = None,
    ) -> dict:
        """Approve the critique and trigger a revision of the prose.

        Only valid when generation status is 'awaiting_approval'.
        The AI will revise the prose based on the critique plus any
        additional instructions you provide.

        Args:
            project_id: Project ID
            generation_id: Generation ID
            instructions: Optional specific guidance for the revision
                          (e.g. 'focus on dialogue' or 'add more tension')
        """
        body: dict = {}
        if instructions is not None:
            body["instructions"] = instructions
        return await safe_post(
            f"/api/projects/{project_id}/generations/{generation_id}/approve",
            json=body if body else None,
            timeout=LONG_TIMEOUT,
        )

    @mcp.tool()
    async def prose_accept_as_canon(project_id: str, generation_id: str) -> dict:
        """Accept current prose as final canon and generate a scene summary.

        Marks the scene as canon, saves the prose, and triggers automatic
        summary generation for series memory continuity. This is the final
        step in the generation pipeline.

        Args:
            project_id: Project ID
            generation_id: Generation ID
        """
        return await safe_post(
            f"/api/projects/{project_id}/generations/{generation_id}/accept",
            timeout=LONG_TIMEOUT,
        )

    @mcp.tool()
    async def prose_reject_generation(project_id: str, generation_id: str) -> dict:
        """Reject a generation and discard the prose. The scene remains unchanged.

        Use this when the generated prose isn't salvageable and you want
        to start fresh.

        Args:
            project_id: Project ID
            generation_id: Generation ID to reject
        """
        return await safe_post(
            f"/api/projects/{project_id}/generations/{generation_id}/reject",
        )

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_list_generations(project_id: str) -> dict:
        """List all generation IDs for a project.

        Args:
            project_id: Project ID
        """
        return await safe_get(f"/api/projects/{project_id}/generations/")

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_get_generation_queue(
        project_id: str, status: str | None = None
    ) -> dict:
        """List all generations with optional status filter.

        Args:
            project_id: Project ID
            status: Optional status filter (e.g. 'awaiting_approval', 'completed')
        """
        params = {}
        if status is not None:
            params["status"] = status
        return await safe_get(
            f"/api/projects/{project_id}/generations/queue",
            params=params or None,
        )
