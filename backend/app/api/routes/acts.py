"""Act management API endpoints."""

import json
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException
from typing import List

from app.models.act import Act, ActCreate, ActUpdate, ActSummary
from app.config import settings

router = APIRouter()


def get_acts_dir(project_id: str) -> Path:
    """Get the acts directory for a project."""
    acts_dir = settings.project_dir(project_id) / "acts"
    acts_dir.mkdir(parents=True, exist_ok=True)
    return acts_dir


def get_chapters_dir(project_id: str) -> Path:
    """Get the chapters directory for a project."""
    return settings.project_dir(project_id) / "chapters"


def get_scenes_dir(project_id: str) -> Path:
    """Get the scenes directory for a project."""
    return settings.scenes_dir(project_id)


def count_chapters_in_act(project_id: str, act_id: str) -> int:
    """Count chapters belonging to an act."""
    chapters_dir = get_chapters_dir(project_id)
    if not chapters_dir.exists():
        return 0

    count = 0
    for filepath in chapters_dir.glob("*.json"):
        try:
            with open(filepath) as f:
                chapter = json.load(f)
                if chapter.get("act_id") == act_id:
                    count += 1
        except Exception:
            continue
    return count


def count_scenes_in_act(project_id: str, act_id: str) -> tuple[int, int]:
    """Count total scenes and canon scenes in an act."""
    chapters_dir = get_chapters_dir(project_id)
    scenes_dir = get_scenes_dir(project_id)

    if not chapters_dir.exists() or not scenes_dir.exists():
        return 0, 0

    # Get chapter IDs belonging to this act
    chapter_ids = set()
    for filepath in chapters_dir.glob("*.json"):
        try:
            with open(filepath) as f:
                chapter = json.load(f)
                if chapter.get("act_id") == act_id:
                    chapter_ids.add(chapter.get("id"))
        except Exception:
            continue

    # Count scenes in those chapters
    total = 0
    canon = 0
    for filepath in scenes_dir.glob("*.json"):
        try:
            with open(filepath) as f:
                scene = json.load(f)
                if scene.get("chapter_id") in chapter_ids:
                    total += 1
                    if scene.get("is_canon"):
                        canon += 1
        except Exception:
            continue

    return total, canon


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    import re
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text


@router.get("/", response_model=List[ActSummary])
async def list_acts(project_id: str):
    """
    List all acts in a project.

    Args:
        project_id: Project ID

    Returns:
        List of act summaries sorted by act_number
    """
    try:
        acts_dir = get_acts_dir(project_id)
        acts = []

        for filepath in acts_dir.glob("*.json"):
            try:
                with open(filepath) as f:
                    data = json.load(f)

                act_id = data.get("id", filepath.stem)
                scene_count, canon_count = count_scenes_in_act(project_id, act_id)

                acts.append(ActSummary(
                    id=act_id,
                    title=data.get("title", "Untitled"),
                    description=data.get("description"),
                    act_number=data.get("act_number", 1),
                    chapter_count=count_chapters_in_act(project_id, act_id),
                    scene_count=scene_count,
                    canon_scene_count=canon_count
                ))
            except Exception:
                continue

        acts.sort(key=lambda a: a.act_number)
        return acts

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{act_id}", response_model=Act)
async def get_act(project_id: str, act_id: str):
    """
    Get an act by ID.

    Args:
        project_id: Project ID
        act_id: Act ID

    Returns:
        Act data

    Raises:
        HTTPException: If act not found
    """
    try:
        acts_dir = get_acts_dir(project_id)
        filepath = acts_dir / f"{act_id}.json"

        if not filepath.exists():
            raise HTTPException(status_code=404, detail=f"Act not found: {act_id}")

        with open(filepath) as f:
            data = json.load(f)

        return Act(
            id=data.get("id", act_id),
            title=data.get("title", "Untitled"),
            description=data.get("description"),
            act_number=data.get("act_number", 1),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.utcnow().isoformat()))
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=Act)
async def create_act(project_id: str, act: ActCreate):
    """
    Create a new act.

    Args:
        project_id: Project ID
        act: Act data

    Returns:
        Created act
    """
    try:
        acts_dir = get_acts_dir(project_id)

        # Generate ID from title
        act_id = slugify(act.title)
        if not act_id:
            act_id = f"act-{datetime.utcnow().timestamp():.0f}"

        filepath = acts_dir / f"{act_id}.json"

        if filepath.exists():
            raise HTTPException(status_code=409, detail=f"Act already exists: {act_id}")

        # Auto-assign act_number if not provided
        act_number = act.act_number
        if act_number is None:
            existing_acts = list(acts_dir.glob("*.json"))
            act_number = len(existing_acts) + 1

        now = datetime.utcnow()
        act_data = {
            "id": act_id,
            "title": act.title,
            "description": act.description,
            "act_number": act_number,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }

        with open(filepath, "w") as f:
            json.dump(act_data, f, indent=2)

        return Act(
            id=act_id,
            title=act.title,
            description=act.description,
            act_number=act_number,
            created_at=now,
            updated_at=now
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create act: {str(e)}")


@router.put("/{act_id}", response_model=Act)
async def update_act(project_id: str, act_id: str, update: ActUpdate):
    """
    Update an act.

    Args:
        project_id: Project ID
        act_id: Act ID
        update: Fields to update

    Returns:
        Updated act
    """
    try:
        acts_dir = get_acts_dir(project_id)
        filepath = acts_dir / f"{act_id}.json"

        if not filepath.exists():
            raise HTTPException(status_code=404, detail=f"Act not found: {act_id}")

        with open(filepath) as f:
            data = json.load(f)

        if update.title is not None:
            data["title"] = update.title
        if update.description is not None:
            data["description"] = update.description
        if update.act_number is not None:
            data["act_number"] = update.act_number

        data["updated_at"] = datetime.utcnow().isoformat()

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        return Act(
            id=data["id"],
            title=data["title"],
            description=data.get("description"),
            act_number=data["act_number"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{act_id}")
async def delete_act(project_id: str, act_id: str):
    """
    Delete an act.

    Note: This will NOT delete chapters or scenes. They will become unassigned from the act.

    Args:
        project_id: Project ID
        act_id: Act ID

    Returns:
        Success message
    """
    try:
        acts_dir = get_acts_dir(project_id)
        filepath = acts_dir / f"{act_id}.json"

        if not filepath.exists():
            raise HTTPException(status_code=404, detail=f"Act not found: {act_id}")

        # Unassign chapters from this act
        chapters_dir = get_chapters_dir(project_id)
        if chapters_dir.exists():
            for chapter_file in chapters_dir.glob("*.json"):
                try:
                    with open(chapter_file) as f:
                        chapter = json.load(f)
                    if chapter.get("act_id") == act_id:
                        chapter["act_id"] = None
                        chapter["updated_at"] = datetime.utcnow().isoformat()
                        with open(chapter_file, "w") as f:
                            json.dump(chapter, f, indent=2)
                except Exception:
                    continue

        filepath.unlink()
        return {"message": f"Act {act_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
