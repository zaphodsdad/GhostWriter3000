"""Chapter-by-chapter extraction of characters, world elements, and memory from imported prose."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services.extraction_service import get_extraction_service
from app.services.entity_service import get_entity_service
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ChapterExtractionRequest(BaseModel):
    extract_entities: bool = True   # Characters + world
    extract_memory: bool = True     # Plot events, state changes per scene
    model: Optional[str] = None


class ChapterExtractionStatus(BaseModel):
    project_id: str
    series_id: Optional[str] = None
    status: str  # running | completed | failed | cancelled
    total_chapters: int
    chapters_extracted: int
    current_chapter: Optional[str] = None
    current_phase: Optional[str] = None        # entities | memory | summaries
    current_chapter_step: Optional[str] = None  # e.g. "Extracting characters..."
    characters_found: int = 0
    world_elements_found: int = 0
    scenes_processed: int = 0
    total_scenes: int = 0
    errors: List[str] = []
    started_at: str
    completed_at: Optional[str] = None


# In-memory job store (keyed by project_id)
_extraction_jobs: Dict[str, ChapterExtractionStatus] = {}
_extraction_cancel: Dict[str, bool] = {}


# ---------------------------------------------------------------------------
# Helpers — load chapter/scene data from disk
# ---------------------------------------------------------------------------

def _load_chapters(project_id: str) -> List[Dict[str, Any]]:
    """Load all chapters sorted by chapter_number."""
    chapters_dir = settings.project_dir(project_id) / "chapters"
    if not chapters_dir.exists():
        return []
    chapters = []
    for fp in chapters_dir.glob("*.json"):
        try:
            with open(fp) as f:
                chapters.append(json.load(f))
        except Exception:
            continue
    chapters.sort(key=lambda c: c.get("chapter_number", 0))
    return chapters


def _load_scenes_for_chapter(project_id: str, chapter_id: str) -> List[Dict[str, Any]]:
    """Load all scenes belonging to a chapter, sorted by scene_number."""
    scenes_dir = settings.scenes_dir(project_id)
    if not scenes_dir.exists():
        return []
    scenes = []
    for fp in scenes_dir.glob("*.json"):
        try:
            with open(fp) as f:
                scene = json.load(f)
            if scene.get("chapter_id") == chapter_id:
                scenes.append(scene)
        except Exception:
            continue
    scenes.sort(key=lambda s: s.get("scene_number", 0))
    return scenes


def _get_scene_prose(scene: Dict[str, Any]) -> str:
    """Get prose from a scene — prefer original_prose (imported text), fall back to prose."""
    return scene.get("original_prose") or scene.get("prose") or ""


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------

def _get_existing_project_character_names(project_id: str) -> List[str]:
    """Get names of existing characters at project level."""
    from app.services.entity_service import parse_markdown_frontmatter
    chars_dir = settings.characters_dir(project_id)
    names = []
    if chars_dir.exists():
        for fp in chars_dir.glob("*.md"):
            try:
                content = fp.read_text(encoding='utf-8')
                metadata, _ = parse_markdown_frontmatter(content)
                if 'name' in metadata:
                    names.append(metadata['name'])
            except Exception:
                continue
    return names


def _get_existing_project_world_names(project_id: str) -> List[str]:
    """Get names of existing world elements at project level."""
    from app.services.entity_service import parse_markdown_frontmatter
    world_dir = settings.world_dir(project_id)
    names = []
    if world_dir.exists():
        for fp in world_dir.glob("*.md"):
            try:
                content = fp.read_text(encoding='utf-8')
                metadata, _ = parse_markdown_frontmatter(content)
                if 'name' in metadata:
                    names.append(metadata['name'])
            except Exception:
                continue
    return names


async def _save_characters_to_project(
    project_id: str,
    book_number: int,
    characters: List[Dict[str, Any]],
) -> Dict[str, int]:
    """Save extracted characters to project-level directory (for standalone books)."""
    from app.services.entity_service import slugify, parse_markdown_frontmatter, build_markdown_with_frontmatter
    entity_svc = get_entity_service()

    chars_dir = settings.characters_dir(project_id)
    chars_dir.mkdir(parents=True, exist_ok=True)

    created = 0
    updated = 0

    for char in characters:
        name = char.get('name', 'Unknown')
        char_id = slugify(name)
        filepath = chars_dir / f"{char_id}.md"

        if filepath.exists():
            content = filepath.read_text(encoding='utf-8')
            metadata, body = parse_markdown_frontmatter(content)
            new_section = entity_svc._format_character_section(char, project_id, book_number)
            body = body + f"\n\n{new_section}"
            metadata = entity_svc._merge_character_metadata(metadata, char, book_number)
            filepath.write_text(build_markdown_with_frontmatter(metadata, body), encoding='utf-8')
            updated += 1
        else:
            metadata = {
                'name': name,
                'role': char.get('role', 'supporting'),
                'first_seen_book': book_number,
                'created_from': project_id,
            }
            body = entity_svc._format_character_body(char, project_id, book_number)
            filepath.write_text(build_markdown_with_frontmatter(metadata, body), encoding='utf-8')
            created += 1

    return {"created": created, "updated": updated}


async def _save_world_to_project(
    project_id: str,
    book_number: int,
    elements: List[Dict[str, Any]],
) -> Dict[str, int]:
    """Save extracted world elements to project-level directory (for standalone books)."""
    from app.services.entity_service import slugify, parse_markdown_frontmatter, build_markdown_with_frontmatter
    entity_svc = get_entity_service()

    world_dir = settings.world_dir(project_id)
    world_dir.mkdir(parents=True, exist_ok=True)

    created = 0
    updated = 0

    for elem in elements:
        name = elem.get('name', 'Unknown')
        elem_id = slugify(name)
        filepath = world_dir / f"{elem_id}.md"

        if filepath.exists():
            content = filepath.read_text(encoding='utf-8')
            metadata, body = parse_markdown_frontmatter(content)
            new_section = entity_svc._format_world_section(elem, project_id, book_number)
            body = body + f"\n\n{new_section}"
            metadata = entity_svc._merge_world_metadata(metadata, elem, book_number)
            filepath.write_text(build_markdown_with_frontmatter(metadata, body), encoding='utf-8')
            updated += 1
        else:
            metadata = {
                'name': name,
                'category': elem.get('category', 'GENERAL'),
                'first_seen_book': book_number,
                'created_from': project_id,
            }
            body = entity_svc._format_world_body(elem, project_id, book_number)
            filepath.write_text(build_markdown_with_frontmatter(metadata, body), encoding='utf-8')
            created += 1

    return {"created": created, "updated": updated}


async def run_chapter_extraction(
    project_id: str,
    series_id: Optional[str],
    book_number: int,
    chapters: List[Dict[str, Any]],
    extract_entities: bool,
    extract_memory: bool,
    model: Optional[str] = None,
):
    """Process chapters one by one, extracting entities and memory."""
    job = _extraction_jobs[project_id]
    extraction_svc = get_extraction_service()
    entity_svc = get_entity_service()

    # Pre-load existing names so we can pass them to extraction to avoid dupes
    if series_id:
        existing_chars = entity_svc._get_existing_character_names(series_id)
        existing_worlds = entity_svc._get_existing_world_names(series_id)
    else:
        existing_chars = _get_existing_project_character_names(project_id)
        existing_worlds = _get_existing_project_world_names(project_id)

    # Count total scenes up front
    total_scenes = 0
    for ch in chapters:
        scenes = _load_scenes_for_chapter(project_id, ch["id"])
        total_scenes += len([s for s in scenes if _get_scene_prose(s)])
    job.total_scenes = total_scenes

    for i, chapter in enumerate(chapters):
        # Check cancellation
        if _extraction_cancel.get(project_id, False):
            job.status = "cancelled"
            job.completed_at = datetime.utcnow().isoformat()
            logger.info(f"Extraction cancelled for {project_id} after {i} chapters")
            return

        chapter_id = chapter["id"]
        chapter_title = chapter.get("title", f"Chapter {chapter.get('chapter_number', i+1)}")
        chapter_number = chapter.get("chapter_number", i + 1)
        job.current_chapter = chapter_title
        job.chapters_extracted = i

        # Load scenes and gather prose
        scenes = _load_scenes_for_chapter(project_id, chapter_id)
        scenes_with_prose = [(s, _get_scene_prose(s)) for s in scenes]
        scenes_with_prose = [(s, p) for s, p in scenes_with_prose if p.strip()]

        if not scenes_with_prose:
            logger.info(f"Skipping chapter '{chapter_title}' — no prose")
            continue

        # Combine all scene prose for this chapter
        chapter_prose = "\n\n---\n\n".join(p for _, p in scenes_with_prose)

        # --- Phase: Entity extraction ---
        if extract_entities:
            job.current_phase = "entities"
            try:
                # Extract characters
                job.current_chapter_step = "Extracting characters..."
                char_result = await extraction_svc.extract_characters(
                    chapter_prose, model, existing_characters=existing_chars
                )
                new_chars = char_result.get("characters", [])

                # Save characters with merge logic
                if series_id:
                    char_stats = await entity_svc._save_characters(
                        series_id, project_id, book_number, new_chars
                    )
                else:
                    char_stats = await _save_characters_to_project(
                        project_id, book_number, new_chars
                    )
                job.characters_found += char_stats["created"] + char_stats["updated"]

                # Add new names to accumulator
                for c in new_chars:
                    name = c.get("name", "")
                    if name and name not in existing_chars:
                        existing_chars.append(name)

                await asyncio.sleep(2)

                # Check cancellation between character and world extraction
                if _extraction_cancel.get(project_id, False):
                    job.status = "cancelled"
                    job.completed_at = datetime.utcnow().isoformat()
                    logger.info(f"Extraction cancelled for {project_id} after character extraction of chapter {i+1}")
                    return

                # Extract world elements
                job.current_chapter_step = "Extracting world elements..."
                world_result = await extraction_svc.extract_world(
                    chapter_prose, model, existing_elements=existing_worlds
                )
                new_worlds = world_result.get("world_elements", [])

                # Save world elements with merge logic
                if series_id:
                    world_stats = await entity_svc._save_world_elements(
                        series_id, project_id, book_number, new_worlds
                    )
                else:
                    world_stats = await _save_world_to_project(
                        project_id, book_number, new_worlds
                    )
                job.world_elements_found += world_stats["created"] + world_stats["updated"]

                # Add new names to accumulator
                for w in new_worlds:
                    name = w.get("name", "")
                    if name and name not in existing_worlds:
                        existing_worlds.append(name)

                await asyncio.sleep(2)

            except Exception as e:
                err = f"Entity extraction failed for '{chapter_title}': {e}"
                logger.warning(err)
                job.errors.append(err)

        # Check cancellation before memory phase
        if _extraction_cancel.get(project_id, False):
            job.status = "cancelled"
            job.completed_at = datetime.utcnow().isoformat()
            logger.info(f"Extraction cancelled for {project_id} after entity extraction of chapter {i+1}")
            return

        # --- Phase: Memory extraction (per scene) — requires series ---
        if extract_memory and series_id:
            job.current_phase = "memory"
            try:
                from app.services.memory_service import memory_service as memory_svc

                for scene_idx, (scene, prose) in enumerate(scenes_with_prose):
                    scene_id = scene.get("id", "unknown")
                    scene_title = scene.get("title", f"Scene {scene_idx + 1}")
                    job.current_chapter_step = f"Memory: scene {scene_idx + 1} of {len(scenes_with_prose)}"

                    try:
                        await memory_svc.extract_from_scene(
                            series_id=series_id,
                            book_id=project_id,
                            scene_id=scene_id,
                            prose=prose,
                            scene_title=scene_title,
                            chapter_title=chapter_title,
                            book_number=book_number,
                            chapter_number=chapter_number,
                            scene_number=scene.get("scene_number", scene_idx + 1),
                            character_names=existing_chars,
                            model=model,
                        )
                    except Exception as e:
                        err = f"Memory extraction failed for scene '{scene_title}': {e}"
                        logger.warning(err)
                        job.errors.append(err)

                    job.scenes_processed += 1
                    await asyncio.sleep(1)

                    # Check cancellation between scene memory extractions
                    if _extraction_cancel.get(project_id, False):
                        job.status = "cancelled"
                        job.completed_at = datetime.utcnow().isoformat()
                        logger.info(f"Extraction cancelled for {project_id} during memory extraction")
                        return

            except Exception as e:
                err = f"Memory phase failed for '{chapter_title}': {e}"
                logger.warning(err)
                job.errors.append(err)

        logger.info(
            f"Chapter {i+1}/{len(chapters)} '{chapter_title}' done — "
            f"chars={job.characters_found}, world={job.world_elements_found}, scenes={job.scenes_processed}"
        )

    # --- Final: generate memory summaries (series only) ---
    if extract_memory and series_id:
        job.current_phase = "summaries"
        job.current_chapter = None
        job.current_chapter_step = "Generating memory summaries..."
        try:
            from app.services.memory_service import memory_service as memory_svc
            await memory_svc.generate_summaries(series_id, model=model)
        except Exception as e:
            err = f"Summary generation failed: {e}"
            logger.warning(err)
            job.errors.append(err)

    job.status = "completed"
    job.chapters_extracted = len(chapters)
    job.current_chapter = None
    job.current_phase = None
    job.current_chapter_step = None
    job.completed_at = datetime.utcnow().isoformat()
    logger.info(
        f"Extraction complete for {project_id}: "
        f"{job.characters_found} chars, {job.world_elements_found} world, "
        f"{job.scenes_processed} scenes, {len(job.errors)} errors"
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/extract")
async def start_chapter_extraction(
    project_id: str,
    background_tasks: BackgroundTasks,
    request: ChapterExtractionRequest = ChapterExtractionRequest(),
):
    """Kick off chapter-by-chapter extraction as a background task."""

    # Check for running job — allow override if stale (>10 min without completing)
    existing = _extraction_jobs.get(project_id)
    if existing and existing.status == "running":
        started = datetime.fromisoformat(existing.started_at)
        age_minutes = (datetime.utcnow() - started).total_seconds() / 60
        if age_minutes < 120:  # 2 hour timeout — long extractions are normal
            raise HTTPException(status_code=409, detail="Extraction already in progress for this project")

    # Load project
    project_path = settings.project_dir(project_id) / "project.json"
    if not project_path.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    with open(project_path) as f:
        project = json.load(f)

    series_id = project.get("series_id")  # None for standalone books
    book_number = project.get("book_number", 1) or 1

    # Load chapters
    chapters = _load_chapters(project_id)
    if not chapters:
        raise HTTPException(status_code=400, detail="No chapters found in this project")

    # Check at least one chapter has prose
    has_prose = False
    for ch in chapters:
        scenes = _load_scenes_for_chapter(project_id, ch["id"])
        if any(_get_scene_prose(s) for s in scenes):
            has_prose = True
            break

    if not has_prose:
        raise HTTPException(status_code=400, detail="No chapters with prose found. Import a manuscript first.")

    # Create job status
    now = datetime.utcnow().isoformat()
    job = ChapterExtractionStatus(
        project_id=project_id,
        series_id=series_id,
        status="running",
        total_chapters=len(chapters),
        chapters_extracted=0,
        started_at=now,
    )
    _extraction_jobs[project_id] = job
    _extraction_cancel[project_id] = False

    # Launch background task
    background_tasks.add_task(
        run_chapter_extraction,
        project_id=project_id,
        series_id=series_id,
        book_number=book_number,
        chapters=chapters,
        extract_entities=request.extract_entities,
        extract_memory=request.extract_memory,
        model=request.model,
    )

    return {"status": "started", "total_chapters": len(chapters)}


@router.get("/extract/status")
async def get_extraction_status(project_id: str):
    """Poll the current extraction status."""
    job = _extraction_jobs.get(project_id)
    if not job:
        raise HTTPException(status_code=404, detail="No extraction job found for this project")
    return job


@router.post("/extract/cancel")
async def cancel_extraction(project_id: str):
    """Cancel a running extraction. Stops at next chapter boundary."""
    job = _extraction_jobs.get(project_id)
    if not job or job.status != "running":
        raise HTTPException(status_code=404, detail="No running extraction job to cancel")
    _extraction_cancel[project_id] = True
    return {"status": "cancelling"}
