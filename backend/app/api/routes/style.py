"""Style guide API endpoints."""

from fastapi import APIRouter, HTTPException

from app.models.style import StyleGuide, StyleGuideUpdate
from app.utils.file_utils import read_json_file, write_json_file
from app.config import settings

router = APIRouter()


def get_style_path(project_id: str):
    """Get path to style guide file."""
    return settings.project_dir(project_id) / "style.json"


def ensure_project_exists(project_id: str):
    """Check that project exists, raise 404 if not."""
    if not settings.project_dir(project_id).exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")


@router.get("/", response_model=StyleGuide)
async def get_style_guide(project_id: str):
    """
    Get the style guide for a project.

    Returns empty style guide if none exists yet.
    """
    ensure_project_exists(project_id)

    style_path = get_style_path(project_id)

    if style_path.exists():
        try:
            data = await read_json_file(style_path)
            return StyleGuide.model_validate(data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading style guide: {str(e)}")

    # Return empty style guide if none exists
    return StyleGuide()


@router.put("/", response_model=StyleGuide)
async def update_style_guide(project_id: str, update: StyleGuideUpdate):
    """
    Update the style guide for a project.

    Creates the style guide if it doesn't exist.
    """
    ensure_project_exists(project_id)

    style_path = get_style_path(project_id)

    # Load existing or create new
    if style_path.exists():
        try:
            data = await read_json_file(style_path)
            style = StyleGuide.model_validate(data)
        except Exception:
            style = StyleGuide()
    else:
        style = StyleGuide()

    # Apply updates
    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(style, key, value)

    # Save
    try:
        await write_json_file(style_path, style.model_dump())
        return style
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving style guide: {str(e)}")


@router.delete("/")
async def clear_style_guide(project_id: str):
    """
    Clear/reset the style guide for a project.
    """
    ensure_project_exists(project_id)

    style_path = get_style_path(project_id)

    if style_path.exists():
        style_path.unlink()

    return {"message": "Style guide cleared"}
