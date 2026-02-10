"""API routes for Series Memory Layer."""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.memory import SeriesMemory, SceneExtraction, ExtractionRequest
from app.services.memory_service import memory_service
from app.config import settings

router = APIRouter()


@router.get("/{series_id}/memory")
async def get_series_memory(series_id: str) -> Dict[str, Any]:
    """
    Get the complete memory state for a series.

    Returns the manifest, accumulated extractions, and generated summaries.
    """
    series_dir = settings.series_path(series_id)
    if not series_dir.exists():
        raise HTTPException(status_code=404, detail=f"Series not found: {series_id}")

    memory = memory_service.get_memory(series_id)
    if not memory:
        # Initialize if doesn't exist
        memory = memory_service.initialize_memory(series_id)

    return memory.model_dump()


@router.post("/{series_id}/memory/initialize")
async def initialize_series_memory(series_id: str) -> Dict[str, Any]:
    """
    Initialize or reset the memory structure for a series.

    Creates the memory directory and empty state files.
    """
    series_dir = settings.series_path(series_id)
    if not series_dir.exists():
        raise HTTPException(status_code=404, detail=f"Series not found: {series_id}")

    memory = memory_service.initialize_memory(series_id)
    return {
        "status": "initialized",
        "series_id": series_id,
        "memory": memory.model_dump()
    }


@router.get("/{series_id}/memory/context")
async def get_memory_context(series_id: str) -> Dict[str, str]:
    """
    Get compact context summaries for use in generation prompts.

    Returns only the generated summaries (character_states, world_state, timeline),
    ready to be injected into prompts.
    """
    series_dir = settings.series_path(series_id)
    if not series_dir.exists():
        raise HTTPException(status_code=404, detail=f"Series not found: {series_id}")

    return memory_service.get_context_for_generation(series_id)


@router.get("/{series_id}/memory/staleness")
async def check_memory_staleness(series_id: str) -> Dict[str, bool]:
    """
    Check which memory summaries are stale.

    Compares current file hashes against stored hashes to detect changes.
    Returns which categories need regeneration.
    """
    series_dir = settings.series_path(series_id)
    if not series_dir.exists():
        raise HTTPException(status_code=404, detail=f"Series not found: {series_id}")

    return memory_service.check_staleness(series_id)


@router.post("/{series_id}/memory/extract")
async def save_extraction(series_id: str, extraction: SceneExtraction) -> Dict[str, Any]:
    """
    Save extraction results from a scene.

    Called after marking a scene as canon. The extraction contains
    character state changes, world facts, and plot events.
    """
    series_dir = settings.series_path(series_id)
    if not series_dir.exists():
        raise HTTPException(status_code=404, detail=f"Series not found: {series_id}")

    memory_service.save_extraction(series_id, extraction)

    return {
        "status": "saved",
        "scene_id": extraction.scene_id,
        "character_changes": len(extraction.character_changes),
        "world_facts": len(extraction.world_facts),
        "plot_events": len(extraction.plot_events)
    }


@router.put("/{series_id}/memory/summaries/characters")
async def update_character_states_summary(series_id: str, summary: Dict[str, str]) -> Dict[str, str]:
    """
    Update the character states summary.

    The summary should be a compact representation of current character states,
    suitable for injection into generation prompts.
    """
    series_dir = settings.series_path(series_id)
    if not series_dir.exists():
        raise HTTPException(status_code=404, detail=f"Series not found: {series_id}")

    if "content" not in summary:
        raise HTTPException(status_code=400, detail="Missing 'content' field")

    memory_service.update_character_states(series_id, summary["content"])
    memory_service.update_hashes(series_id)

    return {"status": "updated", "type": "character_states"}


@router.put("/{series_id}/memory/summaries/world")
async def update_world_state_summary(series_id: str, summary: Dict[str, str]) -> Dict[str, str]:
    """
    Update the world state summary.
    """
    series_dir = settings.series_path(series_id)
    if not series_dir.exists():
        raise HTTPException(status_code=404, detail=f"Series not found: {series_id}")

    if "content" not in summary:
        raise HTTPException(status_code=400, detail="Missing 'content' field")

    memory_service.update_world_state(series_id, summary["content"])
    memory_service.update_hashes(series_id)

    return {"status": "updated", "type": "world_state"}


