"""Project management API endpoints."""

import json
import re
from datetime import datetime
from fastapi import APIRouter, HTTPException
from typing import List

from app.models.project import Project, ProjectCreate, ProjectUpdate, ProjectSummary
from app.config import settings
from app.utils.file_utils import read_json_file, write_json_file
from app.utils.backup import create_snapshot
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
                    word_count_goal=data.get("word_count_goal"),
                    outline_only=data.get("outline_only", False),
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

    # Create snapshot before clearing structure
    await create_snapshot(project_id, "pre-clear-structure", reason="pre-clear")

    deleted = {"acts": 0, "chapters": 0, "scenes": 0, "generations": 0}

    # Delete all scenes
    scenes_dir = project_path / "scenes"
    if scenes_dir.exists():
        for f in scenes_dir.glob("*.json"):
            f.unlink()
            deleted["scenes"] += 1

    # Delete all chapters
    chapters_dir = project_path / "chapters"
    if chapters_dir.exists():
        for f in chapters_dir.glob("*.json"):
            f.unlink()
            deleted["chapters"] += 1

    # Delete all acts
    acts_dir = project_path / "acts"
    if acts_dir.exists():
        for f in acts_dir.glob("*.json"):
            f.unlink()
            deleted["acts"] += 1

    # Delete all generations
    generations_dir = project_path / "generations"
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


# ============================================
# Story Structure Templates
# ============================================

from app.utils.story_templates import list_templates, get_template
from pydantic import BaseModel, Field


class ApplyTemplateRequest(BaseModel):
    template_id: str = Field(..., description="ID of the template to apply")
    clear_existing: bool = Field(default=False, description="Clear existing structure before applying")


@router.get("/templates/list")
async def get_available_templates():
    """
    List all available story structure templates.

    Returns:
        List of templates with id, name, description, and counts
    """
    return list_templates()


