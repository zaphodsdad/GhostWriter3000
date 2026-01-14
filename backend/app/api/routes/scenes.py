"""Scene management API endpoints (project-scoped)."""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from typing import List, Optional

from app.models.scene import Scene, SceneCreate, SceneUpdate
from app.config import settings
from app.utils.file_utils import write_json_file, read_json_file, delete_file

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

        # Merge updates (only non-None fields)
        update_dict = update.model_dump(exclude_unset=True)
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
        if data.get("prose"):
            word_count = len(data["prose"].split())

        return {
            "scene_id": scene_id,
            "title": data.get("title", "Untitled"),
            "is_canon": data.get("is_canon", False),
            "prose": data.get("prose"),
            "summary": data.get("summary"),
            "word_count": word_count
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
