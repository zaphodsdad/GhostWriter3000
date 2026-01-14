"""Project management API endpoints."""

import json
import re
from datetime import datetime
from fastapi import APIRouter, HTTPException
from typing import List

from app.models.project import Project, ProjectCreate, ProjectUpdate, ProjectSummary
from app.config import settings
from app.utils.file_utils import read_json_file, write_json_file
from typing import Optional

router = APIRouter()


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text


def count_files(directory, pattern: str) -> int:
    """Count files matching pattern in directory."""
    if not directory.exists():
        return 0
    return len(list(directory.glob(pattern)))


def count_canon_scenes(project_id: str) -> int:
    """Count scenes marked as canon in a project."""
    scenes_dir = settings.scenes_dir(project_id)
    if not scenes_dir.exists():
        return 0

    count = 0
    for filepath in scenes_dir.glob("*.json"):
        try:
            with open(filepath) as f:
                scene = json.load(f)
                if scene.get("is_canon"):
                    count += 1
        except Exception:
            continue
    return count


@router.get("/", response_model=List[ProjectSummary])
async def list_projects():
    """
    List all projects with summary stats.

    Returns:
        List of project summaries
    """
    try:
        projects = []

        if not settings.projects_dir.exists():
            return projects

        for project_dir in settings.projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            project_file = project_dir / "project.json"
            if not project_file.exists():
                continue

            try:
                with open(project_file) as f:
                    data = json.load(f)

                project_id = project_dir.name
                projects.append(ProjectSummary(
                    id=project_id,
                    title=data.get("title", project_id),
                    description=data.get("description"),
                    genre=data.get("genre"),
                    series_id=data.get("series_id"),
                    book_number=data.get("book_number"),
                    character_count=count_files(settings.characters_dir(project_id), "*.md"),
                    world_count=count_files(settings.world_dir(project_id), "*.md"),
                    scene_count=count_files(settings.scenes_dir(project_id), "*.json"),
                    canon_scene_count=count_canon_scenes(project_id),
                    created_at=datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat())),
                    updated_at=datetime.fromisoformat(data.get("updated_at", datetime.utcnow().isoformat()))
                ))
            except Exception:
                continue

        # Sort by updated_at descending
        projects.sort(key=lambda p: p.updated_at, reverse=True)
        return projects

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: str):
    """
    Get a project by ID.

    Args:
        project_id: Project ID (slug)

    Returns:
        Project data

    Raises:
        HTTPException: If project not found
    """
    try:
        project_file = settings.project_dir(project_id) / "project.json"

        if not project_file.exists():
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

        with open(project_file) as f:
            data = json.load(f)

        return Project(
            id=project_id,
            title=data.get("title", project_id),
            description=data.get("description"),
            author=data.get("author"),
            genre=data.get("genre"),
            series_id=data.get("series_id"),
            book_number=data.get("book_number"),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.utcnow().isoformat()))
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=Project)
async def create_project(project: ProjectCreate):
    """
    Create a new project.

    Args:
        project: Project data

    Returns:
        Created project

    Raises:
        HTTPException: If project creation fails or already exists
    """
    try:
        # Generate slug from title
        project_id = slugify(project.title)

        if not project_id:
            raise HTTPException(status_code=400, detail="Invalid project title")

        project_dir = settings.project_dir(project_id)

        # Check if project already exists
        if project_dir.exists():
            raise HTTPException(status_code=409, detail=f"Project already exists: {project_id}")

        # Create project directory structure
        project_dir.mkdir(parents=True)
        settings.characters_dir(project_id).mkdir()
        settings.world_dir(project_id).mkdir()
        settings.scenes_dir(project_id).mkdir()
        settings.generations_dir(project_id).mkdir()

        # Create project.json
        now = datetime.utcnow()
        project_data = {
            "id": project_id,
            "title": project.title,
            "description": project.description,
            "author": project.author,
            "genre": project.genre,
            "series_id": project.series_id,
            "book_number": project.book_number,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }

        project_file = project_dir / "project.json"
        with open(project_file, "w") as f:
            json.dump(project_data, f, indent=2)

        return Project(
            id=project_id,
            title=project.title,
            description=project.description,
            author=project.author,
            genre=project.genre,
            series_id=project.series_id,
            book_number=project.book_number,
            created_at=now,
            updated_at=now
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")


@router.put("/{project_id}", response_model=Project)
async def update_project(project_id: str, update: ProjectUpdate):
    """
    Update a project.

    Args:
        project_id: Project ID
        update: Fields to update

    Returns:
        Updated project

    Raises:
        HTTPException: If project not found
    """
    try:
        project_file = settings.project_dir(project_id) / "project.json"

        if not project_file.exists():
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

        # Load existing
        with open(project_file) as f:
            data = json.load(f)

        # Merge updates
        if update.title is not None:
            data["title"] = update.title
        if update.description is not None:
            data["description"] = update.description
        if update.author is not None:
            data["author"] = update.author
        if update.genre is not None:
            data["genre"] = update.genre

        data["updated_at"] = datetime.utcnow().isoformat()

        # Write back
        with open(project_file, "w") as f:
            json.dump(data, f, indent=2)

        return Project(
            id=project_id,
            title=data["title"],
            description=data.get("description"),
            author=data.get("author"),
            genre=data.get("genre"),
            series_id=data.get("series_id"),
            book_number=data.get("book_number"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}/structure")
async def clear_project_structure(project_id: str):
    """
    Clear all acts, chapters, and scenes from a project.

    Keeps the project itself, plus characters, world, style, and references.
    Use this to re-import an outline cleanly.

    Args:
        project_id: Project ID

    Returns:
        Summary of what was deleted
    """
    project_path = settings.project_dir(project_id)
    if not project_path.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    deleted = {"acts": 0, "chapters": 0, "scenes": 0, "generations": 0}

    # Delete all scenes
    scenes_dir = settings.scenes_dir(project_id)
    if scenes_dir.exists():
        for f in scenes_dir.glob("*.json"):
            f.unlink()
            deleted["scenes"] += 1

    # Delete all chapters
    chapters_dir = settings.chapters_dir(project_id)
    if chapters_dir.exists():
        for f in chapters_dir.glob("*.json"):
            f.unlink()
            deleted["chapters"] += 1

    # Delete all acts
    acts_dir = settings.acts_dir(project_id)
    if acts_dir.exists():
        for f in acts_dir.glob("*.json"):
            f.unlink()
            deleted["acts"] += 1

    # Delete all generations
    generations_dir = settings.generations_dir(project_id)
    if generations_dir.exists():
        for f in generations_dir.glob("*.json"):
            f.unlink()
            deleted["generations"] += 1

    return {
        "message": "Project structure cleared",
        "deleted": deleted
    }


from pydantic import BaseModel

class MoveToSeriesRequest(BaseModel):
    series_id: Optional[str] = None
    book_number: Optional[int] = None


@router.put("/{project_id}/series")
async def update_project_series(project_id: str, request: MoveToSeriesRequest):
    """
    Move a project into or out of a series.

    Args:
        project_id: Project ID
        request: Series ID and book number

    Returns:
        Updated project
    """
    project_path = settings.project_dir(project_id) / "project.json"
    if not project_path.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    # Validate series exists if provided
    if request.series_id:
        series_path = settings.series_path(request.series_id) / "series.json"
        if not series_path.exists():
            raise HTTPException(status_code=404, detail=f"Series not found: {request.series_id}")

    # Load and update project
    data = await read_json_file(project_path)
    old_series_id = data.get("series_id")

    data["series_id"] = request.series_id
    data["book_number"] = request.book_number if request.series_id else None
    data["updated_at"] = datetime.utcnow().isoformat()

    await write_json_file(project_path, data)

    # Update series project lists
    if old_series_id and old_series_id != request.series_id:
        # Remove from old series
        old_series_path = settings.series_path(old_series_id) / "series.json"
        if old_series_path.exists():
            series_data = await read_json_file(old_series_path)
            if project_id in series_data.get("project_ids", []):
                series_data["project_ids"].remove(project_id)
                await write_json_file(old_series_path, series_data)

    if request.series_id:
        # Add to new series
        series_path = settings.series_path(request.series_id) / "series.json"
        series_data = await read_json_file(series_path)
        if project_id not in series_data.get("project_ids", []):
            series_data["project_ids"].append(project_id)
            await write_json_file(series_path, series_data)

    return {
        "message": f"Project moved to series" if request.series_id else "Project removed from series",
        "project_id": project_id,
        "series_id": request.series_id,
        "book_number": request.book_number
    }


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """
    Delete a project and all its contents.

    Args:
        project_id: Project ID

    Returns:
        Success message

    Raises:
        HTTPException: If project not found
    """
    import shutil

    try:
        project_dir = settings.project_dir(project_id)

        if not project_dir.exists():
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

        # Remove entire project directory
        shutil.rmtree(project_dir)

        return {"message": f"Project {project_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