@router.put("/{series_id}/memory/summaries/timeline")
async def update_timeline_summary(series_id: str, summary: Dict[str, str]) -> Dict[str, str]:
    """
    Update the timeline summary.
    """
    series_dir = settings.series_path(series_id)
    if not series_dir.exists():
        raise HTTPException(status_code=404, detail=f"Series not found: {series_id}")

    if "content" not in summary:
        raise HTTPException(status_code=400, detail="Missing 'content' field")

    memory_service.update_timeline(series_id, summary["content"])

    return {"status": "updated", "type": "timeline"}


@router.delete("/{series_id}/memory")
async def clear_series_memory(series_id: str) -> Dict[str, str]:
    """
    Clear all memory for a series.

    Removes all extractions and resets summaries to empty state.
    Use with caution - this cannot be undone.
    """
    series_dir = settings.series_path(series_id)
    if not series_dir.exists():
        raise HTTPException(status_code=404, detail=f"Series not found: {series_id}")

    memory_service.clear_memory(series_id)

    return {"status": "cleared", "series_id": series_id}


@router.post("/{series_id}/memory/refresh-hashes")
async def refresh_hashes(series_id: str) -> Dict[str, Any]:
    """
    Refresh stored hashes for all source files.

    Call this after updating character/world files to mark them as "seen".
    """
    series_dir = settings.series_path(series_id)
    if not series_dir.exists():
        raise HTTPException(status_code=404, detail=f"Series not found: {series_id}")

    memory_service.update_hashes(series_id)

    return {"status": "refreshed", "series_id": series_id}


class GenerateSummariesRequest(BaseModel):
    """Request to generate summaries."""
    model: Optional[str] = Field(None, description="Optional model override")


class GenerateBookSummaryRequest(BaseModel):
    """Request to generate a book summary from memory."""
    book_id: str = Field(..., description="Book/project ID to summarize")
    model: Optional[str] = Field(None, description="Optional model override")


class GenerateTieredSummaryRequest(BaseModel):
    """Request to generate tiered book summaries."""
    book_id: str = Field(..., description="Book/project ID to summarize")
    book_title: str = Field(default="", description="Book title")
    book_number: int = Field(default=0, description="Book number in series")
    model: Optional[str] = Field(None, description="Optional model override")
    tier: str = Field(
        default="both",
        description="Which tier(s) to generate: 'essential', 'full', or 'both'"
    )


