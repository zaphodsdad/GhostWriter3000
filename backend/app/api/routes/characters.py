"""Character management API endpoints (project-scoped)."""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from typing import List

from app.models.character import Character, CharacterCreate, CharacterUpdate
from app.services.markdown_parser import MarkdownParser
from app.config import settings
from app.utils.file_utils import generate_id_from_filename

router = APIRouter()
parser = MarkdownParser()


def ensure_project_exists(project_id: str):
    """Check that project exists, raise 404 if not."""
    if not settings.project_dir(project_id).exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")


@router.get("/", response_model=List[Character])
async def list_characters(project_id: str):
    """
    List all characters in a project.

    Args:
        project_id: Project ID

    Returns:
        List of characters
    """
    ensure_project_exists(project_id)

    try:
        characters = []
        chars_dir = settings.characters_dir(project_id)

        if not chars_dir.exists():
            return characters

        for filepath in chars_dir.glob("*.md"):
            try:
                parsed = parser.parse_file(filepath)
                char_id = generate_id_from_filename(filepath.name)
                characters.append(Character(
                    id=char_id,
                    filename=filepath.name,
                    metadata=parsed["metadata"],
                    content=parsed["content"],
                    updated_at=datetime.fromtimestamp(filepath.stat().st_mtime)
                ))
            except Exception:
                continue  # Skip invalid files
        return characters

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{character_id}", response_model=Character)
async def get_character(project_id: str, character_id: str):
    """
    Get a character by ID.

    Args:
        project_id: Project ID
        character_id: Character ID

    Returns:
        Character data

    Raises:
        HTTPException: If character not found
    """
    ensure_project_exists(project_id)

    try:
        filepath = settings.characters_dir(project_id) / f"{character_id}.md"
        parsed = parser.parse_file(filepath)
        return Character(
            id=character_id,
            filename=filepath.name,
            metadata=parsed["metadata"],
            content=parsed["content"],
            updated_at=datetime.fromtimestamp(filepath.stat().st_mtime)
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Character not found: {character_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=Character)
async def create_character(project_id: str, character: CharacterCreate):
    """
    Create a new character in a project.

    Args:
        project_id: Project ID
        character: Character data

    Returns:
        Created character

    Raises:
        HTTPException: If character creation fails or already exists
    """
    ensure_project_exists(project_id)

    try:
        char_id = generate_id_from_filename(character.filename)
        chars_dir = settings.characters_dir(project_id)
        filepath = chars_dir / character.filename

        # Ensure directory exists
        chars_dir.mkdir(parents=True, exist_ok=True)

        # Check if file already exists
        if filepath.exists():
            raise HTTPException(status_code=409, detail=f"Character already exists: {char_id}")

        # Write the file
        parser.write_file(filepath, character.metadata, character.content)

        return Character(
            id=char_id,
            filename=character.filename,
            metadata=character.metadata,
            content=character.content,
            updated_at=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create character: {str(e)}")


@router.put("/{character_id}", response_model=Character)
async def update_character(project_id: str, character_id: str, update: CharacterUpdate):
    """
    Update a character.

    Args:
        project_id: Project ID
        character_id: Character ID
        update: Fields to update

    Returns:
        Updated character

    Raises:
        HTTPException: If character not found
    """
    ensure_project_exists(project_id)

    try:
        filepath = settings.characters_dir(project_id) / f"{character_id}.md"

        # Load existing
        existing = parser.parse_file(filepath)

        # Merge updates
        metadata = update.metadata if update.metadata is not None else existing["metadata"]
        content = update.content if update.content is not None else existing["content"]

        # Write back
        parser.write_file(filepath, metadata, content)

        return Character(
            id=character_id,
            filename=filepath.name,
            metadata=metadata,
            content=content,
            updated_at=datetime.utcnow()
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Character not found: {character_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{character_id}")
async def delete_character(project_id: str, character_id: str):
    """
    Delete a character.

    Args:
        project_id: Project ID
        character_id: Character ID

    Returns:
        Success message

    Raises:
        HTTPException: If character not found
    """
    ensure_project_exists(project_id)

    try:
        filepath = settings.characters_dir(project_id) / f"{character_id}.md"

        if not filepath.exists():
            raise HTTPException(status_code=404, detail=f"Character not found: {character_id}")

        filepath.unlink()
        return {"message": f"Character {character_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
