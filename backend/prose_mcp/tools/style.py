"""Style guide management tools — project and series level."""

from __future__ import annotations

from fastmcp import FastMCP

from prose_mcp.client import safe_get, safe_put


def register_style_tools(mcp: FastMCP) -> None:

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_get_project_style(project_id: str) -> dict:
        """Get the style guide for a project.

        Returns POV, tense, tone, heat level, and the full style guide text.

        Args:
            project_id: Project ID
        """
        return await safe_get(f"/api/projects/{project_id}/style")

    @mcp.tool()
    async def prose_update_project_style(
        project_id: str,
        pov: str | None = None,
        tense: str | None = None,
        tone: str | None = None,
        heat_level: str | None = None,
        guide: str | None = None,
    ) -> dict:
        """Update the style guide for a project. Only provided fields are changed.

        Args:
            project_id: Project ID
            pov: Point of view (e.g. 'first person', 'third person limited')
            tense: Narrative tense (e.g. 'past', 'present')
            tone: Overall tone (e.g. 'dark', 'literary', 'commercial')
            heat_level: Content heat level for romance/adult content
            guide: Full style guide text with detailed writing instructions
        """
        body: dict = {}
        if pov is not None:
            body["pov"] = pov
        if tense is not None:
            body["tense"] = tense
        if tone is not None:
            body["tone"] = tone
        if heat_level is not None:
            body["heat_level"] = heat_level
        if guide is not None:
            body["guide"] = guide
        return await safe_put(f"/api/projects/{project_id}/style", json=body)

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_get_series_style(series_id: str) -> dict:
        """Get the style guide for a series (shared across all books).

        Args:
            series_id: Series ID
        """
        return await safe_get(f"/api/series/{series_id}/style")

    @mcp.tool()
    async def prose_update_series_style(
        series_id: str,
        pov: str | None = None,
        tense: str | None = None,
        tone: str | None = None,
        heat_level: str | None = None,
        guide: str | None = None,
    ) -> dict:
        """Update the style guide for a series. Only provided fields are changed.
        Series style applies to all books unless overridden at the project level.

        Args:
            series_id: Series ID
            pov: Point of view
            tense: Narrative tense
            tone: Overall tone
            heat_level: Content heat level
            guide: Full style guide text
        """
        body: dict = {}
        if pov is not None:
            body["pov"] = pov
        if tense is not None:
            body["tense"] = tense
        if tone is not None:
            body["tone"] = tone
        if heat_level is not None:
            body["heat_level"] = heat_level
        if guide is not None:
            body["guide"] = guide
        return await safe_put(f"/api/series/{series_id}/style", json=body)
