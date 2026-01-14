"""Project management API endpoints."""

import json
import re
from datetime import datetime
from fastapi import APIRouter, HTTPException
from typing import List

from app.models.project import Project, ProjectCreate, ProjectUpdate, ProjectSummary
from app.config import settings

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
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
