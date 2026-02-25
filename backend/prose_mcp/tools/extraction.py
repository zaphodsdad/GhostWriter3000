"""Extraction, analysis, and health check tools for GhostWriter 3000."""

from __future__ import annotations

from fastmcp import FastMCP

from prose_mcp.client import safe_get, safe_post, safe_post_form, LONG_TIMEOUT


def register_extraction_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def prose_import_manuscript(
        project_id: str,
        text: str,
        enable_edit_mode: bool = True,
        create_chapters: bool = True,
    ) -> dict:
        """Import manuscript text into a project, auto-detecting chapter breaks.

        Splits the text at chapter markers (e.g., "Chapter 1", "CHAPTER ONE"),
        creates chapter structure, and imports each chapter as a scene in edit
        mode. Use this for loading source material like novels into the system.

        Args:
            project_id: Target project ID
            text: Full manuscript text (plain text or markdown)
            enable_edit_mode: Put scenes in edit mode (default True)
            create_chapters: Auto-create chapter structure (default True)
        """
        # Step 1: Split text into chapters
        split_result = await safe_post_form(
            f"/api/projects/{project_id}/manuscript/split",
            data={"text": text},
            timeout=LONG_TIMEOUT,
        )

        chapters = split_result.get("chapters", [])
        if not chapters:
            return {
                "status": "no_chapters",
                "message": "No chapter breaks detected in the text.",
            }

        # Step 2: Import the detected chapters
        return await safe_post(
            f"/api/projects/{project_id}/manuscript/import-bulk",
            json={
                "chapters": chapters,
                "enable_edit_mode": enable_edit_mode,
                "create_chapters": create_chapters,
            },
            timeout=LONG_TIMEOUT,
        )

    @mcp.tool()
    async def prose_analyze_manuscript(
        text: str,
        model: str | None = None,
        author_name: str | None = None,
    ) -> dict:
        """Analyze prose text to extract characters, world elements, and style.

        Runs comprehensive AI analysis: character extraction, world building
        detection, and writing style analysis. Requires at least 500 characters
        of prose.

        Args:
            text: Prose text to analyze (minimum 500 characters)
            model: Optional LLM model override
            author_name: Optional author name for the style guide
        """
        body: dict = {"text": text}
        if model is not None:
            body["model"] = model
        if author_name is not None:
            body["author_name"] = author_name
        return await safe_post("/api/extract/analyze", json=body, timeout=LONG_TIMEOUT)

    @mcp.tool(annotations={"readOnlyHint": True})
    async def prose_health_check() -> dict:
        """Check if the GhostWriter 3000 API is running and healthy.

        Returns status, timestamp, and version.
        """
        return await safe_get("/api/health")
