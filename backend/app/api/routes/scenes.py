"""Scene management API endpoints (project-scoped)."""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel, Field

from app.models.scene import Scene, SceneCreate, SceneUpdate
from app.config import settings
from app.utils.file_utils import write_json_file, read_json_file, delete_file
from app.utils.backup import backup_scene

router = APIRouter()


def ensure_project_exists(project_id: str):
    """Check that project exists, raise 404 if not."""
    if not settings.project_dir(project_id).exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")


def validate_chapter_exists(project_id: str, chapter_id: str):
    """Validate that a chapter exists in the project."""
    chapters_dir = settings.project_dir(project_id) / "chapters"
    chapter_file = chapters_dir / f"{chapter_id}.json"
    if not chapter_file.exists():
        raise HTTPException(status_code=400, detail=f"Chapter not found: {chapter_id}")


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    import re
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text


@router.post("/", response_model=Scene)
async def create_scene(project_id: str, scene_data: SceneCreate):
    """
    Create a new scene in a project.

    Args:
        project_id: Project ID
        scene_data: Scene data (chapter_id is required)

    Returns:
        Created scene

    Raises:
        HTTPException: If scene creation fails or chapter not found
    """
    ensure_project_exists(project_id)
    validate_chapter_exists(project_id, scene_data.chapter_id)

    try:
        scenes_dir = settings.scenes_dir(project_id)
        scenes_dir.mkdir(parents=True, exist_ok=True)

        # Generate ID from title
        scene_id = slugify(scene_data.title)
        if not scene_id:
            scene_id = f"scene-{datetime.utcnow().timestamp():.0f}"

        filepath = scenes_dir / f"{scene_id}.json"

        if filepath.exists():
            # Add timestamp to make unique
            scene_id = f"{scene_id}-{int(datetime.utcnow().timestamp())}"
            filepath = scenes_dir / f"{scene_id}.json"

        # Auto-assign scene_number if not provided
        scene_number = scene_data.scene_number
        if scene_number is None:
            # Count existing scenes in this chapter
            existing_count = 0
            for f in scenes_dir.glob("*.json"):
                try:
                    data = await read_json_file(f)
                    if data.get("chapter_id") == scene_data.chapter_id:
                        existing_count += 1
                except:
                    continue
            scene_number = existing_count + 1

        now = datetime.utcnow()
        scene = Scene(
            id=scene_id,
            title=scene_data.title,
            outline=scene_data.outline,
            chapter_id=scene_data.chapter_id,
            scene_number=scene_number,
            character_ids=scene_data.character_ids,
            world_context_ids=scene_data.world_context_ids,
            previous_scene_ids=scene_data.previous_scene_ids,
            tags=scene_data.tags,
            additional_notes=scene_data.additional_notes,
            tone=scene_data.tone,
            pov=scene_data.pov,
            target_length=scene_data.target_length,
            is_canon=False,
            prose=None,
            summary=None,
            created_at=now,
            updated_at=now
        )

        await write_json_file(filepath, scene.model_dump(mode='json'))
        return scene

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create scene: {str(e)}")


