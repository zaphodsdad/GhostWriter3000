"""Chapter management API endpoints."""

import json
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException
from typing import List, Optional

from app.models.chapter import Chapter, ChapterCreate, ChapterUpdate, ChapterSummary
from app.config import settings

router = APIRouter()


def get_chapters_dir(project_id: str) -> Path:
    """Get the chapters directory for a project."""
    chapters_dir = settings.project_dir(project_id) / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    return chapters_dir


def get_scenes_dir(project_id: str) -> Path:
    """Get the scenes directory for a project."""
    return settings.scenes_dir(project_id)


def count_scenes_in_chapter(project_id: str, chapter_id: str) -> tuple[int, int, int]:
    """Count total scenes, canon scenes, and word count in a chapter."""
    scenes_dir = get_scenes_dir(project_id)

    if not scenes_dir.exists():
        return 0, 0, 0

    total = 0
    canon = 0
    word_count = 0

    for filepath in scenes_dir.glob("*.json"):
        try:
            with open(filepath) as f:
                scene = json.load(f)
                if scene.get("chapter_id") == chapter_id:
                    total += 1
                    if scene.get("is_canon"):
                        canon += 1
                        prose = scene.get("prose", "")
                        if prose:
                            word_count += len(prose.split())
        except Exception:
            continue

    return total, canon, word_count


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    import re
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text


