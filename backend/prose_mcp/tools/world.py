"""World context management tools — full CRUD."""

from __future__ import annotations

from fastmcp import FastMCP

from prose_mcp.client import safe_get, safe_post, safe_put, safe_delete


def register_world_tools(mcp: FastMCP) -> None:

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_list_world_contexts(project_id: str) -> dict:
        """List all world building context documents in a project.

        Args:
            project_id: Project ID
        """
        return await safe_get(f"/api/projects/{project_id}/world")

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_get_world_context(project_id: str, world_id: str) -> dict:
        """Get full details for a single world context document.

        Args:
            project_id: Project ID
            world_id: World context ID
        """
        return await safe_get(f"/api/projects/{project_id}/world/{world_id}")

    @mcp.tool()
    async def prose_create_world_context(
        project_id: str,
        filename: str,
        metadata: dict,
        content: str,
    ) -> dict:
        """Create a new world building document in a project.

        World contexts are stored as markdown with YAML frontmatter.

        Args:
            project_id: Project ID
            filename: Filename (e.g. 'magic-system.md')
            metadata: YAML frontmatter dict — name (required), plus optional
                      era, magic_system, technology_level, etc.
            content: Markdown body with history, geography, factions, etc.
        """
        return await safe_post(
            f"/api/projects/{project_id}/world",
            json={"filename": filename, "metadata": metadata, "content": content},
        )

    @mcp.tool()
    async def prose_update_world_context(
        project_id: str,
        world_id: str,
        metadata: dict | None = None,
        content: str | None = None,
    ) -> dict:
        """Update an existing world context document.

        Args:
            project_id: Project ID
            world_id: World context ID
            metadata: Updated YAML frontmatter dict
            content: Updated markdown body
        """
        body: dict = {}
        if metadata is not None:
            body["metadata"] = metadata
        if content is not None:
            body["content"] = content
        return await safe_put(
            f"/api/projects/{project_id}/world/{world_id}", json=body
        )

    @mcp.tool()
    async def prose_delete_world_context(project_id: str, world_id: str) -> dict:
        """Delete a world context document. WARNING: This permanently removes the file.

        Args:
            project_id: Project ID
            world_id: World context ID to delete
        """
        return await safe_delete(f"/api/projects/{project_id}/world/{world_id}")
