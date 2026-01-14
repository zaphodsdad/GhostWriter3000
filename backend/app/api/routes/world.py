"""World context management API endpoints (project-scoped)."""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from typing import List

from app.models.world import WorldContext, WorldContextCreate, WorldContextUpdate
from app.services.markdown_parser import MarkdownParser
from app.config import settings
from app.utils.file_utils import generate_id_from_filename

router = APIRouter()
parser = MarkdownParser()


def ensure_project_exists(project_id: str):
    """Check that project exists, raise 404 if not."""
    if not settings.project_dir(project_id).exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")


@router.get("/", response_model=List[WorldContext])
async def list_world_contexts(project_id: str):
    """
    List all world contexts in a project.

    Args:
        project_id: Project ID

    Returns:
        List of world contexts
    """
    ensure_project_exists(project_id)

    try:
        contexts = []
        world_dir = settings.world_dir(project_id)

        if not world_dir.exists():
            return contexts

        for filepath in world_dir.glob("*.md"):
            try:
                parsed = parser.parse_file(filepath)
                world_id = generate_id_from_filename(filepath.name)
                contexts.append(WorldContext(
                    id=world_id,
                    filename=filepath.name,
                    metadata=parsed["metadata"],
                    content=parsed["content"],
                    updated_at=datetime.fromtimestamp(filepath.stat().st_mtime)
                ))
            except Exception:
                continue  # Skip invalid files
        return contexts

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{world_id}", response_model=WorldContext)
async def get_world_context(project_id: str, world_id: str):
    """
    Get a world context by ID.

    Args:
        project_id: Project ID
        world_id: World context ID

    Returns:
        World context data

    Raises:
        HTTPException: If world context not found
    """
    ensure_project_exists(project_id)

    try:
        filepath = settings.world_dir(project_id) / f"{world_id}.md"
        parsed = parser.parse_file(filepath)
        return WorldContext(
            id=world_id,
            filename=filepath.name,
            metadata=parsed["metadata"],
            content=parsed["content"],
            updated_at=datetime.fromtimestamp(filepath.stat().st_mtime)
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"World context not found: {world_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=WorldContext)
async def create_world_context(project_id: str, world: WorldContextCreate):
    """
    Create a new world context in a project.

    Args:
        project_id: Project ID
        world: World context data

    Returns:
        Created world context

    Raises:
        HTTPException: If world context creation fails or already exists
    """
    ensure_project_exists(project_id)

    try:
        world_id = generate_id_from_filename(world.filename)
        world_dir = settings.world_dir(project_id)
        filepath = world_dir / world.filename

        # Ensure directory exists
        world_dir.mkdir(parents=True, exist_ok=True)

        # Check if file already exists
        if filepath.exists():
            raise HTTPException(status_code=409, detail=f"World context already exists: {world_id}")

        # Write the file
        parser.write_file(filepath, world.metadata, world.content)

        return WorldContext(
            id=world_id,
            filename=world.filename,
            metadata=world.metadata,
            content=world.content,
            updated_at=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create world context: {str(e)}")


@router.put("/{world_id}", response_model=WorldContext)
async def update_world_context(project_id: str, world_id: str, update: WorldContextUpdate):
    """
    Update a world context.

    Args:
        project_id: Project ID
        world_id: World context ID
        update: Fields to update

    Returns:
        Updated world context

    Raises:
        HTTPException: If world context not found
    """
    ensure_project_exists(project_id)

    try:
        filepath = settings.world_dir(project_id) / f"{world_id}.md"

        # Load existing
        existing = parser.parse_file(filepath)

        # Merge updates
        metadata = update.metadata if update.metadata is not None else existing["metadata"]
        content = update.content if update.content is not None else existing["content"]

        # Write back
        parser.write_file(filepath, metadata, content)

        return WorldContext(
            id=world_id,
            filename=filepath.name,
            metadata=metadata,
            content=content,
            updated_at=datetime.utcnow()
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"World context not found: {world_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{world_id}")
async def delete_world_context(project_id: str, world_id: str):
    """
    Delete a world context.

    Args:
        project_id: Project ID
        world_id: World context ID

    Returns:
        Success message

    Raises:
        HTTPException: If world context not found
    """
    ensure_project_exists(project_id)

    try:
        filepath = settings.world_dir(project_id) / f"{world_id}.md"

        if not filepath.exists():
            raise HTTPException(status_code=404, detail=f"World context not found: {world_id}")

        filepath.unlink()
        return {"message": f"World context {world_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