@router.get("/", response_model=List[ChapterSummary])
async def list_chapters(project_id: str, act_id: Optional[str] = None):
    """
    List all chapters in a project, optionally filtered by act.

    Args:
        project_id: Project ID
        act_id: Optional act ID to filter by

    Returns:
        List of chapter summaries sorted by chapter_number
    """
    try:
        chapters_dir = get_chapters_dir(project_id)
        chapters = []

        for filepath in chapters_dir.glob("*.json"):
            try:
                with open(filepath) as f:
                    data = json.load(f)

                # Filter by act_id if provided
                if act_id is not None and data.get("act_id") != act_id:
                    continue

                chapter_id = data.get("id", filepath.stem)
                scene_count, canon_count, word_count = count_scenes_in_chapter(project_id, chapter_id)

                chapters.append(ChapterSummary(
                    id=chapter_id,
                    title=data.get("title", "Untitled"),
                    description=data.get("description"),
                    chapter_number=data.get("chapter_number", 1),
                    act_id=data.get("act_id"),
                    scene_count=scene_count,
                    canon_scene_count=canon_count,
                    word_count=word_count
                ))
            except Exception:
                continue

        chapters.sort(key=lambda c: c.chapter_number)
        return chapters

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{chapter_id}", response_model=Chapter)
async def get_chapter(project_id: str, chapter_id: str):
    """
    Get a chapter by ID.

    Args:
        project_id: Project ID
        chapter_id: Chapter ID

    Returns:
        Chapter data

    Raises:
        HTTPException: If chapter not found
    """
    try:
        chapters_dir = get_chapters_dir(project_id)
        filepath = chapters_dir / f"{chapter_id}.json"

        if not filepath.exists():
            raise HTTPException(status_code=404, detail=f"Chapter not found: {chapter_id}")

        with open(filepath) as f:
            data = json.load(f)

        return Chapter(
            id=data.get("id", chapter_id),
            title=data.get("title", "Untitled"),
            description=data.get("description"),
            notes=data.get("notes"),
            chapter_number=data.get("chapter_number", 1),
            act_id=data.get("act_id"),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.utcnow().isoformat()))
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=Chapter)
async def create_chapter(project_id: str, chapter: ChapterCreate):
    """
    Create a new chapter.

    Args:
        project_id: Project ID
        chapter: Chapter data

    Returns:
        Created chapter
    """
    try:
        chapters_dir = get_chapters_dir(project_id)

        # Generate ID from title
        chapter_id = slugify(chapter.title)
        if not chapter_id:
            chapter_id = f"chapter-{datetime.utcnow().timestamp():.0f}"

        filepath = chapters_dir / f"{chapter_id}.json"

        if filepath.exists():
            raise HTTPException(status_code=409, detail=f"Chapter already exists: {chapter_id}")

        # Validate act_id if provided
        if chapter.act_id:
            acts_dir = settings.project_dir(project_id) / "acts"
            act_file = acts_dir / f"{chapter.act_id}.json"
            if not act_file.exists():
                raise HTTPException(status_code=400, detail=f"Act not found: {chapter.act_id}")

        # Auto-assign chapter_number if not provided
        chapter_number = chapter.chapter_number
        if chapter_number is None:
            existing_chapters = list(chapters_dir.glob("*.json"))
            chapter_number = len(existing_chapters) + 1

        now = datetime.utcnow()
        chapter_data = {
            "id": chapter_id,
            "title": chapter.title,
            "description": chapter.description,
            "notes": chapter.notes,
            "chapter_number": chapter_number,
            "act_id": chapter.act_id,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }

        with open(filepath, "w") as f:
            json.dump(chapter_data, f, indent=2)

        return Chapter(
            id=chapter_id,
            title=chapter.title,
            description=chapter.description,
            notes=chapter.notes,
            chapter_number=chapter_number,
            act_id=chapter.act_id,
            created_at=now,
            updated_at=now
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create chapter: {str(e)}")


@router.put("/{chapter_id}", response_model=Chapter)
async def update_chapter(project_id: str, chapter_id: str, update: ChapterUpdate):
    """
    Update a chapter.

    Args:
        project_id: Project ID
        chapter_id: Chapter ID
        update: Fields to update

    Returns:
        Updated chapter
    """
    try:
        chapters_dir = get_chapters_dir(project_id)
        filepath = chapters_dir / f"{chapter_id}.json"

        if not filepath.exists():
            raise HTTPException(status_code=404, detail=f"Chapter not found: {chapter_id}")

        with open(filepath) as f:
            data = json.load(f)

        if update.title is not None:
            data["title"] = update.title
        if update.description is not None:
            data["description"] = update.description
        if update.notes is not None:
            data["notes"] = update.notes
        if update.chapter_number is not None:
            data["chapter_number"] = update.chapter_number
        if update.act_id is not None:
            # Validate act_id
            if update.act_id:
                acts_dir = settings.project_dir(project_id) / "acts"
                act_file = acts_dir / f"{update.act_id}.json"
                if not act_file.exists():
                    raise HTTPException(status_code=400, detail=f"Act not found: {update.act_id}")
            data["act_id"] = update.act_id

        data["updated_at"] = datetime.utcnow().isoformat()

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        return Chapter(
            id=data["id"],
            title=data["title"],
            description=data.get("description"),
            notes=data.get("notes"),
            chapter_number=data["chapter_number"],
            act_id=data.get("act_id"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{chapter_id}")
async def delete_chapter(project_id: str, chapter_id: str):
    """
    Delete a chapter.

    Note: This will fail if there are scenes assigned to this chapter.
    Move or delete scenes first.

    Args:
        project_id: Project ID
        chapter_id: Chapter ID

    Returns:
        Success message
    """
    try:
        chapters_dir = get_chapters_dir(project_id)
        filepath = chapters_dir / f"{chapter_id}.json"

        if not filepath.exists():
            raise HTTPException(status_code=404, detail=f"Chapter not found: {chapter_id}")

        # Check if there are scenes in this chapter
        scene_count, _, _ = count_scenes_in_chapter(project_id, chapter_id)
        if scene_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete chapter with {scene_count} scene(s). Move or delete scenes first."
            )

        filepath.unlink()
        return {"message": f"Chapter {chapter_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{chapter_id}/prose")
async def get_chapter_prose(project_id: str, chapter_id: str):
    """
    Get concatenated prose for all canon scenes in a chapter.

    Args:
        project_id: Project ID
        chapter_id: Chapter ID

    Returns:
        Chapter title and concatenated prose from all canon scenes
    """
    try:
        # Get chapter info
        chapters_dir = get_chapters_dir(project_id)
        chapter_file = chapters_dir / f"{chapter_id}.json"

        if not chapter_file.exists():
            raise HTTPException(status_code=404, detail=f"Chapter not found: {chapter_id}")

        with open(chapter_file) as f:
            chapter_data = json.load(f)

        # Get all scenes in this chapter
        scenes_dir = get_scenes_dir(project_id)
        scenes = []

        if scenes_dir.exists():
            for filepath in scenes_dir.glob("*.json"):
                try:
                    with open(filepath) as f:
                        scene = json.load(f)
                        if scene.get("chapter_id") == chapter_id and scene.get("is_canon"):
                            scenes.append(scene)
                except Exception:
                    continue

        # Sort by scene_number
        scenes.sort(key=lambda s: s.get("scene_number") or 0)

        # Concatenate prose
        prose_parts = []
        for scene in scenes:
            if scene.get("prose"):
                prose_parts.append(scene["prose"])

        return {
            "chapter_id": chapter_id,
            "chapter_title": chapter_data.get("title", "Untitled"),
            "chapter_number": chapter_data.get("chapter_number", 1),
            "scene_count": len(scenes),
            "word_count": sum(len(p.split()) for p in prose_parts),
            "prose": "\n\n---\n\n".join(prose_parts) if prose_parts else None
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
