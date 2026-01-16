"""Grammar and style checking API endpoints (project-scoped)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.grammar_service import get_grammar_service, GrammarCheckResult
from app.config import settings

router = APIRouter()


class CheckProseRequest(BaseModel):
    """Request body for grammar check."""
    prose: str
    enable_all_rules: bool = False  # Include strict/noisy rules


class GrammarStatusResponse(BaseModel):
    """Response for grammar service status."""
    available: bool
    message: str


def ensure_project_exists(project_id: str):
    """Check that project exists, raise 404 if not."""
    if not settings.project_dir(project_id).exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")


@router.get("/status", response_model=GrammarStatusResponse)
async def get_grammar_status(project_id: str):
    """
    Check if grammar checking is available.

    Returns availability status and any error messages.
    """
    ensure_project_exists(project_id)

    try:
        service = get_grammar_service()
        available = service.is_available()
        return GrammarStatusResponse(
            available=available,
            message="Grammar checking is available" if available else "Grammar checking unavailable"
        )
    except Exception as e:
        return GrammarStatusResponse(
            available=False,
            message=f"Grammar checking unavailable: {str(e)}"
        )


@router.post("/check", response_model=GrammarCheckResult)
async def check_prose(project_id: str, request: CheckProseRequest):
    """
    Check prose for grammar and style issues.

    Args:
        project_id: Project ID (for scoping)
        request: CheckProseRequest with prose text

    Returns:
        GrammarCheckResult with all found issues
    """
    ensure_project_exists(project_id)

    if not request.prose or not request.prose.strip():
        raise HTTPException(status_code=400, detail="No prose provided")

    try:
        service = get_grammar_service()
        result = service.check_text(
            request.prose,
            enable_all_rules=request.enable_all_rules
        )
        return result

    except RuntimeError as e:
        # LanguageTool initialization failed (e.g., no Java)
        raise HTTPException(
            status_code=503,
            detail=f"Grammar service unavailable: {str(e)}. Ensure Java is installed."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Grammar check failed: {str(e)}")