@router.post("/{series_id}/memory/generate-summaries")
async def generate_summaries(series_id: str, request: GenerateSummariesRequest = None) -> Dict[str, Any]:
    """
    Generate all summaries from accumulated extractions.

    Uses LLM to synthesize:
    - character_states.md: Current state of all characters
    - world_state.md: Established world facts organized by category
    - timeline.md: Chronological plot events

    This is typically called after marking multiple scenes as canon,
    or when you want to refresh the summaries.
    """
    series_dir = settings.series_path(series_id)
    if not series_dir.exists():
        raise HTTPException(status_code=404, detail=f"Series not found: {series_id}")

    model = request.model if request else None

    try:
        results = await memory_service.generate_summaries(series_id, model=model)
        return {
            "status": "generated",
            "series_id": series_id,
            "summaries_generated": list(results.keys()),
            "summaries": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate summaries: {str(e)}")


@router.post("/{series_id}/memory/generate-book-summary")
async def generate_book_summary(series_id: str, request: GenerateBookSummaryRequest) -> Dict[str, Any]:
    """
    Generate a book summary from accumulated memory for a specific book.

    This creates a prose summary suitable for the Book Summary feature,
    compiled from all extractions for scenes in that book. Useful for
    generating summaries of completed books for series continuity.
    """
    series_dir = settings.series_path(series_id)
    if not series_dir.exists():
        raise HTTPException(status_code=404, detail=f"Series not found: {series_id}")

    try:
        summary = await memory_service.generate_book_summary_from_memory(
            series_id,
            request.book_id,
            model=request.model
        )

        if not summary:
            return {
                "status": "empty",
                "message": "No memory data found for this book. Mark some scenes as canon first."
            }

        return {
            "status": "generated",
            "book_id": request.book_id,
            "summary": summary,
            "word_count": len(summary.split())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate book summary: {str(e)}")


@router.post("/{series_id}/memory/generate-tiered-summary")
async def generate_tiered_summary(series_id: str, request: GenerateTieredSummaryRequest) -> Dict[str, Any]:
    """
    Generate tiered book summaries from accumulated memory.

    Creates two versions optimized for different purposes:
    - Essential (~500 words): Key plot points only, used in generation context
    - Full (~2500 words): Complete details for reference and export

    Args:
        series_id: Series ID
        request: Book details and tier option

    Returns:
        BookSummary with both or specified tier(s)
    """
    series_dir = settings.series_path(series_id)
    if not series_dir.exists():
        raise HTTPException(status_code=404, detail=f"Series not found: {series_id}")

    if request.tier not in ("essential", "full", "both"):
        raise HTTPException(status_code=400, detail="tier must be 'essential', 'full', or 'both'")

    try:
        summary = await memory_service.generate_tiered_book_summary(
            series_id=series_id,
            book_id=request.book_id,
            book_title=request.book_title,
            book_number=request.book_number,
            model=request.model,
            tier=request.tier
        )

        if not summary:
            return {
                "status": "empty",
                "message": "No memory data found for this book. Mark some scenes as canon first."
            }

        return {
            "status": "generated",
            "book_id": request.book_id,
            "tier": request.tier,
            "essential": summary.essential,
            "essential_word_count": summary.essential_word_count,
            "full": summary.full,
            "full_word_count": summary.full_word_count,
            "generated_at": summary.generated_at.isoformat() if summary.generated_at else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate tiered summary: {str(e)}")


@router.get("/{series_id}/memory/book-summary/{book_id}")
async def get_book_summary(series_id: str, book_id: str, tier: str = "essential") -> Dict[str, Any]:
    """
    Get a stored book summary.

    Args:
        series_id: Series ID
        book_id: Book/project ID
        tier: Which tier to return: 'essential' (default) or 'full'

    Returns:
        Summary text and metadata
    """
    series_dir = settings.series_path(series_id)
    if not series_dir.exists():
        raise HTTPException(status_code=404, detail=f"Series not found: {series_id}")

    if tier not in ("essential", "full"):
        raise HTTPException(status_code=400, detail="tier must be 'essential' or 'full'")

    memory = memory_service.get_memory(series_id)
    if not memory:
        raise HTTPException(status_code=404, detail="No memory found for series")

    book_summary = memory.book_summaries.get(book_id)
    if not book_summary:
        return {
            "status": "not_found",
            "message": f"No summary found for book {book_id}. Generate one first."
        }

    summary_text = book_summary.essential if tier == "essential" else book_summary.full
    word_count = book_summary.essential_word_count if tier == "essential" else book_summary.full_word_count

    return {
        "status": "found",
        "book_id": book_id,
        "tier": tier,
        "summary": summary_text,
        "word_count": word_count,
        "generated_at": book_summary.generated_at.isoformat() if book_summary.generated_at else None,
        "has_essential": bool(book_summary.essential),
        "has_full": bool(book_summary.full)
    }


@router.get("/{series_id}/memory/book-summaries")
async def list_book_summaries(series_id: str) -> Dict[str, Any]:
    """
    List all stored book summaries for a series.

    Returns metadata about available summaries without the full text.
    """
    series_dir = settings.series_path(series_id)
    if not series_dir.exists():
        raise HTTPException(status_code=404, detail=f"Series not found: {series_id}")

    memory = memory_service.get_memory(series_id)
    if not memory:
        return {"summaries": []}

    summaries = []
    for book_id, summary in memory.book_summaries.items():
        summaries.append({
            "book_id": book_id,
            "book_number": summary.book_number,
            "title": summary.title,
            "has_essential": bool(summary.essential),
            "essential_word_count": summary.essential_word_count,
            "has_full": bool(summary.full),
            "full_word_count": summary.full_word_count,
            "generated_at": summary.generated_at.isoformat() if summary.generated_at else None
        })

    # Sort by book number
    summaries.sort(key=lambda x: x["book_number"])

    return {"summaries": summaries}


class ExtractFromSceneRequest(BaseModel):
    """Request to LLM-extract memory facts from a scene's prose."""
    book_id: str = Field(..., description="Book/project ID containing the scene")
    scene_id: str = Field(..., description="Scene ID")
    prose: str = Field(..., description="Scene prose text to extract from")
    scene_title: Optional[str] = Field(None, description="Scene title for context")
    chapter_title: Optional[str] = Field(None, description="Chapter title for context")
    book_number: Optional[int] = Field(None, description="Book number in series")
    chapter_number: Optional[int] = Field(None, description="Chapter number")
    scene_number: Optional[int] = Field(None, description="Scene number")
    character_names: Optional[list] = Field(None, description="Known character names for better extraction")
    model: Optional[str] = Field(None, description="Optional LLM model override")


@router.post("/{series_id}/memory/extract-from-scene")
async def extract_from_scene(series_id: str, request: ExtractFromSceneRequest) -> Dict[str, Any]:
    """
    Extract memory facts from a scene using LLM analysis.

    Runs AI extraction to identify character state changes, world facts,
    and plot events from the scene prose. Results are saved to the series
    memory layer automatically.

    This is the tool CYOABot calls after generating and accepting a new scene.
    """
    series_dir = settings.series_path(series_id)
    if not series_dir.exists():
        raise HTTPException(status_code=404, detail=f"Series not found: {series_id}")

    try:
        extraction = await memory_service.extract_from_scene(
            series_id=series_id,
            book_id=request.book_id,
            scene_id=request.scene_id,
            prose=request.prose,
            scene_title=request.scene_title,
            chapter_title=request.chapter_title,
            book_number=request.book_number,
            chapter_number=request.chapter_number,
            scene_number=request.scene_number,
            character_names=request.character_names,
            model=request.model,
        )

        return {
            "status": "extracted",
            "scene_id": request.scene_id,
            "character_changes": len(extraction.character_changes),
            "world_facts": len(extraction.world_facts),
            "plot_events": len(extraction.plot_events),
            "extraction": extraction.model_dump(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scene extraction failed: {str(e)}")


class ContinuityCheckRequest(BaseModel):
    """Request to check prose for continuity issues."""
    prose_text: str = Field(..., description="Prose to check for continuity issues")
    scene_context: Optional[str] = Field(None, description="Optional scene outline for context")
    model: Optional[str] = Field(None, description="Optional model override")


@router.post("/{series_id}/memory/check-continuity")
async def check_continuity(series_id: str, request: ContinuityCheckRequest) -> Dict[str, Any]:
    """
    Check prose text for continuity issues against series memory.

    Compares the provided prose against established facts in the memory layer
    and returns any detected contradictions.

    Returns:
        - issues: List of potential continuity problems
        - checked_against: Count of facts checked per category
        - has_issues: Whether any issues were found
    """
    series_dir = settings.series_path(series_id)
    if not series_dir.exists():
        raise HTTPException(status_code=404, detail=f"Series not found: {series_id}")

    from app.services.continuity_service import get_continuity_service
    service = get_continuity_service()

    try:
        result = await service.check_continuity(
            series_id=series_id,
            prose_text=request.prose_text,
            scene_context=request.scene_context,
            model=request.model
        )

        return {
            "has_issues": result.has_issues,
            "issue_count": len(result.issues),
            "checked_against": result.checked_against,
            "issues": [issue.model_dump() for issue in result.issues]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Continuity check failed: {str(e)}")
