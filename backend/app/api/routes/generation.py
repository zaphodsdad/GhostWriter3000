"""Generation pipeline API endpoints (project-scoped)."""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import List, Optional
from pydantic import BaseModel

from app.models.generation import (
    GenerationStart,
    EditModeStart,
    GenerationResponse,
    GenerationState,
    GenerationStatus
)
from app.services.generation_service import get_generation_service
from app.api.routes.settings import load_user_settings
from app.config import settings

router = APIRouter()


class ApproveRequest(BaseModel):
    """Request body for approve and revise."""
    instructions: Optional[str] = None  # Optional revision guidance from user


class SelectionRevisionRequest(BaseModel):
    """Request body for selection-based revision."""
    selection_start: int  # Start character index in prose
    selection_end: int    # End character index in prose
    selection_text: str   # The selected text (for verification)
    instructions: Optional[str] = None  # Optional revision guidance


def get_effective_models(gen_model: Optional[str], critique_model: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Get effective models, falling back to user settings if not specified."""
    user_settings = load_user_settings()

    effective_gen = gen_model or user_settings.get("default_generation_model")
    effective_critique = critique_model or user_settings.get("default_critique_model")

    return effective_gen, effective_critique


def ensure_project_exists(project_id: str):
    """Check that project exists, raise 404 if not."""
    if not settings.project_dir(project_id).exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")


@router.post("/start", response_model=GenerationResponse)
async def start_generation(project_id: str, request: GenerationStart, background_tasks: BackgroundTasks):
    """
    Start a new generation pipeline for a scene.

    Args:
        project_id: Project ID
        request: Generation start request with scene_id and max_iterations

    Returns:
        Initial generation state

    Raises:
        HTTPException: If scene not found or invalid
    """
    ensure_project_exists(project_id)

    # Get effective models (user settings override if not specified in request)
    gen_model, critique_model = get_effective_models(
        request.generation_model,
        request.critique_model
    )

    try:
        service = get_generation_service()
        state = await service.start_generation(
            project_id=project_id,
            scene_id=request.scene_id,
            max_iterations=request.max_iterations,
            generation_model=gen_model,
            critique_model=critique_model,
            revision_mode=request.revision_mode
        )

        return _build_response(state)

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.post("/start-edit", response_model=GenerationResponse)
async def start_edit_mode_generation(project_id: str, request: EditModeStart, background_tasks: BackgroundTasks):
    """
    Start edit mode generation for a scene with imported prose.

    This skips the initial generation step and goes directly to critique.
    The scene must already be in edit mode with original_prose set.

    Args:
        project_id: Project ID
        request: EditModeStart request with scene_id and max_iterations

    Returns:
        Initial generation state (starting at critique phase)

    Raises:
        HTTPException: If scene not found, not in edit mode, or missing prose
    """
    ensure_project_exists(project_id)

    # Get effective models (user settings override if not specified in request)
    gen_model, critique_model = get_effective_models(
        request.generation_model,
        request.critique_model
    )

    try:
        service = get_generation_service()
        state = await service.start_edit_mode_generation(
            project_id=project_id,
            scene_id=request.scene_id,
            max_iterations=request.max_iterations,
            generation_model=gen_model,
            critique_model=critique_model,
            revision_mode=request.revision_mode
        )

        return _build_response(state)

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Edit mode generation failed: {str(e)}")


@router.get("/queue", response_model=List[GenerationResponse])
async def get_generation_queue(
    project_id: str,
    status: Optional[str] = Query(None, description="Filter by status (e.g., 'awaiting_approval', 'generating')")
):
    """
    Get all generations with full details, optionally filtered by status.

    Args:
        project_id: Project ID
        status: Optional status filter

    Returns:
        List of generation states with full details, sorted by created_at (newest first)
    """
    ensure_project_exists(project_id)

    try:
        service = get_generation_service()
        states = await service.state_manager.get_generations_by_status(project_id, status)
        return [_build_response(state) for state in states]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{generation_id}", response_model=GenerationResponse)
async def get_generation(project_id: str, generation_id: str):
    """
    Get current generation state.

    Args:
        project_id: Project ID
        generation_id: Unique generation identifier

    Returns:
        Current generation state

    Raises:
        HTTPException: If generation not found
    """
    ensure_project_exists(project_id)

    try:
        service = get_generation_service()
        state = await service.get_state(project_id, generation_id)
        return _build_response(state)

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Generation not found: {generation_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{generation_id}/approve", response_model=GenerationResponse)
async def approve_and_revise(project_id: str, generation_id: str, request: ApproveRequest = None):
    """
    Approve current iteration and trigger revision.

    Args:
        project_id: Project ID
        generation_id: Unique generation identifier
        request: Optional request body with revision instructions

    Returns:
        Updated generation state

    Raises:
        HTTPException: If generation not found or not awaiting approval
    """
    ensure_project_exists(project_id)

    # Extract instructions from request body if provided
    instructions = request.instructions if request else None

    try:
        service = get_generation_service()
        state = await service.approve_and_revise(project_id, generation_id, instructions=instructions)
        return _build_response(state)

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Generation not found: {generation_id}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class UpdateProseRequest(BaseModel):
    """Request body for updating generation prose."""
    prose: str


@router.put("/{generation_id}/prose", response_model=GenerationResponse)
async def update_prose(project_id: str, generation_id: str, request: UpdateProseRequest):
    """
    Update the current prose in a generation.

    Used for applying selective changes from diff view.

    Args:
        project_id: Project ID
        generation_id: Unique generation identifier
        request: New prose content

    Returns:
        Updated generation state

    Raises:
        HTTPException: If generation not found or not awaiting approval
    """
    ensure_project_exists(project_id)

    try:
        service = get_generation_service()
        state = await service.update_prose(project_id, generation_id, request.prose)
        return _build_response(state)

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Generation not found: {generation_id}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{generation_id}/revise-selection", response_model=GenerationResponse)
async def revise_selection(project_id: str, generation_id: str, request: SelectionRevisionRequest):
    """
    Revise only a selected portion of the prose.

    Args:
        project_id: Project ID
        generation_id: Unique generation identifier
        request: Selection details and optional instructions

    Returns:
        Updated generation state

    Raises:
        HTTPException: If generation not found or not awaiting approval
    """
    ensure_project_exists(project_id)

    try:
        service = get_generation_service()
        state = await service.revise_selection(
            project_id,
            generation_id,
            selection_start=request.selection_start,
            selection_end=request.selection_end,
            selection_text=request.selection_text,
            instructions=request.instructions
        )
        return _build_response(state)

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Generation not found: {generation_id}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{generation_id}/accept", response_model=GenerationResponse)
async def accept_final(project_id: str, generation_id: str):
    """
    Accept current prose as final and generate summary.

    Args:
        project_id: Project ID
        generation_id: Unique generation identifier

    Returns:
        Updated generation state

    Raises:
        HTTPException: If generation not found or not awaiting approval
    """
    ensure_project_exists(project_id)

    try:
        service = get_generation_service()
        state = await service.accept_final(project_id, generation_id)
        return _build_response(state)

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Generation not found: {generation_id}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{generation_id}/reject", response_model=GenerationResponse)
async def reject_generation(project_id: str, generation_id: str):
    """
    Reject generation and mark as rejected.

    Args:
        project_id: Project ID
        generation_id: Unique generation identifier

    Returns:
        Updated generation state

    Raises:
        HTTPException: If generation not found
    """
    ensure_project_exists(project_id)

    try:
        service = get_generation_service()
        state = await service.reject_generation(project_id, generation_id)
        return _build_response(state)

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Generation not found: {generation_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{generation_id}")
async def delete_generation(project_id: str, generation_id: str):
    """
    Delete generation state.

    Args:
        project_id: Project ID
        generation_id: Unique generation identifier

    Returns:
        Success message

    Raises:
        HTTPException: If generation not found
    """
    ensure_project_exists(project_id)

    try:
        service = get_generation_service()
        await service.state_manager.delete_state(project_id, generation_id)
        return {"message": f"Generation {generation_id} deleted successfully"}

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Generation not found: {generation_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[str])
async def list_generations(project_id: str):
    """
    List all generation IDs in a project.

    Args:
        project_id: Project ID

    Returns:
        List of generation IDs
    """
    ensure_project_exists(project_id)

    try:
        service = get_generation_service()
        return await service.state_manager.list_generations(project_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _build_response(state: GenerationState) -> GenerationResponse:
    """
    Build API response from generation state.

    Args:
        state: Generation state

    Returns:
        Generation response
    """
    return GenerationResponse(
        generation_id=state.generation_id,
        project_id=state.project_id,
        scene_id=state.scene_id,
        status=state.status,
        current_iteration=state.current_iteration,
        max_iterations=state.max_iterations,
        can_revise=state.can_revise,
        revision_mode=state.revision_mode,
        current_prose=state.current_prose,
        current_critique=state.current_critique,
        final_prose=state.final_prose,
        scene_summary=state.scene_summary,
        history=state.iterations,
        created_at=state.created_at,
        updated_at=state.updated_at
    )
