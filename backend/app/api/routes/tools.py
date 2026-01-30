"""Tools API endpoints for grammar checking and other utilities."""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.utils.file_utils import read_json_file

router = APIRouter()
logger = logging.getLogger(__name__)

# Lazy-load LanguageTool to avoid startup delay
_language_tool = None


def get_language_tool():
    """Get or create LanguageTool instance (lazy loading)."""
    global _language_tool
    if _language_tool is None:
        try:
            import language_tool_python
            logger.info("Initializing LanguageTool (first use - may download ~200MB)...")
            _language_tool = language_tool_python.LanguageTool('en-US')
            logger.info("LanguageTool initialized successfully")
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail="language_tool_python not installed. Run: pip install language_tool_python"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize LanguageTool: {str(e)}"
            )
    return _language_tool


class GrammarMatch(BaseModel):
    """A single grammar/spelling/style issue."""
    offset: int = Field(..., description="Character offset in text")
    length: int = Field(..., description="Length of the problematic text")
    message: str = Field(..., description="Description of the issue")
    context: str = Field(..., description="Text surrounding the issue")
    replacements: List[str] = Field(default_factory=list, description="Suggested corrections")
    rule_id: str = Field(..., description="Rule identifier")
    category: str = Field(..., description="Issue category (GRAMMAR, SPELLING, etc.)")
    issue_type: str = Field(..., description="Issue type (misspelling, grammar, etc.)")


class LanguageToolRequest(BaseModel):
    """Request for grammar checking."""
    text: Optional[str] = Field(None, description="Text to check (use this OR project_id+scene_id)")
    project_id: Optional[str] = Field(None, description="Project ID to fetch scene from")
    scene_id: Optional[str] = Field(None, description="Scene ID to check")
    language: str = Field("en-US", description="Language code")


class LanguageToolResponse(BaseModel):
    """Response from grammar checking."""
    text_length: int = Field(..., description="Length of checked text")
    word_count: int = Field(..., description="Word count of checked text")
    match_count: int = Field(..., description="Number of issues found")
    matches: List[GrammarMatch] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict, description="Issues grouped by category")


class AutoCorrectRequest(BaseModel):
    """Request for auto-correction."""
    text: str = Field(..., description="Text to auto-correct")
    language: str = Field("en-US", description="Language code")


class AutoCorrectResponse(BaseModel):
    """Response from auto-correction."""
    original: str
    corrected: str
    changes_made: int


@router.post("/languagetool", response_model=LanguageToolResponse)
async def check_grammar(request: LanguageToolRequest):
    """
    Check text for grammar, spelling, and style issues using LanguageTool.

    Provide either:
    - `text`: Raw text to check
    - `project_id` + `scene_id`: Fetch prose from a scene

    Returns detailed issue information with suggestions.
    """
    # Get text to check
    text = request.text

    if not text and request.project_id and request.scene_id:
        # Fetch from scene
        scene_file = settings.scenes_dir(request.project_id) / f"{request.scene_id}.json"
        if not scene_file.exists():
            raise HTTPException(status_code=404, detail=f"Scene not found: {request.scene_id}")

        scene = await read_json_file(scene_file)

        # Get prose from scene (same logic as evaluation)
        text = scene.get('prose') or scene.get('original_prose')
        if not text:
            raise HTTPException(
                status_code=400,
                detail=f"Scene '{request.scene_id}' has no prose to check"
            )

    if not text:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'text' or 'project_id' + 'scene_id'"
        )

    try:
        tool = get_language_tool()
        matches = tool.check(text)

        # Format matches
        formatted_matches = []
        category_counts = {}

        for m in matches:
            category = m.category if hasattr(m, 'category') else 'UNKNOWN'
            if hasattr(m, 'category') and hasattr(m.category, 'name'):
                category = m.category.name

            # Track category counts
            category_counts[category] = category_counts.get(category, 0) + 1

            # Get context (text around the error)
            start = max(0, m.offset - 20)
            end = min(len(text), m.offset + m.errorLength + 20)
            context = text[start:end]
            if start > 0:
                context = "..." + context
            if end < len(text):
                context = context + "..."

            formatted_matches.append(GrammarMatch(
                offset=m.offset,
                length=m.errorLength,
                message=m.message,
                context=context,
                replacements=[r for r in m.replacements[:5]],  # Limit to 5 suggestions
                rule_id=m.ruleId,
                category=category,
                issue_type=m.ruleIssueType if hasattr(m, 'ruleIssueType') else 'unknown'
            ))

        return LanguageToolResponse(
            text_length=len(text),
            word_count=len(text.split()),
            match_count=len(formatted_matches),
            matches=formatted_matches,
            summary=category_counts
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LanguageTool check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Grammar check failed: {str(e)}")


@router.post("/languagetool/correct", response_model=AutoCorrectResponse)
async def auto_correct(request: AutoCorrectRequest):
    """
    Auto-correct text using LanguageTool suggestions.

    WARNING: This automatically applies all suggestions.
    Use with caution - review changes before accepting.
    """
    try:
        tool = get_language_tool()

        # Count issues first
        matches = tool.check(request.text)
        changes = len(matches)

        # Apply corrections
        corrected = tool.correct(request.text)

        return AutoCorrectResponse(
            original=request.text,
            corrected=corrected,
            changes_made=changes
        )

    except Exception as e:
        logger.error(f"LanguageTool correction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Auto-correct failed: {str(e)}")


@router.get("/languagetool/health")
async def languagetool_health():
    """Check if LanguageTool is available and working."""
    try:
        tool = get_language_tool()
        # Quick test
        matches = tool.check("This is a test.")
        return {
            "status": "healthy",
            "language": "en-US",
            "test_result": "ok"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
