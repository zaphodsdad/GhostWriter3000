"""Outline import API endpoints."""

from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from app.utils.outline_parser import parse_outline_markdown, validate_outline
from app.utils.file_utils import write_json_file, read_json_file
from app.services.markdown_parser import MarkdownParser
from app.config import settings

router = APIRouter()
parser = MarkdownParser()


class OutlineImportRequest(BaseModel):
    """Request to import an outline."""
    markdown: str = Field(..., description="Markdown outline text", min_length=10)
    preview_only: bool = Field(False, description="If true, only preview without saving")
    create_character_stubs: bool = Field(True, description="Create placeholder characters for new character IDs")


class CharacterStub(BaseModel):
    """A character stub parsed from the outline."""
    id: str
    name: str
    role: Optional[str] = None
    description: Optional[str] = None
    voice: Optional[str] = None
    first_appearance: Optional[str] = None
    exists: bool = False  # True if character already exists in project/series


class OutlineImportPreview(BaseModel):
    """Preview of what will be imported."""
    book_metadata: Dict[str, Any] = {}
    acts: List[Dict[str, Any]]
    chapters: List[Dict[str, Any]]
    scenes: List[Dict[str, Any]]
    characters: List[CharacterStub]
    warnings: List[str]


class OutlineImportResult(BaseModel):
    """Result of outline import."""
    acts_created: int
    chapters_created: int
    scenes_created: int
    characters_created: int
    warnings: List[str]


def ensure_project_exists(project_id: str):
    """Check that project exists, raise 404 if not."""
    if not settings.project_dir(project_id).exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")


def get_project_series_id(project_id: str) -> Optional[str]:
    """Get the series_id for a project if it belongs to one."""
    project_file = settings.project_dir(project_id) / "project.json"
    if project_file.exists():
        try:
            import json
            with open(project_file) as f:
                project_data = json.load(f)
            return project_data.get('series_id')
        except Exception:
            pass
    return None


def character_exists(project_id: str, char_id: str) -> bool:
    """Check if a character exists in the project or its series."""
    # Check project characters
    char_file = settings.characters_dir(project_id) / f"{char_id}.md"
    if char_file.exists():
        return True

    # Check series characters if project belongs to a series
    series_id = get_project_series_id(project_id)
    if series_id:
        series_char_file = settings.series_characters_dir(series_id) / f"{char_id}.md"
        if series_char_file.exists():
            return True

    return False


def collect_all_character_ids(parsed: Dict[str, Any]) -> List[str]:
    """Collect all unique character IDs referenced in scenes."""
    char_ids = set()

    # From scenes' character_ids
    for scene in parsed['scenes']:
        for char_id in scene.get('character_ids', []):
            char_ids.add(char_id)

    # From explicit character definitions
    for char in parsed['characters']:
        char_ids.add(char['id'])

    return list(char_ids)


def create_character_stub_file(project_id: str, char_data: Dict[str, Any]) -> None:
    """Create a placeholder character markdown file."""
    chars_dir = settings.characters_dir(project_id)
    chars_dir.mkdir(parents=True, exist_ok=True)

    char_id = char_data['id']
    filepath = chars_dir / f"{char_id}.md"

    # Build metadata
    metadata = {
        'name': char_data.get('name', char_id.replace('-', ' ').title()),
        'role': char_data.get('role', 'Unknown'),
        'placeholder': True  # Mark as placeholder for easy identification
    }

    # Build content
    content_parts = []
    if char_data.get('description'):
        content_parts.append(f"## Description\n{char_data['description']}")
    if char_data.get('voice'):
        content_parts.append(f"## Voice\n{char_data['voice']}")
    if char_data.get('first_appearance'):
        content_parts.append(f"## First Appearance\n{char_data['first_appearance']}")

    if not content_parts:
        content_parts.append("## Notes\n*This is a placeholder character. Fill in details as needed.*")

    content = "\n\n".join(content_parts)

    parser.write_file(filepath, metadata, content)


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

        # Build character stubs with existence check
        all_char_ids = collect_all_character_ids(parsed)
        char_stubs = []

        # Create a lookup for parsed character data
        parsed_char_data = {c['id']: c for c in parsed['characters']}

        for char_id in all_char_ids:
            exists = character_exists(project_id, char_id)
            char_data = parsed_char_data.get(char_id, {'id': char_id, 'name': char_id})

            char_stubs.append(CharacterStub(
                id=char_id,
                name=char_data.get('name', char_id),
                role=char_data.get('role'),
                description=char_data.get('description'),
                voice=char_data.get('voice'),
                first_appearance=char_data.get('first_appearance'),
                exists=exists
            ))

        return OutlineImportPreview(
            book_metadata=parsed.get('book_metadata', {}),
            acts=parsed['acts'],
            chapters=parsed['chapters'],
            scenes=parsed['scenes'],
            characters=char_stubs,
            warnings=warnings
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse outline: {str(e)}")


@router.post("/import", response_model=OutlineImportResult)
async def import_outline(project_id: str, request: OutlineImportRequest):
    """
    Import an outline from markdown, creating acts, chapters, scenes, and character stubs.
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
                characters_created=0,
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
                "function": act.get('function'),
                "target_word_count": act.get('target_word_count'),
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
                "pov_pattern": chapter.get('pov_pattern'),
                "target_word_count": chapter.get('target_word_count'),
                "function": chapter.get('function'),
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
                "character_ids": scene.get('character_ids', []),
                "world_context_ids": [],
                "previous_scene_ids": [],
                "tags": scene.get('tags', []),
                "additional_notes": None,
                "tone": scene.get('tone'),
                "pov": scene.get('pov'),
                "target_length": scene.get('target_length'),
                # Enhanced fields
                "heat_level": scene.get('heat_level'),
                "emotional_arc": scene.get('emotional_arc'),
                "setting": scene.get('setting'),
                "generation_notes": scene.get('generation_notes'),
                # Beats
                "beats": scene.get('beats', []),
                "depends_on": [],
                "outline_status": "ready",  # Parsed outlines are ready
                # Status
                "is_canon": False,
                "prose": None,
                "summary": None,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            await write_json_file(scenes_dir / f"{scene['id']}.json", scene_data)

        # Create character stubs if enabled
        characters_created = 0
        if request.create_character_stubs:
            all_char_ids = collect_all_character_ids(parsed)
            parsed_char_data = {c['id']: c for c in parsed['characters']}

            for char_id in all_char_ids:
                if not character_exists(project_id, char_id):
                    char_data = parsed_char_data.get(char_id, {'id': char_id, 'name': char_id})
                    char_data['id'] = char_id  # Ensure ID is set
                    create_character_stub_file(project_id, char_data)
                    characters_created += 1

        return OutlineImportResult(
            acts_created=len(parsed['acts']),
            chapters_created=len(parsed['chapters']),
            scenes_created=len(parsed['scenes']),
            characters_created=characters_created,
            warnings=warnings
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import outline: {str(e)}")
