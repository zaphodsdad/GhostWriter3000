"""Outline import API endpoints."""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from app.utils.outline_parser import parse_outline_markdown, validate_outline
from app.utils.file_utils import write_json_file, read_json_file
from app.config import settings

router = APIRouter()


class OutlineImportRequest(BaseModel):
    """Request to import an outline."""
    markdown: str = Field(..., description="Markdown outline text", min_length=10)
    preview_only: bool = Field(False, description="If true, only preview without saving")


class OutlineImportPreview(BaseModel):
    """Preview of what will be imported."""
    acts: List[Dict[str, Any]]
    chapters: List[Dict[str, Any]]
    scenes: List[Dict[str, Any]]
    warnings: List[str]


class OutlineImportResult(BaseModel):
    """Result of outline import."""
    acts_created: int
    chapters_created: int
    scenes_created: int
    warnings: List[str]


def ensure_project_exists(project_id: str):
    """Check that project exists, raise 404 if not."""
    if not settings.project_dir(project_id).exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")


@router.post("/preview", response_model=OutlineImportPreview)
async def preview_outline_import(project_id: str, request: OutlineImportRequest):
    """
    Preview what will be imported from the markdown outline.

    This parses the markdown but doesn't save anything.
    """
    ensure_project_exists(project_id)

    try:
        parsed = parse_outline_markdown(request.markdown)
        warnings = validate_outline(parsed)

        return OutlineImportPreview(
            acts=parsed['acts'],
            chapters=parsed['chapters'],
            scenes=parsed['scenes'],
            warnings=warnings
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse outline: {str(e)}")


@router.post("/import", response_model=OutlineImportResult)
async def import_outline(project_id: str, request: OutlineImportRequest):
    """
    Import an outline from markdown, creating acts, chapters, and scenes.
    """
    ensure_project_exists(project_id)

    try:
        parsed = parse_outline_markdown(request.markdown)
        warnings = validate_outline(parsed)

        if request.preview_only:
            return OutlineImportResult(
                acts_created=len(parsed['acts']),
                chapters_created=len(parsed['chapters']),
                scenes_created=len(parsed['scenes']),
                warnings=warnings
            )

        # Create acts
        acts_dir = settings.project_dir(project_id) / "acts"
        acts_dir.mkdir(parents=True, exist_ok=True)

        for act in parsed['acts']:
            act_data = {
                "id": act['id'],
                "title": act['title'],
                "act_number": act['act_number'],
                "description": act.get('description', ''),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            await write_json_file(acts_dir / f"{act['id']}.json", act_data)

        # Create chapters
        chapters_dir = settings.project_dir(project_id) / "chapters"
        chapters_dir.mkdir(parents=True, exist_ok=True)

        for chapter in parsed['chapters']:
            chapter_data = {
                "id": chapter['id'],
                "title": chapter['title'],
                "chapter_number": chapter['chapter_number'],
                "act_id": chapter.get('act_id'),
                "description": chapter.get('description', ''),
                "notes": None,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            await write_json_file(chapters_dir / f"{chapter['id']}.json", chapter_data)

        # Create scenes
        scenes_dir = settings.scenes_dir(project_id)
        scenes_dir.mkdir(parents=True, exist_ok=True)

        for scene in parsed['scenes']:
            scene_data = {
                "id": scene['id'],
                "title": scene['title'],
                "outline": scene.get('outline', ''),
                "chapter_id": scene.get('chapter_id'),
                "scene_number": scene.get('scene_number'),
                "character_ids": [],
                "world_context_ids": [],
                "previous_scene_ids": [],
                "tags": [],
                "additional_notes": None,
                "tone": None,
                "pov": None,
                "target_length": None,
                "is_canon": False,
                "prose": None,
                "summary": None,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            await write_json_file(scenes_dir / f"{scene['id']}.json", scene_data)

        return OutlineImportResult(
            acts_created=len(parsed['acts']),
            chapters_created=len(parsed['chapters']),
            scenes_created=len(parsed['scenes']),
            warnings=warnings
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import outline: {str(e)}")
