"""Character management tools — full CRUD."""

from __future__ import annotations

from fastmcp import FastMCP

from prose_mcp.client import safe_get, safe_post, safe_put, safe_delete


def register_character_tools(mcp: FastMCP) -> None:

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_list_characters(project_id: str) -> dict:
        """List all characters in a project with metadata and full content.

        Args:
            project_id: Project ID
        """
        return await safe_get(f"/api/projects/{project_id}/characters")

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_get_character(project_id: str, character_id: str) -> dict:
        """Get full details for a single character.

        Args:
            project_id: Project ID
            character_id: Character ID
        """
        return await safe_get(f"/api/projects/{project_id}/characters/{character_id}")

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

    @mcp.tool()
    async def prose_update_character(
        project_id: str,
        character_id: str,
        metadata: dict | None = None,
        content: str | None = None,
    ) -> dict:
        """Update an existing character's metadata and/or content.

        Args:
            project_id: Project ID
            character_id: Character ID
            metadata: Updated YAML frontmatter dict
            content: Updated markdown body
        """
        body: dict = {}
        if metadata is not None:
            body["metadata"] = metadata
        if content is not None:
            body["content"] = content
        return await safe_put(
            f"/api/projects/{project_id}/characters/{character_id}", json=body
        )

    @mcp.tool()
    async def prose_delete_character(project_id: str, character_id: str) -> dict:
        """Delete a character. WARNING: This permanently removes the character file.

        Args:
            project_id: Project ID
            character_id: Character ID to delete
        """
        return await safe_delete(f"/api/projects/{project_id}/characters/{character_id}")