@router.get("/{scene_id}", response_model=Scene)
async def get_scene(project_id: str, scene_id: str):
    """
    Get a scene by ID.

    Args:
        project_id: Project ID
        scene_id: Scene ID

    Returns:
        Scene data

    Raises:
        HTTPException: If scene not found
    """
    ensure_project_exists(project_id)

    try:
        filepath = settings.scenes_dir(project_id) / f"{scene_id}.json"
        data = await read_json_file(filepath)
        return Scene.model_validate(data)

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[Scene])
async def list_scenes(project_id: str, chapter_id: Optional[str] = None):
    """
    List all scenes in a project, optionally filtered by chapter.

    Args:
        project_id: Project ID
        chapter_id: Optional chapter ID to filter by

    Returns:
        List of scenes sorted by scene_number
    """
    ensure_project_exists(project_id)

    try:
        scenes = []
        scenes_dir = settings.scenes_dir(project_id)

        if not scenes_dir.exists():
            return scenes

        for filepath in scenes_dir.glob("*.json"):
            try:
                data = await read_json_file(filepath)

                # Filter by chapter_id if provided
                if chapter_id is not None and data.get("chapter_id") != chapter_id:
                    continue

                scenes.append(Scene.model_validate(data))
            except Exception:
                continue  # Skip invalid files

        # Sort by chapter_id then scene_number
        scenes.sort(key=lambda s: (s.chapter_id or "", s.scene_number or 0))
        return scenes

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{scene_id}", response_model=Scene)
async def update_scene(project_id: str, scene_id: str, update: SceneUpdate):
    """
    Update a scene.

    Args:
        project_id: Project ID
        scene_id: Scene ID
        update: Fields to update

    Returns:
        Updated scene

    Raises:
        HTTPException: If scene not found or chapter not found
    """
    ensure_project_exists(project_id)

    # Validate new chapter_id if being changed
    if update.chapter_id is not None:
        validate_chapter_exists(project_id, update.chapter_id)

    try:
        filepath = settings.scenes_dir(project_id) / f"{scene_id}.json"
        data = await read_json_file(filepath)

        # Check if prose is being modified - backup first
        update_dict = update.model_dump(exclude_unset=True)
        if "prose" in update_dict and update_dict["prose"] is not None:
            current_prose = data.get("prose")
            # Only backup if there's existing prose and it's changing
            if current_prose and current_prose != update_dict["prose"]:
                await backup_scene(project_id, scene_id, reason="pre-edit")

        # Merge updates (only non-None fields)
        for key, value in update_dict.items():
            if value is not None:
                data[key] = value

        # Update timestamp
        data["updated_at"] = datetime.utcnow().isoformat()

        # Save back
        await write_json_file(filepath, data)
        return Scene.model_validate(data)

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{scene_id}")
async def delete_scene(project_id: str, scene_id: str):
    """
    Delete a scene.

    Args:
        project_id: Project ID
        scene_id: Scene ID

    Returns:
        Success message

    Raises:
        HTTPException: If scene not found
    """
    ensure_project_exists(project_id)

    try:
        # Backup before delete
        await backup_scene(project_id, scene_id, reason="pre-delete")

        filepath = settings.scenes_dir(project_id) / f"{scene_id}.json"
        await delete_file(filepath)
        return {"message": f"Scene {scene_id} deleted successfully"}

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{scene_id}/prose")
async def get_scene_prose(project_id: str, scene_id: str):
    """
    Get the prose for a scene (if it has been accepted as canon).

    Args:
        project_id: Project ID
        scene_id: Scene ID

    Returns:
        Scene prose and metadata

    Raises:
        HTTPException: If scene not found
    """
    ensure_project_exists(project_id)

    try:
        filepath = settings.scenes_dir(project_id) / f"{scene_id}.json"
        data = await read_json_file(filepath)

        word_count = 0
        prose = data.get("prose")
        original_prose = data.get("original_prose")
        edit_mode = data.get("edit_mode", False)

        # Count words from prose, or original_prose if in edit mode
        if prose:
            word_count = len(prose.split())
        elif original_prose:
            word_count = len(original_prose.split())

        return {
            "scene_id": scene_id,
            "title": data.get("title", "Untitled"),
            "is_canon": data.get("is_canon", False),
            "prose": prose,
            "original_prose": original_prose,
            "edit_mode": edit_mode,
            "summary": data.get("summary"),
            "word_count": word_count
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Edit Mode Models and Endpoints

class EditModeRequest(BaseModel):
    """Request to enable edit mode with imported prose."""
    prose: str = Field(..., description="The prose text to import for editing", min_length=1)


class EditModeResponse(BaseModel):
    """Response after enabling edit mode."""
    scene_id: str
    title: str
    edit_mode: bool
    original_prose: str
    word_count: int
    message: str


@router.post("/{scene_id}/edit-mode", response_model=EditModeResponse)
async def enable_edit_mode(project_id: str, scene_id: str, request: EditModeRequest):
    """
    Enable edit mode for a scene by importing existing prose.

    This sets the scene up for revision rather than generation from scratch.
    The imported prose becomes the "original" that will be critiqued and revised.

    Args:
        project_id: Project ID
        scene_id: Scene ID
        request: EditModeRequest with the prose to import

    Returns:
        EditModeResponse with updated scene info

    Raises:
        HTTPException: If scene not found or already has canon prose
    """
    ensure_project_exists(project_id)

    try:
        filepath = settings.scenes_dir(project_id) / f"{scene_id}.json"
        data = await read_json_file(filepath)

        # Check if scene already has canon prose
        if data.get("is_canon") and data.get("prose"):
            raise HTTPException(
                status_code=400,
                detail="Scene already has canon prose. Clear it first to enable edit mode."
            )

        # Enable edit mode
        now = datetime.utcnow()
        data["edit_mode"] = True
        data["original_prose"] = request.prose
        data["edit_mode_started_at"] = now.isoformat()
        data["updated_at"] = now.isoformat()

        # Save updated scene
        await write_json_file(filepath, data)

        word_count = len(request.prose.split())

        return EditModeResponse(
            scene_id=scene_id,
            title=data.get("title", "Untitled"),
            edit_mode=True,
            original_prose=request.prose,
            word_count=word_count,
            message=f"Edit mode enabled. {word_count} words imported. Ready for critique."
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{scene_id}/edit-mode")
async def disable_edit_mode(project_id: str, scene_id: str):
    """
    Disable edit mode and clear imported prose.

    Args:
        project_id: Project ID
        scene_id: Scene ID

    Returns:
        Success message

    Raises:
        HTTPException: If scene not found or not in edit mode
    """
    ensure_project_exists(project_id)

    try:
        filepath = settings.scenes_dir(project_id) / f"{scene_id}.json"
        data = await read_json_file(filepath)

        if not data.get("edit_mode"):
            raise HTTPException(status_code=400, detail="Scene is not in edit mode")

        # Disable edit mode
        data["edit_mode"] = False
        data["original_prose"] = None
        data["edit_mode_started_at"] = None
        data["updated_at"] = datetime.utcnow().isoformat()

        await write_json_file(filepath, data)

        return {"message": f"Edit mode disabled for scene {scene_id}"}

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Direct Selection Revision (for reading view)

class SelectionRevisionRequest(BaseModel):
    """Request to revise a selection of prose directly."""
    selection_start: int
    selection_end: int
    selection_text: str
    instructions: Optional[str] = None
    model: Optional[str] = None
    quick_action: Optional[str] = None  # e.g., "shorten", "lengthen", "rephrase"


class SelectionRevisionResponse(BaseModel):
    """Response after revising selection (not saved until explicit save)."""
    scene_id: str
    revised_selection: str  # Just the revised portion
    merged_prose: str  # Full prose with revision spliced in
    word_count: int
    message: str


class SaveProseRequest(BaseModel):
    """Request to save prose changes."""
    prose: str = Field(..., description="The full prose to save")


class SaveProseResponse(BaseModel):
    """Response after saving prose."""
    scene_id: str
    word_count: int
    backup_created: bool
    message: str


# Quick action mappings to instructions
QUICK_ACTION_INSTRUCTIONS = {
    "shorten": "Make this more concise. Reduce word count while preserving the essential meaning and impact.",
    "lengthen": "Expand this with more detail, description, or nuance. Add depth without padding.",
    "rephrase": "Rewrite this with different wording while keeping the same meaning and tone.",
    "more_vivid": "Make this more vivid with stronger sensory details and more evocative language.",
    "more_tension": "Increase the tension and suspense. Make it more gripping and urgent.",
    "simplify": "Simplify the language. Make it clearer and more accessible without losing meaning.",
}


@router.post("/{scene_id}/revise-selection", response_model=SelectionRevisionResponse)
async def revise_scene_selection(project_id: str, scene_id: str, request: SelectionRevisionRequest):
    """
    Revise a selected portion of scene prose directly using AI.

    Returns the revised text WITHOUT saving. Use save-prose endpoint to persist.
    This allows multiple revisions before committing changes.

    Args:
        project_id: Project ID
        scene_id: Scene ID
        request: Selection details, optional instructions/model/quick_action

    Returns:
        Revised selection and merged prose (not saved)

    Raises:
        HTTPException: If scene not found, is canon, or revision fails
    """
    ensure_project_exists(project_id)

    try:
        filepath = settings.scenes_dir(project_id) / f"{scene_id}.json"
        data = await read_json_file(filepath)

        # Check if scene is canon - require explicit un-marking first
        if data.get("is_canon"):
            raise HTTPException(
                status_code=400,
                detail="Cannot edit canon prose. Un-mark as canon first to enable editing."
            )

        current_prose = data.get("prose") or data.get("original_prose")
        if not current_prose:
            raise HTTPException(status_code=400, detail="Scene has no prose to revise")

        # NO backup here - backup happens on explicit save

        # Get LLM service
        from app.services.llm_service import get_llm_service

        llm = get_llm_service()

        # Build a simple system prompt for direct revision
        system_prompt = "You are a skilled prose editor. Revise the selected text while maintaining consistency with the surrounding context, narrative voice, and style."

        # Combine quick_action with custom instructions
        instructions = request.instructions or ""
        if request.quick_action and request.quick_action in QUICK_ACTION_INSTRUCTIONS:
            action_instruction = QUICK_ACTION_INSTRUCTIONS[request.quick_action]
            if instructions:
                instructions = f"{action_instruction} Additionally: {instructions}"
            else:
                instructions = action_instruction

        # Revise the selection
        revised_selection = await llm.revise_selection(
            full_prose=current_prose,
            selection=request.selection_text,
            selection_start=request.selection_start,
            selection_end=request.selection_end,
            system_prompt=system_prompt,
            critique=None,
            instructions=instructions if instructions else None,
            model=request.model
        )

        # Clean any AI preambles
        from app.utils.prompt_templates import clean_prose_output
        revised_selection = clean_prose_output(revised_selection)

        # Splice revised selection back into prose
        merged_prose = current_prose[:request.selection_start] + revised_selection + current_prose[request.selection_end:]

        # DO NOT save - return for preview only
        word_count = len(merged_prose.split())

        return SelectionRevisionResponse(
            scene_id=scene_id,
            revised_selection=revised_selection,
            merged_prose=merged_prose,
            word_count=word_count,
            message=f"Selection revised. Use Save to commit changes."
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{scene_id}/save-prose", response_model=SaveProseResponse)
async def save_scene_prose(project_id: str, scene_id: str, request: SaveProseRequest):
    """
    Save prose changes to a scene with automatic backup.

    This is the commit point after making revisions. Creates a backup
    of the previous version before saving.

    Args:
        project_id: Project ID
        scene_id: Scene ID
        request: The prose to save

    Returns:
        Confirmation with word count

    Raises:
        HTTPException: If scene not found or is canon
    """
    ensure_project_exists(project_id)

    try:
        filepath = settings.scenes_dir(project_id) / f"{scene_id}.json"
        data = await read_json_file(filepath)

        # Check if scene is canon - shouldn't happen but double-check
        if data.get("is_canon"):
            raise HTTPException(
                status_code=400,
                detail="Cannot save to canon scene. Un-mark as canon first."
            )

        # Check if there's existing prose to backup
        current_prose = data.get("prose") or data.get("original_prose")
        backup_created = False

        if current_prose and current_prose != request.prose:
            # Backup before overwriting
            await backup_scene(project_id, scene_id, reason="pre-edit")
            backup_created = True

        # Save the new prose
        data["prose"] = request.prose
        data["updated_at"] = datetime.utcnow().isoformat()

        await write_json_file(filepath, data)

        word_count = len(request.prose.split())

        return SaveProseResponse(
            scene_id=scene_id,
            word_count=word_count,
            backup_created=backup_created,
            message=f"Prose saved successfully. {word_count} words."
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Evaluate-Only Endpoint (critique without revision loop)

class EvaluateRequest(BaseModel):
    """Request for evaluate-only critique."""
    model: Optional[str] = Field(None, description="Optional critique model override")
    revision_mode: str = Field("full", description="'full' or 'polish' critique style")


class EvaluateResponse(BaseModel):
    """Response with critique only, no state changes."""
    scene_id: str
    title: str
    critique: str
    word_count: int
    revision_mode: str


@router.post("/{scene_id}/evaluate", response_model=EvaluateResponse)
async def evaluate_scene(project_id: str, scene_id: str, request: EvaluateRequest):
    """
    Get AI critique of a scene without entering revision loop.

    This is a read-only evaluation - no generation state is created,
    no changes are made to the scene. Just feedback.

    Args:
        project_id: Project ID
        scene_id: Scene ID
        request: EvaluateRequest with optional model and revision mode

    Returns:
        EvaluateResponse with the critique

    Raises:
        HTTPException: If scene not found or has no prose
    """
    ensure_project_exists(project_id)

    try:
        # Load scene
        filepath = settings.scenes_dir(project_id) / f"{scene_id}.json"
        data = await read_json_file(filepath)

        # Get prose (prefer prose, fall back to original_prose for edit mode)
        prose = data.get("prose") or data.get("original_prose")
        if not prose or not prose.strip():
            raise HTTPException(status_code=400, detail="Scene has no prose to evaluate")

        # Load style guide if available
        style_guide = None
        style_path = settings.project_dir(project_id) / "style.json"
        if style_path.exists():
            try:
                style_guide = await read_json_file(style_path)
            except:
                pass  # Style guide is optional

        # Get LLM service and run critique
        from app.services.llm_service import LLMService
        llm = LLMService()

        if request.revision_mode == "polish":
            critique = await llm.critique_prose_polish(
                prose=prose,
                model=request.model,
                style_guide=style_guide
            )
        else:
            critique = await llm.critique_prose(
                prose=prose,
                model=request.model,
                style_guide=style_guide
            )

        word_count = len(prose.split())

        return EvaluateResponse(
            scene_id=scene_id,
            title=data.get("title", "Untitled"),
            critique=critique,
            word_count=word_count,
            revision_mode=request.revision_mode
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")
