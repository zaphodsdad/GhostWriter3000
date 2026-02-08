"""Extraction, analysis, and health check tools."""

from __future__ import annotations

from fastmcp import FastMCP

from prose_mcp.client import safe_get, safe_post, LONG_TIMEOUT


def register_extraction_tools(mcp: FastMCP) -> None:

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
        """Check if the prose-pipeline API is running and healthy.

        Returns status, timestamp, and version.
        """
        return await safe_get("/api/health")
