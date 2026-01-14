"""Series API routes for managing book series."""

import json
import re
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models.series import (
    Series,
    SeriesCreate,
    SeriesSummary,
    SeriesUpdate,
    AddBookToSeries,
    ReorderBooks
)
from app.services.series_service import get_series_service
from app.services.markdown_parser import MarkdownParser

router = APIRouter()
parser = MarkdownParser()


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text


def ensure_series_exists(series_id: str):
    """Check that series exists, raise 404 if not."""
    if not settings.series_path(series_id).exists():
        raise HTTPException(status_code=404, detail=f"Series not found: {series_id}")


# Series CRUD

@router.get("/", response_model=List[SeriesSummary])
async def list_series():
    """List all series."""
    try:
        service = get_series_service()
        return await service.list_series()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list series: {str(e)}")


@router.get("/{series_id}", response_model=Series)
async def get_series(series_id: str):
    """Get a series by ID."""
    ensure_series_exists(series_id)
    try:
        service = get_series_service()
        series = await service.get_series(series_id)
        if not series:
            raise HTTPException(status_code=404, detail=f"Series not found: {series_id}")
        return series
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get series: {str(e)}")


@router.post("/", response_model=Series, status_code=201)
async def create_series(series_data: SeriesCreate):
    """Create a new series."""
    try:
        # Generate series ID from title
        series_id = slugify(series_data.title)
        if not series_id:
            series_id = f"series-{int(datetime.utcnow().timestamp())}"

        # Check if series already exists
        if settings.series_path(series_id).exists():
            raise HTTPException(status_code=409, detail=f"Series already exists: {series_id}")

        service = get_series_service()
        return await service.create_series(series_data, series_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create series: {str(e)}")


@router.put("/{series_id}", response_model=Series)
async def update_series(series_id: str, series_update: SeriesUpdate):
    """Update a series."""
    ensure_series_exists(series_id)
    try:
        service = get_series_service()
        updates = series_update.model_dump(exclude_unset=True)
        series = await service.update_series(series_id, updates)
        if not series:
            raise HTTPException(status_code=404, detail=f"Series not found: {series_id}")
        return series
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update series: {str(e)}")


@router.delete("/{series_id}")
async def delete_series(series_id: str):
    """Delete a series (projects/books are preserved)."""
    ensure_series_exists(series_id)
    try:
        service = get_series_service()
        await service.delete_series(series_id)
        return {"message": f"Series '{series_id}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete series: {str(e)}")


# Book management within series

@router.post("/{series_id}/books", response_model=Series)
async def add_book_to_series(series_id: str, book_data: AddBookToSeries):
    """Add a project/book to a series."""
    ensure_series_exists(series_id)
    try:
        service = get_series_service()
        series = await service.add_book_to_series(
            series_id,
            book_data.project_id,
            book_data.book_number
        )
        if not series:
            raise HTTPException(status_code=404, detail=f"Series not found: {series_id}")
        return series
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add book: {str(e)}")


@router.delete("/{series_id}/books/{project_id}", response_model=Series)
async def remove_book_from_series(series_id: str, project_id: str):
    """Remove a project/book from a series."""
    ensure_series_exists(series_id)
    try:
        service = get_series_service()
        series = await service.remove_book_from_series(series_id, project_id)
        if not series:
            raise HTTPException(status_code=404, detail=f"Series not found: {series_id}")
        return series
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove book: {str(e)}")


@router.put("/{series_id}/books/reorder", response_model=Series)
async def reorder_books(series_id: str, reorder_data: ReorderBooks):
    """Reorder books in a series."""
    ensure_series_exists(series_id)
    try:
        service = get_series_service()
        series = await service.reorder_books(series_id, reorder_data.project_ids)
        if not series:
            raise HTTPException(status_code=404, detail=f"Series not found: {series_id}")
        return series
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reorder books: {str(e)}")


# Series-level characters (shared across all books)

@router.get("/{series_id}/characters/")
async def list_series_characters(series_id: str):
    """List all characters for a series."""
    ensure_series_exists(series_id)
    try:
        chars_dir = settings.series_characters_dir(series_id)
        characters = []

        if chars_dir.exists():
            for filepath in chars_dir.glob("*.md"):
                try:
                    parsed = parser.parse_file(filepath)
                    char_id = filepath.stem.lower().replace(" ", "-")
                    characters.append({
                        "id": char_id,
                        "filename": filepath.name,
                        "metadata": parsed.get("metadata", {}),
                        "content": parsed.get("content", ""),
                        "updated_at": datetime.fromtimestamp(filepath.stat().st_mtime).isoformat()
                    })
                except Exception:
                    continue

        return characters
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list characters: {str(e)}")


@router.post("/{series_id}/characters/")
async def create_series_character(series_id: str, character_data: dict):
    """Create a character for the series."""
    ensure_series_exists(series_id)
    try:
        chars_dir = settings.series_characters_dir(series_id)
        chars_dir.mkdir(parents=True, exist_ok=True)

        filename = character_data.get("filename", "")
        if not filename:
            name = character_data.get("metadata", {}).get("name", "character")
            filename = f"{name}.md"

        filepath = chars_dir / filename

        parser.write_file(
            filepath,
            character_data.get("metadata", {}),
            character_data.get("content", "")
        )

        char_id = filepath.stem.lower().replace(" ", "-")
        return {
            "id": char_id,
            "filename": filepath.name,
            "metadata": character_data.get("metadata", {}),
            "content": character_data.get("content", ""),
            "created_at": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create character: {str(e)}")


@router.delete("/{series_id}/characters/{character_id}")
async def delete_series_character(series_id: str, character_id: str):
    """Delete a character from the series."""
    ensure_series_exists(series_id)
    try:
        chars_dir = settings.series_characters_dir(series_id)

        # Find file by ID
        for filepath in chars_dir.glob("*.md"):
            if filepath.stem.lower().replace(" ", "-") == character_id:
                filepath.unlink()
                return {"message": f"Character '{character_id}' deleted"}

        raise HTTPException(status_code=404, detail=f"Character not found: {character_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete character: {str(e)}")


# Series-level world contexts

@router.get("/{series_id}/world/")
async def list_series_worlds(series_id: str):
    """List all world contexts for a series."""
    ensure_series_exists(series_id)
    try:
        world_dir = settings.series_world_dir(series_id)
        worlds = []

        if world_dir.exists():
            for filepath in world_dir.glob("*.md"):
                try:
                    parsed = parser.parse_file(filepath)
                    world_id = filepath.stem.lower().replace(" ", "-")
                    worlds.append({
                        "id": world_id,
                        "filename": filepath.name,
                        "metadata": parsed.get("metadata", {}),
                        "content": parsed.get("content", ""),
                        "updated_at": datetime.fromtimestamp(filepath.stat().st_mtime).isoformat()
                    })
                except Exception:
                    continue

        return worlds
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list world contexts: {str(e)}")


@router.post("/{series_id}/world/")
async def create_series_world(series_id: str, world_data: dict):
    """Create a world context for the series."""
    ensure_series_exists(series_id)
    try:
        world_dir = settings.series_world_dir(series_id)
        world_dir.mkdir(parents=True, exist_ok=True)

        filename = world_data.get("filename", "")
        if not filename:
            name = world_data.get("metadata", {}).get("name", "world")
            filename = f"{name}.md"

        filepath = world_dir / filename

        parser.write_file(
            filepath,
            world_data.get("metadata", {}),
            world_data.get("content", "")
        )

        world_id = filepath.stem.lower().replace(" ", "-")
        return {
            "id": world_id,
            "filename": filepath.name,
            "metadata": world_data.get("metadata", {}),
            "content": world_data.get("content", ""),
            "created_at": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create world context: {str(e)}")


@router.delete("/{series_id}/world/{world_id}")
async def delete_series_world(series_id: str, world_id: str):
    """Delete a world context from the series."""
    ensure_series_exists(series_id)
    try:
        world_dir = settings.series_world_dir(series_id)

        for filepath in world_dir.glob("*.md"):
            if filepath.stem.lower().replace(" ", "-") == world_id:
                filepath.unlink()
                return {"message": f"World context '{world_id}' deleted"}

        raise HTTPException(status_code=404, detail=f"World context not found: {world_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete world context: {str(e)}")


# Series-level style guide

@router.get("/{series_id}/style")
async def get_series_style(series_id: str):
    """Get the series-level style guide."""
    ensure_series_exists(series_id)
    try:
        style_file = settings.series_path(series_id) / "style.json"
        if not style_file.exists():
            return {"pov": None, "tense": None, "tone": None, "heat_level": None, "guide": None}

        with open(style_file) as f:
            return json.load(f)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get style guide: {str(e)}")


@router.put("/{series_id}/style")
async def update_series_style(series_id: str, style_data: dict):
    """Update the series-level style guide."""
    ensure_series_exists(series_id)
    try:
        style_file = settings.series_path(series_id) / "style.json"

        # Load existing or create new
        if style_file.exists():
            with open(style_file) as f:
                existing = json.load(f)
        else:
            existing = {}

        # Merge updates
        for key, value in style_data.items():
            if value is not None:
                existing[key] = value

        with open(style_file, "w") as f:
            json.dump(existing, f, indent=2)

        return existing
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update style guide: {str(e)}")


# Series-level references

def _load_refs_index(refs_dir) -> dict:
    """Load reference index file."""
    index_file = refs_dir / "_index.json"
    if index_file.exists():
        with open(index_file) as f:
            return json.load(f)
    return {}


def _save_refs_index(refs_dir, index: dict):
    """Save reference index file."""
    index_file = refs_dir / "_index.json"
    with open(index_file, "w") as f:
        json.dump(index, f, indent=2)


@router.get("/{series_id}/references/")
async def list_series_references(series_id: str):
    """List all reference documents for a series."""
    ensure_series_exists(series_id)
    try:
        refs_dir = settings.series_references_dir(series_id)
        refs_dir.mkdir(parents=True, exist_ok=True)
        index = _load_refs_index(refs_dir)
        references = []

        for filepath in refs_dir.glob("*"):
            if filepath.name.startswith("_") or filepath.is_dir():
                continue
            if filepath.suffix.lower() not in [".txt", ".md", ""]:
                continue

            try:
                ref_id = filepath.stem.lower().replace(" ", "-")
                meta = index.get(ref_id, {})
                content = filepath.read_text(encoding="utf-8")

                references.append({
                    "id": ref_id,
                    "title": meta.get("title", filepath.stem),
                    "description": meta.get("description"),
                    "doc_type": meta.get("doc_type", "other"),
                    "use_in_generation": meta.get("use_in_generation", True),
                    "use_in_chat": meta.get("use_in_chat", True),
                    "scope": "series",
                    "word_count": len(content.split()),
                    "content_preview": content[:500] if content else None,
                    "updated_at": datetime.fromtimestamp(filepath.stat().st_mtime).isoformat()
                })
            except Exception:
                continue

        return references
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list references: {str(e)}")


@router.get("/{series_id}/references/{ref_id}")
async def get_series_reference(series_id: str, ref_id: str):
    """Get a series reference document with full content."""
    ensure_series_exists(series_id)
    try:
        refs_dir = settings.series_references_dir(series_id)
        index = _load_refs_index(refs_dir)

        for filepath in refs_dir.glob("*"):
            if filepath.name.startswith("_") or filepath.is_dir():
                continue
            if filepath.stem.lower().replace(" ", "-") == ref_id:
                meta = index.get(ref_id, {})
                content = filepath.read_text(encoding="utf-8")

                return {
                    "id": ref_id,
                    "title": meta.get("title", filepath.stem),
                    "description": meta.get("description"),
                    "doc_type": meta.get("doc_type", "other"),
                    "use_in_generation": meta.get("use_in_generation", True),
                    "use_in_chat": meta.get("use_in_chat", True),
                    "scope": "series",
                    "scope_id": series_id,
                    "content": content,
                    "word_count": len(content.split()),
                    "char_count": len(content)
                }

        raise HTTPException(status_code=404, detail=f"Reference not found: {ref_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get reference: {str(e)}")


@router.post("/{series_id}/references/")
async def create_series_reference(series_id: str, ref_data: dict):
    """Upload a reference document to a series."""
    ensure_series_exists(series_id)
    try:
        refs_dir = settings.series_references_dir(series_id)
        refs_dir.mkdir(parents=True, exist_ok=True)
        index = _load_refs_index(refs_dir)

        title = ref_data.get("title", "reference")
        filename = ref_data.get("filename") or f"{slugify(title)}.md"
        if not filename.endswith((".txt", ".md")):
            filename += ".md"

        filepath = refs_dir / filename
        ref_id = filepath.stem.lower().replace(" ", "-")

        if filepath.exists():
            raise HTTPException(status_code=409, detail=f"Reference already exists: {ref_id}")

        content = ref_data.get("content", "")
        filepath.write_text(content, encoding="utf-8")

        index[ref_id] = {
            "title": title,
            "description": ref_data.get("description"),
            "doc_type": ref_data.get("doc_type", "other"),
            "use_in_generation": ref_data.get("use_in_generation", True),
            "use_in_chat": ref_data.get("use_in_chat", True),
            "filename": filename
        }
        _save_refs_index(refs_dir, index)

        return {
            "id": ref_id,
            "title": title,
            "description": ref_data.get("description"),
            "doc_type": ref_data.get("doc_type", "other"),
            "scope": "series",
            "word_count": len(content.split()),
            "created_at": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create reference: {str(e)}")


@router.put("/{series_id}/references/{ref_id}")
async def update_series_reference(series_id: str, ref_id: str, update_data: dict):
    """Update a series reference document."""
    ensure_series_exists(series_id)
    try:
        refs_dir = settings.series_references_dir(series_id)
        index = _load_refs_index(refs_dir)

        filepath = None
        for fp in refs_dir.glob("*"):
            if fp.name.startswith("_") or fp.is_dir():
                continue
            if fp.stem.lower().replace(" ", "-") == ref_id:
                filepath = fp
                break

        if not filepath:
            raise HTTPException(status_code=404, detail=f"Reference not found: {ref_id}")

        if "content" in update_data and update_data["content"] is not None:
            filepath.write_text(update_data["content"], encoding="utf-8")

        meta = index.get(ref_id, {})
        for key in ["title", "description", "doc_type", "use_in_generation", "use_in_chat"]:
            if key in update_data and update_data[key] is not None:
                meta[key] = update_data[key]

        index[ref_id] = meta
        _save_refs_index(refs_dir, index)

        content = filepath.read_text(encoding="utf-8")
        return {
            "id": ref_id,
            "title": meta.get("title", filepath.stem),
            "description": meta.get("description"),
            "doc_type": meta.get("doc_type", "other"),
            "use_in_generation": meta.get("use_in_generation", True),
            "use_in_chat": meta.get("use_in_chat", True),
            "scope": "series",
            "word_count": len(content.split()),
            "updated_at": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update reference: {str(e)}")


@router.delete("/{series_id}/references/{ref_id}")
async def delete_series_reference(series_id: str, ref_id: str):
    """Delete a reference document from a series."""
    ensure_series_exists(series_id)
    try:
        refs_dir = settings.series_references_dir(series_id)
        index = _load_refs_index(refs_dir)

        filepath = None
        for fp in refs_dir.glob("*"):
            if fp.name.startswith("_") or fp.is_dir():
                continue
            if fp.stem.lower().replace(" ", "-") == ref_id:
                filepath = fp
                break

        if not filepath:
            raise HTTPException(status_code=404, detail=f"Reference not found: {ref_id}")

        filepath.unlink()

        if ref_id in index:
            del index[ref_id]
            _save_refs_index(refs_dir, index)

        return {"message": f"Reference '{ref_id}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete reference: {str(e)}")
