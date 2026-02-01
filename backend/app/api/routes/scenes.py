"""Scene management API endpoints (project-scoped)."""

import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel, Field

from app.models.scene import Scene, SceneCreate, SceneUpdate, Beat, BeatCreate, BeatUpdate
from app.config import settings
from app.utils.file_utils import write_json_file, read_json_file, delete_file
from app.utils.backup import backup_scene
from app.services.memory_service import memory_service

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
async def update_scene(project_id: str, scene_id: str, update: SceneUpdate, background_tasks: BackgroundTasks):
    """
    Update a scene.

    Args:
        project_id: Project ID
        scene_id: Scene ID
        update: Fields to update
        background_tasks: FastAPI background tasks for async operations

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

        # Track if we're marking as canon (for memory extraction)
        was_canon = data.get("is_canon", False)
        marking_as_canon = update_dict.get("is_canon", False) and not was_canon

        # Merge updates (only non-None fields)
        for key, value in update_dict.items():
            if value is not None:
                data[key] = value

        # Update timestamp
        data["updated_at"] = datetime.utcnow().isoformat()

        # Save back
        await write_json_file(filepath, data)

        # If marking as canon and project belongs to a series, extract memory
        if marking_as_canon and data.get("prose"):
            await _trigger_memory_extraction(
                project_id, scene_id, data, background_tasks
            )

        return Scene.model_validate(data)

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _trigger_memory_extraction(
    project_id: str,
    scene_id: str,
    scene_data: dict,
    background_tasks: BackgroundTasks
):
    """
    Trigger memory extraction when a scene is marked as canon.

    Runs in background to not block the response.
    """
    # Get project info to find series_id
    project_file = settings.project_dir(project_id) / "project.json"
    if not project_file.exists():
        return

    project_data = await read_json_file(project_file)
    series_id = project_data.get("series_id")

    if not series_id:
        # Not in a series, skip extraction
        return

    # Get chapter info for context
    chapter_title = None
    chapter_number = None
    if scene_data.get("chapter_id"):
        chapter_file = settings.project_dir(project_id) / "chapters" / f"{scene_data['chapter_id']}.json"
        if chapter_file.exists():
            chapter_data = await read_json_file(chapter_file)
            chapter_title = chapter_data.get("title")
            chapter_number = chapter_data.get("order")

    # Get character names from series for better extraction
    character_names = []
    char_dir = settings.series_path(series_id) / "characters"
    if char_dir.exists():
        for char_file in char_dir.glob("*.md"):
            # Use filename as character name hint
            character_names.append(char_file.stem.replace("-", " ").title())

    # Run extraction in background
    background_tasks.add_task(
        _run_extraction,
        series_id,
        project_id,
        scene_id,
        scene_data,
        chapter_title,
        project_data.get("book_number"),
        chapter_number,
        character_names
    )


async def _run_extraction(
    series_id: str,
    project_id: str,
    scene_id: str,
    scene_data: dict,
    chapter_title: Optional[str],
    book_number: Optional[int],
    chapter_number: Optional[int],
    character_names: List[str]
):
    """Background task to run memory extraction."""
    try:
        await memory_service.extract_from_scene(
            series_id=series_id,
            book_id=project_id,
            scene_id=scene_id,
            prose=scene_data.get("prose", ""),
            scene_title=scene_data.get("title"),
            chapter_title=chapter_title,
            book_number=book_number,
            chapter_number=chapter_number,
            scene_number=scene_data.get("order"),
            character_names=character_names if character_names else None
        )
        print(f"Memory extraction completed for scene {scene_id}")
    except Exception as e:
        # Log but don't fail - extraction is non-critical
        print(f"Memory extraction failed for scene {scene_id}: {e}")


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
# IMPORTANT: All instructions include anti-AI-tell guidance to ensure human-quality output
QUICK_ACTION_INSTRUCTIONS = {
    "shorten": "Make this more concise. Reduce word count while preserving essential meaning. Do NOT use AI-tell vocabulary (delve, myriad, whilst, etc.).",
    "lengthen": "Expand with specific, concrete detail - not vague adjectives. Add depth through sensory specifics, not padding. Avoid AI vocabulary (delve, tapestry, myriad).",
    "rephrase": "Rewrite with different wording, same meaning and tone. Use natural vocabulary a human novelist would choose. Avoid: delve, whilst, myriad, tapestry, commence.",
    "more_vivid": "Sharpen with concrete sensory details - specific sights, sounds, textures. Avoid purple prose and AI-tell words (delve, tapestry, myriad). Precision beats decoration.",
    "more_tension": "Increase tension through pacing and stakes, not overwrought language. Short sentences. Specific details. No AI vocabulary (delve, whilst, tapestry).",
    "simplify": "Clarify with simpler, more direct language. Cut unnecessary words. Use strong verbs. Avoid formal AI patterns (furthermore, moreover, utilize, commence).",
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
        system_prompt = "You are a skilled prose editor. Revise the selected text while maintaining consistency with the surrounding context, narrative voice, and style. CRITICAL: Your output must read as human-written. Never use AI-tell vocabulary (delve, tapestry, myriad, whilst, amidst, commence, utilize, plethora). Write with the natural voice of a published novelist."

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

            # Learn from user edits (style preferences)
            try:
                # Get project to check for series
                project_file = settings.project_dir(project_id) / "project.json"
                if project_file.exists():
                    project_data = await read_json_file(project_file)
                    series_id = project_data.get("series_id")

                    if series_id:
                        from app.services.style_learning_service import get_style_learning_service
                        style_service = get_style_learning_service()

                        # Learn from the edit (background, don't block save)
                        import asyncio
                        asyncio.create_task(
                            style_service.learn_from_edit(
                                series_id=series_id,
                                scene_id=scene_id,
                                book_id=project_id,
                                original_text=current_prose,
                                edited_text=request.prose
                            )
                        )
            except Exception:
                # Style learning is optional, don't fail the save
                pass

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


# ==================== Beat CRUD Endpoints ====================
# Beats are planning artifacts within scenes for the Outline Module


class BeatListResponse(BaseModel):
    """Response for listing beats."""
    scene_id: str
    beats: List[Beat]
    count: int


class BeatResponse(BaseModel):
    """Response for single beat operations."""
    scene_id: str
    beat: Beat
    message: str


class ReorderBeatsRequest(BaseModel):
    """Request to reorder beats."""
    beat_ids: List[str] = Field(..., description="Beat IDs in desired order")


@router.get("/{scene_id}/beats", response_model=BeatListResponse)
async def list_beats(project_id: str, scene_id: str):
    """
    List all beats for a scene.

    Args:
        project_id: Project ID
        scene_id: Scene ID

    Returns:
        List of beats in order
    """
    ensure_project_exists(project_id)

    try:
        filepath = settings.scenes_dir(project_id) / f"{scene_id}.json"
        data = await read_json_file(filepath)

        beats = data.get("beats", [])
        # Ensure beats have proper structure
        beat_objects = [Beat(**b) if isinstance(b, dict) else b for b in beats]

        return BeatListResponse(
            scene_id=scene_id,
            beats=beat_objects,
            count=len(beat_objects)
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{scene_id}/beats", response_model=BeatResponse)
async def create_beat(project_id: str, scene_id: str, beat_data: BeatCreate):
    """
    Add a new beat to a scene.

    Args:
        project_id: Project ID
        scene_id: Scene ID
        beat_data: Beat data

    Returns:
        Created beat
    """
    ensure_project_exists(project_id)

    try:
        filepath = settings.scenes_dir(project_id) / f"{scene_id}.json"
        data = await read_json_file(filepath)

        beats = data.get("beats", [])

        # Generate beat ID
        beat_id = f"beat-{int(datetime.utcnow().timestamp() * 1000)}"

        # Determine order
        if beat_data.order is not None:
            order = beat_data.order
        else:
            # Append to end
            order = max([b.get("order", 0) for b in beats], default=-1) + 1

        # Create beat
        new_beat = Beat(
            id=beat_id,
            text=beat_data.text,
            notes=beat_data.notes,
            tags=beat_data.tags,
            order=order
        )

        # Add to beats list
        beats.append(new_beat.model_dump())

        # Sort by order
        beats.sort(key=lambda b: b.get("order", 0))

        # Update scene
        data["beats"] = beats
        data["updated_at"] = datetime.utcnow().isoformat()

        await write_json_file(filepath, data)

        return BeatResponse(
            scene_id=scene_id,
            beat=new_beat,
            message="Beat created successfully"
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{scene_id}/beats/{beat_id}", response_model=BeatResponse)
async def update_beat(project_id: str, scene_id: str, beat_id: str, beat_data: BeatUpdate):
    """
    Update an existing beat.

    Args:
        project_id: Project ID
        scene_id: Scene ID
        beat_id: Beat ID
        beat_data: Updated beat data

    Returns:
        Updated beat
    """
    ensure_project_exists(project_id)

    try:
        filepath = settings.scenes_dir(project_id) / f"{scene_id}.json"
        data = await read_json_file(filepath)

        beats = data.get("beats", [])

        # Find beat
        beat_index = None
        for i, b in enumerate(beats):
            if b.get("id") == beat_id:
                beat_index = i
                break

        if beat_index is None:
            raise HTTPException(status_code=404, detail=f"Beat not found: {beat_id}")

        # Update fields
        if beat_data.text is not None:
            beats[beat_index]["text"] = beat_data.text
        if beat_data.notes is not None:
            beats[beat_index]["notes"] = beat_data.notes
        if beat_data.tags is not None:
            beats[beat_index]["tags"] = beat_data.tags
        if beat_data.order is not None:
            beats[beat_index]["order"] = beat_data.order

        # Sort by order
        beats.sort(key=lambda b: b.get("order", 0))

        # Update scene
        data["beats"] = beats
        data["updated_at"] = datetime.utcnow().isoformat()

        await write_json_file(filepath, data)

        updated_beat = Beat(**beats[beat_index])

        return BeatResponse(
            scene_id=scene_id,
            beat=updated_beat,
            message="Beat updated successfully"
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{scene_id}/beats/{beat_id}")
async def delete_beat(project_id: str, scene_id: str, beat_id: str):
    """
    Delete a beat from a scene.

    Args:
        project_id: Project ID
        scene_id: Scene ID
        beat_id: Beat ID

    Returns:
        Deletion confirmation
    """
    ensure_project_exists(project_id)

    try:
        filepath = settings.scenes_dir(project_id) / f"{scene_id}.json"
        data = await read_json_file(filepath)

        beats = data.get("beats", [])

        # Find and remove beat
        original_count = len(beats)
        beats = [b for b in beats if b.get("id") != beat_id]

        if len(beats) == original_count:
            raise HTTPException(status_code=404, detail=f"Beat not found: {beat_id}")

        # Update scene
        data["beats"] = beats
        data["updated_at"] = datetime.utcnow().isoformat()

        await write_json_file(filepath, data)

        return {"message": f"Beat {beat_id} deleted", "scene_id": scene_id}

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{scene_id}/beats/reorder", response_model=BeatListResponse)
async def reorder_beats(project_id: str, scene_id: str, request: ReorderBeatsRequest):
    """
    Reorder beats within a scene.

    Args:
        project_id: Project ID
        scene_id: Scene ID
        request: New order of beat IDs

    Returns:
        Reordered beats list
    """
    ensure_project_exists(project_id)

    try:
        filepath = settings.scenes_dir(project_id) / f"{scene_id}.json"
        data = await read_json_file(filepath)

        beats = data.get("beats", [])

        # Create a map of beat_id -> beat
        beat_map = {b.get("id"): b for b in beats}

        # Verify all beat IDs exist
        for bid in request.beat_ids:
            if bid not in beat_map:
                raise HTTPException(status_code=400, detail=f"Beat not found: {bid}")

        # Reorder based on provided order
        reordered = []
        for i, bid in enumerate(request.beat_ids):
            beat = beat_map[bid]
            beat["order"] = i
            reordered.append(beat)

        # Add any beats not in the request (shouldn't happen but be safe)
        for beat in beats:
            if beat.get("id") not in request.beat_ids:
                beat["order"] = len(reordered)
                reordered.append(beat)

        # Update scene
        data["beats"] = reordered
        data["updated_at"] = datetime.utcnow().isoformat()

        await write_json_file(filepath, data)

        beat_objects = [Beat(**b) for b in reordered]

        return BeatListResponse(
            scene_id=scene_id,
            beats=beat_objects,
            count=len(beat_objects)
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