@router.post("/{project_id}/apply-template")
async def apply_template_to_project(project_id: str, request: ApplyTemplateRequest):
    """
    Apply a story structure template to a project.

    Creates acts, chapters, and scenes based on the selected template.
    Optionally clears existing structure first.

    Args:
        project_id: Project ID
        request: Template ID and options

    Returns:
        Summary of created structure
    """
    import time

    # Verify project exists
    project_dir = settings.project_dir(project_id)
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    # Get template
    template = get_template(request.template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template not found: {request.template_id}")

    # Create backup before modifying
    await create_snapshot(project_id, f"Before applying template: {template['name']}")

    # Optionally clear existing structure
    if request.clear_existing:
        import shutil
        for subdir in ["acts", "chapters", "scenes"]:
            dir_path = project_dir / subdir
            if dir_path.exists():
                shutil.rmtree(dir_path)
            dir_path.mkdir(parents=True, exist_ok=True)

    # Ensure directories exist
    acts_dir = project_dir / "acts"
    chapters_dir = project_dir / "chapters"
    scenes_dir = settings.scenes_dir(project_id)
    acts_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir.mkdir(parents=True, exist_ok=True)
    scenes_dir.mkdir(parents=True, exist_ok=True)

    created = {"acts": 0, "chapters": 0, "scenes": 0, "beats": 0}
    now = datetime.utcnow().isoformat()

    for act_num, act_data in enumerate(template["acts"], 1):
        # Create act
        act_id = slugify(f"act-{act_num}-{act_data['title']}")
        act = {
            "id": act_id,
            "title": act_data["title"],
            "description": act_data.get("description", ""),
            "act_number": act_num,
            "created_at": now,
            "updated_at": now
        }
        await write_json_file(acts_dir / f"{act_id}.json", act)
        created["acts"] += 1

        for ch_num, chapter_data in enumerate(act_data["chapters"], 1):
            # Create chapter
            global_ch_num = sum(
                len(a["chapters"]) for a in template["acts"][:act_num-1]
            ) + ch_num

            chapter_id = slugify(f"ch-{global_ch_num}-{chapter_data['title']}")
            chapter = {
                "id": chapter_id,
                "title": chapter_data["title"],
                "chapter_number": global_ch_num,
                "act_id": act_id,
                "created_at": now,
                "updated_at": now
            }
            await write_json_file(chapters_dir / f"{chapter_id}.json", chapter)
            created["chapters"] += 1

            for scene_num, scene_data in enumerate(chapter_data["scenes"], 1):
                # Create scene with beats
                scene_id = slugify(f"scene-{global_ch_num}-{scene_num}-{scene_data['title']}")

                # Convert beat data to Beat objects
                beats = []
                for beat_num, beat_data in enumerate(scene_data.get("beats", [])):
                    beats.append({
                        "id": f"beat-{int(time.time() * 1000)}-{beat_num}",
                        "text": beat_data["text"],
                        "notes": beat_data.get("notes"),
                        "tags": beat_data.get("tags", []),
                        "order": beat_num
                    })
                    created["beats"] += 1
                    time.sleep(0.001)  # Ensure unique IDs

                scene = {
                    "id": scene_id,
                    "title": scene_data["title"],
                    "outline": scene_data.get("outline", ""),
                    "scene_number": scene_num,
                    "chapter_id": chapter_id,
                    "character_ids": [],
                    "world_context_ids": [],
                    "previous_scene_ids": [],
                    "is_canon": False,
                    "prose": None,
                    "summary": None,
                    "edit_mode": False,
                    "original_prose": None,
                    "beats": beats,
                    "depends_on": [],
                    "outline_status": "idea",
                    "created_at": now,
                    "updated_at": now
                }
                await write_json_file(scenes_dir / f"{scene_id}.json", scene)
                created["scenes"] += 1

    return {
        "message": f"Applied template: {template['name']}",
        "template_id": request.template_id,
        "template_name": template["name"],
        "created": created
    }


# ============================================
# Auto-Generate Outline
# ============================================

from app.services.outline_generator import (
    OutlineGenerator, GenerationScope, GenerationMode,
    estimate_generation_cost, SCOPE_CONFIG
)


class AutoGenerateRequest(BaseModel):
    seed: str = Field(..., description="Story premise/synopsis")
    scope: str = Field(default="standard", description="Generation scope: quick, standard, detailed")
    mode: str = Field(default="full", description="Generation mode: staged, full")
    genre: Optional[str] = Field(default=None, description="Story genre")
    character_names: Optional[List[str]] = Field(default=None, description="Character names to include")
    budget_limit: Optional[float] = Field(default=None, description="Max cost in dollars")
    level: Optional[str] = Field(default=None, description="For staged mode: acts, chapters, scenes, beats")
    context: Optional[dict] = Field(default=None, description="For staged mode: previously approved structure")


@router.get("/auto-generate/estimate")
async def estimate_auto_generate_cost(scope: str = "standard"):
    """
    Get cost estimate for auto-generating an outline.

    Args:
        scope: Generation scope (quick, standard, detailed)

    Returns:
        Token and cost estimates
    """
    try:
        gen_scope = GenerationScope(scope)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid scope: {scope}. Use: quick, standard, detailed")

    return estimate_generation_cost(gen_scope)


@router.get("/auto-generate/scopes")
async def get_generation_scopes():
    """
    Get available generation scopes with descriptions.

    Returns:
        List of scopes with their configurations
    """
    scopes = []
    for scope in GenerationScope:
        estimate = estimate_generation_cost(scope)
        scopes.append({
            "id": scope.value,
            "name": scope.value.title(),
            "description": estimate["description"],
            "estimates": estimate["estimates"],
            "cost": estimate["cost"]
        })
    return scopes


@router.post("/{project_id}/auto-generate")
async def auto_generate_outline(project_id: str, request: AutoGenerateRequest):
    """
    Auto-generate a story outline from a seed premise.

    Supports two modes:
    - full: Generate complete outline in one operation
    - staged: Generate one level at a time (acts -> chapters -> scenes -> beats)

    Args:
        project_id: Project ID
        request: Generation parameters

    Returns:
        Generated outline structure
    """
    # Verify project exists
    project_dir = settings.project_dir(project_id)
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    # Parse scope
    try:
        scope = GenerationScope(request.scope)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid scope: {request.scope}")

    # Create generator
    generator = OutlineGenerator()

    if request.mode == "full":
        # Full generation mode
        result = await generator.generate_full_outline(
            seed=request.seed,
            scope=scope,
            genre=request.genre,
            characters=request.character_names,
            budget_limit=request.budget_limit
        )

        return result

    elif request.mode == "staged":
        # Staged generation mode
        if not request.level:
            raise HTTPException(status_code=400, detail="Staged mode requires 'level' parameter")

        if request.level == "acts":
            result = await generator.generate_acts(
                seed=request.seed,
                scope=scope,
                genre=request.genre,
                characters=request.character_names
            )
        elif request.level == "chapters":
            if not request.context or "acts" not in request.context:
                raise HTTPException(status_code=400, detail="Chapters generation requires acts in context")
            if "act_index" not in request.context:
                raise HTTPException(status_code=400, detail="Chapters generation requires act_index in context")

            result = await generator.generate_chapters(
                seed=request.seed,
                acts=request.context["acts"],
                act_index=request.context["act_index"],
                scope=scope
            )
        elif request.level == "scenes":
            if not request.context or "act" not in request.context or "chapter" not in request.context:
                raise HTTPException(status_code=400, detail="Scenes generation requires act and chapter in context")

            result = await generator.generate_scenes(
                seed=request.seed,
                act=request.context["act"],
                chapter=request.context["chapter"],
                scope=scope
            )
        elif request.level == "beats":
            if not request.context or "scene" not in request.context:
                raise HTTPException(status_code=400, detail="Beats generation requires scene in context")

            result = await generator.generate_beats(
                seed=request.seed,
                scene=request.context["scene"],
                scope=scope
            )
        else:
            raise HTTPException(status_code=400, detail=f"Invalid level: {request.level}")

        result["usage"] = generator._get_usage()
        return result

    else:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {request.mode}. Use: full, staged")


@router.post("/{project_id}/auto-generate/apply")
async def apply_generated_outline(project_id: str, outline: dict, clear_existing: bool = False):
    """
    Apply a generated outline to a project, creating acts/chapters/scenes/beats.

    Args:
        project_id: Project ID
        outline: Generated outline structure from auto-generate endpoint
        clear_existing: Whether to clear existing structure first

    Returns:
        Summary of created items
    """
    import time as time_module

    # Verify project exists
    project_dir = settings.project_dir(project_id)
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    # Create backup
    await create_snapshot(project_id, "Before applying auto-generated outline")

    # Optionally clear existing
    if clear_existing:
        import shutil
        for subdir in ["acts", "chapters", "scenes"]:
            dir_path = project_dir / subdir
            if dir_path.exists():
                shutil.rmtree(dir_path)
            dir_path.mkdir(parents=True, exist_ok=True)

    # Ensure directories exist
    acts_dir = project_dir / "acts"
    chapters_dir = project_dir / "chapters"
    scenes_dir = settings.scenes_dir(project_id)
    acts_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir.mkdir(parents=True, exist_ok=True)
    scenes_dir.mkdir(parents=True, exist_ok=True)

    created = {"acts": 0, "chapters": 0, "scenes": 0, "beats": 0}
    now = datetime.utcnow().isoformat()
    global_chapter_num = 0

    for act_num, act_data in enumerate(outline.get("acts", []), 1):
        # Create act
        act_id = slugify(f"act-{act_num}-{act_data['title']}")
        act = {
            "id": act_id,
            "title": act_data["title"],
            "description": act_data.get("description", ""),
            "act_number": act_num,
            "created_at": now,
            "updated_at": now
        }
        await write_json_file(acts_dir / f"{act_id}.json", act)
        created["acts"] += 1

        for chapter_data in act_data.get("chapters", []):
            global_chapter_num += 1

            # Create chapter
            chapter_id = slugify(f"ch-{global_chapter_num}-{chapter_data['title']}")
            chapter = {
                "id": chapter_id,
                "title": chapter_data["title"],
                "description": chapter_data.get("description", ""),
                "chapter_number": global_chapter_num,
                "act_id": act_id,
                "created_at": now,
                "updated_at": now
            }
            await write_json_file(chapters_dir / f"{chapter_id}.json", chapter)
            created["chapters"] += 1

            for scene_num, scene_data in enumerate(chapter_data.get("scenes", []), 1):
                # Create scene with beats
                scene_id = slugify(f"scene-{global_chapter_num}-{scene_num}-{scene_data['title']}")

                # Convert beats
                beats = []
                for beat_num, beat_data in enumerate(scene_data.get("beats", [])):
                    beats.append({
                        "id": f"beat-{int(time_module.time() * 1000)}-{beat_num}",
                        "text": beat_data.get("text", ""),
                        "notes": beat_data.get("notes"),
                        "tags": [],
                        "order": beat_num
                    })
                    created["beats"] += 1
                    time_module.sleep(0.001)

                scene = {
                    "id": scene_id,
                    "title": scene_data["title"],
                    "outline": scene_data.get("outline", ""),
                    "scene_number": scene_num,
                    "chapter_id": chapter_id,
                    "character_ids": [],
                    "world_context_ids": [],
                    "previous_scene_ids": [],
                    "is_canon": False,
                    "prose": None,
                    "summary": None,
                    "edit_mode": False,
                    "original_prose": None,
                    "beats": beats,
                    "depends_on": [],
                    "outline_status": "idea",
                    "pov": scene_data.get("pov"),
                    "tone": scene_data.get("tone"),
                    "created_at": now,
                    "updated_at": now
                }
                await write_json_file(scenes_dir / f"{scene_id}.json", scene)
                created["scenes"] += 1

    return {
        "message": "Applied auto-generated outline",
        "created": created
    }
