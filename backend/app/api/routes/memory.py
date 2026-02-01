"""API routes for Series Memory Layer."""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException

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
