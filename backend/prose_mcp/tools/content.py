"""Character, world context, and scene management tools."""

from __future__ import annotations

from fastmcp import FastMCP

from prose_mcp.client import safe_get, safe_post


def register_content_tools(mcp: FastMCP) -> None:

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_get_characters(project_id: str) -> dict:
        """List all characters in a project with metadata and full content.

        Args:
            project_id: Project ID
        """
        return await safe_get(f"/api/projects/{project_id}/characters")

    @mcp.tool()
    async def prose_create_character(
        project_id: str,
        filename: str,
        metadata: dict,
        content: str,
    ) -> dict:
        """Create a new character in a project.

        Characters are stored as markdown with YAML frontmatter.

        Args:
            project_id: Project ID
            filename: Character filename (e.g. 'jane-doe.md')
            metadata: YAML frontmatter dict — name (required), plus optional
                      age, role, personality_traits, skills, etc.
            content: Markdown body with background, voice, mannerisms
        """
        return await safe_post(
            f"/api/projects/{project_id}/characters",
            json={"filename": filename, "metadata": metadata, "content": content},
        )

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_get_world_contexts(project_id: str) -> dict:
        """List all world building context documents in a project.

        Args:
            project_id: Project ID
        """
        return await safe_get(f"/api/projects/{project_id}/world")

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

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_get_scenes(project_id: str, chapter_id: str | None = None) -> dict:
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
