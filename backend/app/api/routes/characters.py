"""Character management API endpoints (project-scoped)."""

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Any, Dict

from app.models.character import Character, CharacterCreate, CharacterUpdate
from app.services.markdown_parser import MarkdownParser
from app.services.llm_service import get_llm_service
from app.config import settings
from app.utils.file_utils import generate_id_from_filename
from app.utils.logging import get_logger

logger = get_logger(__name__)

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


# Portrait management
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_PORTRAIT_SIZE = 5 * 1024 * 1024  # 5MB


@router.post("/{character_id}/portrait")
async def upload_portrait(project_id: str, character_id: str, file: UploadFile = File(...)):
    """
    Upload a portrait image for a character.

    Args:
        project_id: Project ID
        character_id: Character ID
        file: Image file (JPEG, PNG, GIF, or WebP)

    Returns:
        Success message with portrait URL
    """
    ensure_project_exists(project_id)

    # Verify character exists
    char_file = settings.characters_dir(project_id) / f"{character_id}.md"
    if not char_file.exists():
        raise HTTPException(status_code=404, detail=f"Character not found: {character_id}")

    # Validate file type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: JPEG, PNG, GIF, WebP"
        )

    # Check file size
    file.file.seek(0, 2)  # Seek to end
    size = file.file.tell()
    file.file.seek(0)  # Reset
    if size > MAX_PORTRAIT_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 5MB")

    try:
        # Create portraits directory
        portraits_dir = settings.characters_dir(project_id) / "portraits"
        portraits_dir.mkdir(parents=True, exist_ok=True)

        # Determine file extension
        ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
        if ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            ext = ".jpg"

        # Save portrait
        portrait_path = portraits_dir / f"{character_id}{ext}"

        # Remove old portrait if exists (different extension)
        for old_file in portraits_dir.glob(f"{character_id}.*"):
            old_file.unlink()

        with open(portrait_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Update character metadata with portrait path
        parsed = parser.parse_file(char_file)
        parsed["metadata"]["portrait"] = f"{character_id}{ext}"
        parser.write_file(char_file, parsed["metadata"], parsed["content"])

        return {
            "message": "Portrait uploaded successfully",
            "portrait": f"{character_id}{ext}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Portrait upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{character_id}/portrait")
async def get_portrait(project_id: str, character_id: str):
    """
    Get a character's portrait image.

    Args:
        project_id: Project ID
        character_id: Character ID

    Returns:
        Portrait image file
    """
    ensure_project_exists(project_id)

    portraits_dir = settings.characters_dir(project_id) / "portraits"

    # Find portrait with any extension
    for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        portrait_path = portraits_dir / f"{character_id}{ext}"
        if portrait_path.exists():
            media_type = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp"
            }.get(ext, "image/jpeg")
            return FileResponse(portrait_path, media_type=media_type)

    raise HTTPException(status_code=404, detail="Portrait not found")


@router.delete("/{character_id}/portrait")
async def delete_portrait(project_id: str, character_id: str):
    """
    Delete a character's portrait.

    Args:
        project_id: Project ID
        character_id: Character ID

    Returns:
        Success message
    """
    ensure_project_exists(project_id)

    # Verify character exists
    char_file = settings.characters_dir(project_id) / f"{character_id}.md"
    if not char_file.exists():
        raise HTTPException(status_code=404, detail=f"Character not found: {character_id}")

    portraits_dir = settings.characters_dir(project_id) / "portraits"
    deleted = False

    # Find and delete portrait with any extension
    for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        portrait_path = portraits_dir / f"{character_id}{ext}"
        if portrait_path.exists():
            portrait_path.unlink()
            deleted = True

    if deleted:
        # Update character metadata to remove portrait
        parsed = parser.parse_file(char_file)
        if "portrait" in parsed["metadata"]:
            del parsed["metadata"]["portrait"]
            parser.write_file(char_file, parsed["metadata"], parsed["content"])

        return {"message": "Portrait deleted successfully"}

    raise HTTPException(status_code=404, detail="Portrait not found")


# AI-assisted character import models
class CharacterImportRequest(BaseModel):
    """Request to parse characters from text using AI."""
    text: str
    preview_only: bool = True


class ParsedCharacter(BaseModel):
    """A character extracted by AI."""
    name: str
    role: Optional[str] = None
    age: Optional[int] = None
    occupation: Optional[str] = None
    personality_traits: Optional[List[str]] = None
    background: Optional[str] = None
    goals: Optional[List[str]] = None
    fears: Optional[List[str]] = None
    relationships: Optional[str] = None
    additional_notes: Optional[str] = None


class CharacterImportResponse(BaseModel):
    """Response with parsed characters."""
    characters: List[ParsedCharacter]
    warnings: List[str] = []


class CharacterImportResult(BaseModel):
    """Result of importing characters."""
    imported: int
    failed: int
    errors: List[str] = []


