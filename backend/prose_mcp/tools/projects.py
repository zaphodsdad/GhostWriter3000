"""Project and series management tools."""

from __future__ import annotations

from fastmcp import FastMCP

from prose_mcp.client import safe_get, safe_post


def register_project_tools(mcp: FastMCP) -> None:

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_list_projects() -> dict:
        """List all prose generation projects with summary stats.

        Returns project IDs, titles, word counts, scene counts,
        and series membership for every project.
        """
        return await safe_get("/api/projects")

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_get_project(project_id: str) -> dict:
        """Get full details for a specific project.

        Args:
            project_id: Project ID (URL slug, e.g. 'my-novel')
        """
        return await safe_get(f"/api/projects/{project_id}")

    @mcp.tool()
    async def prose_create_project(
        title: str,
        description: str | None = None,
        genre: str | None = None,
        series_id: str | None = None,
        book_number: int | None = None,
    ) -> dict:
        """Create a new prose generation project (book).

        Args:
            title: Project title (auto-generates URL slug)
            description: Optional project description
            genre: Optional genre classification
            series_id: Optional series to assign this book to
            book_number: Book number within the series
        """
        body: dict = {"title": title}
        if description is not None:
            body["description"] = description
        if genre is not None:
            body["genre"] = genre
        if series_id is not None:
            body["series_id"] = series_id
        if book_number is not None:
            body["book_number"] = book_number
        return await safe_post("/api/projects", json=body)

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_list_series() -> dict:
        """List all book series with their metadata and book lists."""
        return await safe_get("/api/series")

    @mcp.tool()
    async def prose_create_series(
        title: str,
        description: str | None = None,
        genre: str | None = None,
    ) -> dict:
        """Create a new book series for grouping related projects.

        Args:
            title: Series title
            description: Optional series description
            genre: Optional genre
        """
        body: dict = {"title": title}
        if description is not None:
            body["description"] = description
        if genre is not None:
            body["genre"] = genre
        return await safe_post("/api/series", json=body)
