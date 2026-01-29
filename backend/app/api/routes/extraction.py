"""Extraction API routes for analyzing manuscripts and extracting story elements."""

from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.extraction_service import get_extraction_service

router = APIRouter(prefix="/api/extract", tags=["extraction"])


class ExtractCharactersRequest(BaseModel):
    """Request body for character extraction."""
    text: str
    model: Optional[str] = None
    existing_characters: Optional[List[str]] = None


class ExtractWorldRequest(BaseModel):
    """Request body for world/lore extraction."""
    text: str
    model: Optional[str] = None
    existing_elements: Optional[List[str]] = None


class ExtractStyleRequest(BaseModel):
    """Request body for style guide extraction."""
    text: str
    model: Optional[str] = None
    author_name: Optional[str] = None


class AnalyzeManuscriptRequest(BaseModel):
    """Request body for full manuscript analysis."""
    text: str
    model: Optional[str] = None
    author_name: Optional[str] = None


class EvaluateManuscriptRequest(BaseModel):
    """Request body for manuscript evaluation."""
    text: str
    model: Optional[str] = None


@router.post("/characters")
async def extract_characters(request: ExtractCharactersRequest):
    """
    Extract character information from prose text.

    Analyzes the provided text and returns structured character data including:
    - Names and roles (protagonist, antagonist, supporting, minor)
    - Physical descriptions
    - Personality traits
    - Relationships
    - Voice patterns
    - First appearances

    Args:
        request: ExtractCharactersRequest with text and optional parameters

    Returns:
        Dict with 'characters' list and 'usage' token stats
    """
    if not request.text or len(request.text.strip()) < 100:
        raise HTTPException(status_code=400, detail="Text must be at least 100 characters")

    service = get_extraction_service()
    try:
        result = await service.extract_characters(
            text=request.text,
            model=request.model,
            existing_characters=request.existing_characters
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Character extraction failed: {str(e)}")


@router.post("/world")
async def extract_world(request: ExtractWorldRequest):
    """
    Extract world-building elements from prose text.

    Analyzes the provided text and returns structured world data including:
    - Locations
    - Magic systems
    - Technology
    - History and lore
    - Political structures
    - Culture and customs
    - Creatures and species
    - Important items/artifacts

    Args:
        request: ExtractWorldRequest with text and optional parameters

    Returns:
        Dict with 'world_elements' list and 'usage' token stats
    """
    if not request.text or len(request.text.strip()) < 100:
        raise HTTPException(status_code=400, detail="Text must be at least 100 characters")

    service = get_extraction_service()
    try:
        result = await service.extract_world(
            text=request.text,
            model=request.model,
            existing_elements=request.existing_elements
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"World extraction failed: {str(e)}")


@router.post("/style")
async def extract_style(request: ExtractStyleRequest):
    """
    Generate a style guide from prose text.

    Analyzes the author's writing patterns to create a comprehensive style guide:
    - Sentence structure preferences
    - Vocabulary and formality
    - Dialogue techniques
    - POV and narrative distance
    - Description style
    - Pacing patterns
    - Tone and voice
    - Distinctive patterns and signatures

    For best results, provide at least 5000 words of prose.

    Args:
        request: ExtractStyleRequest with text and optional parameters

    Returns:
        Dict with 'style_guide' object and 'usage' token stats
    """
    if not request.text or len(request.text.strip()) < 500:
        raise HTTPException(status_code=400, detail="Text must be at least 500 characters (5000+ words recommended)")

    service = get_extraction_service()
    try:
        result = await service.extract_style(
            text=request.text,
            model=request.model,
            author_name=request.author_name
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Style extraction failed: {str(e)}")


@router.post("/analyze")
async def analyze_manuscript(request: AnalyzeManuscriptRequest):
    """
    Perform comprehensive manuscript analysis.

    Runs all three extraction types (characters, world, style) on the provided text.
    This is a convenience endpoint that combines:
    - /extract/characters
    - /extract/world
    - /extract/style

    Note: This makes multiple LLM calls and may take longer than individual endpoints.

    Args:
        request: AnalyzeManuscriptRequest with text and optional parameters

    Returns:
        Dict with 'characters', 'world_elements', 'style_guide', and combined 'usage' stats
    """
    if not request.text or len(request.text.strip()) < 500:
        raise HTTPException(status_code=400, detail="Text must be at least 500 characters")

    service = get_extraction_service()
    try:
        result = await service.analyze_manuscript(
            text=request.text,
            model=request.model,
            author_name=request.author_name
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Manuscript analysis failed: {str(e)}")


@router.post("/evaluate")
async def evaluate_manuscript(request: EvaluateManuscriptRequest):
    """
    Evaluate manuscript quality, pacing, and structure.

    Provides developmental editing feedback including:
    - Overall quality assessment
    - Pacing analysis
    - Structure evaluation
    - Character development review
    - Dialogue quality
    - Prose quality
    - Consistency check
    - Engagement/hook analysis

    Each area receives a 1-10 score with specific feedback.

    Args:
        request: EvaluateManuscriptRequest with text and optional model

    Returns:
        Dict with 'evaluation' object containing scores and feedback, plus 'usage' stats
    """
    if not request.text or len(request.text.strip()) < 500:
        raise HTTPException(status_code=400, detail="Text must be at least 500 characters")

    service = get_extraction_service()
    try:
        result = await service.evaluate_manuscript(
            text=request.text,
            model=request.model
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Manuscript evaluation failed: {str(e)}")