@router.post("/import/parse", response_model=CharacterImportResponse)
async def parse_characters_with_ai(project_id: str, request: CharacterImportRequest):
    """
    Use AI to extract characters from unstructured text.

    Args:
        project_id: Project ID
        request: Text containing character descriptions

    Returns:
        Parsed characters ready for import
    """
    ensure_project_exists(project_id)

    if not request.text or len(request.text.strip()) < 20:
        raise HTTPException(status_code=400, detail="Text is too short to parse")

    llm = get_llm_service()

    system_prompt = """You are a character extraction assistant. Your job is to read text containing character descriptions and extract structured character data.

For each character you find, extract:
- name (required): The character's name
- role: Their role in the story (Protagonist, Antagonist, Supporting, Minor, etc.)
- age: Their age as a number (if mentioned)
- occupation: Their job or role in the world
- personality_traits: A list of personality traits
- background: Their backstory/history
- goals: A list of their goals or motivations
- fears: A list of their fears or weaknesses
- relationships: Key relationships with other characters
- additional_notes: Any other important details

Return ONLY a valid JSON array of character objects. No explanation, no markdown, just the JSON array.

Example output:
[
  {
    "name": "Elena Blackwood",
    "role": "Protagonist",
    "age": 28,
    "occupation": "Archaeologist",
    "personality_traits": ["Curious", "Determined", "Skeptical"],
    "background": "Born in London to academics...",
    "goals": ["Find her father", "Prove the lost civilization exists"],
    "fears": ["Failure", "Trusting the wrong people"],
    "relationships": "Sister to Marcus, mentored by Dr. Webb",
    "additional_notes": "Has a distinctive scar on her left hand"
  }
]

If a field is not mentioned, omit it from the output (don't include null values)."""

    user_prompt = f"""Extract all characters from the following text. Return ONLY the JSON array, nothing else.

TEXT:
{request.text}"""

    try:
        async with llm.semaphore:
            if llm.provider == "anthropic":
                response = await llm.client.messages.create(
                    model=settings.critique_model,  # Use faster model for parsing
                    max_tokens=4000,
                    temperature=0.1,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ],
                    system=system_prompt
                )
                response_text = response.content[0].text.strip()
            else:  # openrouter
                all_messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                response = await llm.client.chat.completions.create(
                    model=settings.critique_model,
                    max_tokens=4000,
                    temperature=0.1,
                    messages=all_messages
                )
                response_text = response.choices[0].message.content.strip()

        # Try to extract JSON from response
        # Handle potential markdown code blocks
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])

        characters_data = json.loads(response_text)

        if not isinstance(characters_data, list):
            characters_data = [characters_data]

        characters = []
        warnings = []

        for idx, char_data in enumerate(characters_data):
            if not char_data.get("name"):
                warnings.append(f"Character {idx + 1} has no name, skipping")
                continue

            # Normalize fields that might come in different formats
            relationships = char_data.get("relationships")
            if isinstance(relationships, dict):
                # Convert dict like {"Character": "relationship"} to string
                relationships = "; ".join(f"{k}: {v}" for k, v in relationships.items())

            # Handle age - might be string like "Late 20s" or int
            age = char_data.get("age")
            if age is not None:
                if isinstance(age, str):
                    # Try to extract a number, otherwise set to None
                    match = re.search(r'\d+', str(age))
                    age = int(match.group()) if match else None
                elif not isinstance(age, int):
                    age = None

            # Ensure list fields are actually lists
            def ensure_list(val):
                if val is None:
                    return None
                if isinstance(val, str):
                    return [val]
                return val

            characters.append(ParsedCharacter(
                name=char_data.get("name"),
                role=char_data.get("role"),
                age=age,
                occupation=char_data.get("occupation"),
                personality_traits=ensure_list(char_data.get("personality_traits")),
                background=char_data.get("background"),
                goals=ensure_list(char_data.get("goals")),
                fears=ensure_list(char_data.get("fears")),
                relationships=relationships,
                additional_notes=char_data.get("additional_notes")
            ))

        if len(characters) == 0:
            warnings.append("No characters could be extracted from the text")

        return CharacterImportResponse(characters=characters, warnings=warnings)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response as JSON: {e}")
        raise HTTPException(status_code=500, detail="AI returned invalid JSON. Try again or simplify the input.")
    except Exception as e:
        logger.error(f"Character parsing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import/confirm", response_model=CharacterImportResult)
async def confirm_character_import(project_id: str, characters: List[ParsedCharacter]):
    """
    Import parsed characters into the project.

    Args:
        project_id: Project ID
        characters: List of parsed characters to import

    Returns:
        Import result with counts
    """
    ensure_project_exists(project_id)

    imported = 0
    failed = 0
    errors = []

    chars_dir = settings.characters_dir(project_id)
    chars_dir.mkdir(parents=True, exist_ok=True)

    for char in characters:
        try:
            # Build metadata dict
            metadata = {"name": char.name}
            if char.role:
                metadata["role"] = char.role
            if char.age:
                metadata["age"] = char.age
            if char.occupation:
                metadata["occupation"] = char.occupation
            if char.personality_traits:
                metadata["personality_traits"] = char.personality_traits
            if char.background:
                metadata["background"] = char.background

            # Build content from remaining fields
            content_parts = []
            if char.goals:
                content_parts.append("## Goals\n" + "\n".join(f"- {g}" for g in char.goals))
            if char.fears:
                content_parts.append("## Fears\n" + "\n".join(f"- {f}" for f in char.fears))
            if char.relationships:
                content_parts.append(f"## Relationships\n{char.relationships}")
            if char.additional_notes:
                content_parts.append(f"## Additional Notes\n{char.additional_notes}")

            content = "\n\n".join(content_parts)

            # Generate filename from name
            char_id = char.name.lower().replace(" ", "-").replace("'", "")
            char_id = "".join(c for c in char_id if c.isalnum() or c == "-")
            filepath = chars_dir / f"{char_id}.md"

            # Check for existing
            counter = 1
            while filepath.exists():
                filepath = chars_dir / f"{char_id}-{counter}.md"
                counter += 1

            # Write file
            parser.write_file(filepath, metadata, content)
            imported += 1

        except Exception as e:
            failed += 1
            errors.append(f"{char.name}: {str(e)}")

    return CharacterImportResult(imported=imported, failed=failed, errors=errors)
