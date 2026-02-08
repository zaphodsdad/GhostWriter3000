"""Project and series management tools."""

from __future__ import annotations

from fastmcp import FastMCP

from prose_mcp.client import safe_get, safe_post, safe_put, safe_delete


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

    @mcp.tool()
    async def prose_update_project(
        project_id: str,
        title: str | None = None,
        description: str | None = None,
        author: str | None = None,
        genre: str | None = None,
        series_id: str | None = None,
        book_number: int | None = None,
        word_count_goal: int | None = None,
    ) -> dict:
        """Update an existing project's metadata. Only provided fields are changed.

        Args:
            project_id: Project ID
            title: New title
            description: New description
            author: Author name
            genre: Genre classification
            series_id: Assign to or change series (use empty string to unassign)
            book_number: Book number within series
            word_count_goal: Target word count for the project
        """
        body: dict = {}
        if title is not None:
            body["title"] = title
        if description is not None:
            body["description"] = description
        if author is not None:
            body["author"] = author
        if genre is not None:
            body["genre"] = genre
        if series_id is not None:
            body["series_id"] = series_id
        if book_number is not None:
            body["book_number"] = book_number
        if word_count_goal is not None:
            body["word_count_goal"] = word_count_goal
        return await safe_put(f"/api/projects/{project_id}", json=body)

    @mcp.tool()
    async def prose_delete_project(project_id: str) -> dict:
        """Delete an entire project. WARNING: This permanently removes the project
        and all its data (acts, chapters, scenes, characters, world contexts).

        Args:
            project_id: Project ID to delete
        """
        return await safe_delete(f"/api/projects/{project_id}")

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_export_project(project_id: str) -> dict:
        """Export a project as a single markdown file.

        Returns the full manuscript assembled from all canon scenes,
        organized by acts and chapters.

        Args:
            project_id: Project ID
        """
        return await safe_get(f"/api/projects/{project_id}/export")

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_get_series(series_id: str) -> dict:
        """Get full details for a single series including book list.

        Args:
            series_id: Series ID
        """
        return await safe_get(f"/api/series/{series_id}")

    @mcp.tool()
    async def prose_update_series(
        series_id: str,
        title: str | None = None,
        description: str | None = None,
        author: str | None = None,
        genre: str | None = None,
        total_planned_books: int | None = None,
    ) -> dict:
        """Update an existing series. Only provided fields are changed.

        Args:
            series_id: Series ID
            title: New title
            description: New description
            author: Author name
            genre: Genre classification
            total_planned_books: Planned number of books in the series
        """
        body: dict = {}
        if title is not None:
            body["title"] = title
        if description is not None:
            body["description"] = description
        if author is not None:
            body["author"] = author
        if genre is not None:
            body["genre"] = genre
        if total_planned_books is not None:
            body["total_planned_books"] = total_planned_books
        return await safe_put(f"/api/series/{series_id}", json=body)

    @mcp.tool()
    async def prose_delete_series(series_id: str) -> dict:
        """Delete a series. WARNING: Books in the series are preserved but
        will no longer be grouped.

        Args:
            series_id: Series ID to delete
        """
        return await safe_delete(f"/api/series/{series_id}")
