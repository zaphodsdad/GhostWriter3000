"""Reference Library API routes for project-level document storage."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models.reference import (
    ReferenceDocument,
    ReferenceCreate,
    ReferenceUpdate,
    ReferenceSummary,
    ReferenceContent
)

router = APIRouter()


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text


def ensure_project_exists(project_id: str):
    """Check that project exists, raise 404 if not."""
    if not settings.project_dir(project_id).exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")


def _get_refs_dir(project_id: str) -> Path:
    """Get references directory for a project, creating if needed."""
    refs_dir = settings.project_references_dir(project_id)
    refs_dir.mkdir(parents=True, exist_ok=True)
    return refs_dir


def _load_index(refs_dir: Path) -> dict:
    """Load the reference index file."""
    index_file = refs_dir / "_index.json"
    if index_file.exists():
        with open(index_file) as f:
            return json.load(f)
    return {}


def _save_index(refs_dir: Path, index: dict):
    """Save the reference index file."""
    index_file = refs_dir / "_index.json"
    with open(index_file, "w") as f:
        json.dump(index, f, indent=2)


def _build_reference_summary(
    ref_id: str,
    filepath: Path,
    meta: dict,
    scope: str = "project"
) -> ReferenceSummary:
    """Build a ReferenceSummary from file and metadata."""
    content = filepath.read_text(encoding="utf-8")
    word_count = len(content.split())

    return ReferenceSummary(
        id=ref_id,
        title=meta.get("title", filepath.stem),
        description=meta.get("description"),
        doc_type=meta.get("doc_type", "other"),
        use_in_generation=meta.get("use_in_generation", True),
        use_in_chat=meta.get("use_in_chat", True),
        scope=scope,
        word_count=word_count,
        content_preview=content[:500] if content else None,
        created_at=datetime.fromtimestamp(filepath.stat().st_ctime),
        updated_at=datetime.fromtimestamp(filepath.stat().st_mtime)
    )


# List references

@router.get("/", response_model=List[ReferenceSummary])
async def list_references(project_id: str):
    """List all reference documents for a project."""
    ensure_project_exists(project_id)
    try:
        refs_dir = _get_refs_dir(project_id)
        index = _load_index(refs_dir)
        references = []

        for filepath in refs_dir.glob("*"):
            # Skip index file and directories
            if filepath.name.startswith("_") or filepath.is_dir():
                continue

            # Skip non-text files
            if filepath.suffix.lower() not in [".txt", ".md", ""]:
                continue

            try:
                ref_id = slugify(filepath.stem)
                meta = index.get(ref_id, {})
                references.append(_build_reference_summary(ref_id, filepath, meta, "project"))
            except Exception:
                continue

        # Sort by updated time, newest first
        references.sort(key=lambda r: r.updated_at, reverse=True)
        return references
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list references: {str(e)}")


# Get reference

@router.get("/{ref_id}", response_model=ReferenceContent)
async def get_reference(project_id: str, ref_id: str):
    """Get a reference document with full content."""
    ensure_project_exists(project_id)
    try:
        refs_dir = _get_refs_dir(project_id)
        index = _load_index(refs_dir)

        # Find file by ID
        for filepath in refs_dir.glob("*"):
            if filepath.name.startswith("_") or filepath.is_dir():
                continue

            if slugify(filepath.stem) == ref_id:
                meta = index.get(ref_id, {})
                content = filepath.read_text(encoding="utf-8")

                return ReferenceContent(
                    id=ref_id,
                    title=meta.get("title", filepath.stem),
                    description=meta.get("description"),
                    doc_type=meta.get("doc_type", "other"),
                    use_in_generation=meta.get("use_in_generation", True),
                    use_in_chat=meta.get("use_in_chat", True),
                    scope="project",
                    scope_id=project_id,
                    content=content,
                    word_count=len(content.split()),
                    char_count=len(content),
                    created_at=datetime.fromtimestamp(filepath.stat().st_ctime),
                    updated_at=datetime.fromtimestamp(filepath.stat().st_mtime)
                )

        raise HTTPException(status_code=404, detail=f"Reference not found: {ref_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get reference: {str(e)}")


# Create reference

@router.post("/", response_model=ReferenceSummary, status_code=201)
async def create_reference(project_id: str, ref_data: ReferenceCreate):
    """Upload a new reference document."""
    ensure_project_exists(project_id)
    try:
        refs_dir = _get_refs_dir(project_id)
        index = _load_index(refs_dir)

        # Generate filename
        filename = ref_data.filename
        if not filename:
            filename = f"{slugify(ref_data.title)}.md"

        # Ensure .txt or .md extension
        if not filename.endswith((".txt", ".md")):
            filename += ".md"

        filepath = refs_dir / filename
        ref_id = slugify(Path(filename).stem)

        # Check for existing
        if filepath.exists():
            raise HTTPException(status_code=409, detail=f"Reference already exists: {ref_id}")

        # Write content
        filepath.write_text(ref_data.content, encoding="utf-8")

        # Update index with metadata
        index[ref_id] = {
            "title": ref_data.title,
            "description": ref_data.description,
            "doc_type": ref_data.doc_type,
            "use_in_generation": ref_data.use_in_generation,
            "use_in_chat": ref_data.use_in_chat,
            "filename": filename
        }
        _save_index(refs_dir, index)

        return _build_reference_summary(ref_id, filepath, index[ref_id], "project")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create reference: {str(e)}")


# Update reference

@router.put("/{ref_id}", response_model=ReferenceSummary)
async def update_reference(project_id: str, ref_id: str, update_data: ReferenceUpdate):
    """Update a reference document metadata and/or content."""
    ensure_project_exists(project_id)
    try:
        refs_dir = _get_refs_dir(project_id)
        index = _load_index(refs_dir)

        # Find file by ID
        filepath = None
        for fp in refs_dir.glob("*"):
            if fp.name.startswith("_") or fp.is_dir():
                continue
            if slugify(fp.stem) == ref_id:
                filepath = fp
                break

        if not filepath:
            raise HTTPException(status_code=404, detail=f"Reference not found: {ref_id}")

        # Update content if provided
        if update_data.content is not None:
            filepath.write_text(update_data.content, encoding="utf-8")

        # Update metadata
        meta = index.get(ref_id, {})
        if update_data.title is not None:
            meta["title"] = update_data.title
        if update_data.description is not None:
            meta["description"] = update_data.description
        if update_data.doc_type is not None:
            meta["doc_type"] = update_data.doc_type
        if update_data.use_in_generation is not None:
            meta["use_in_generation"] = update_data.use_in_generation
        if update_data.use_in_chat is not None:
            meta["use_in_chat"] = update_data.use_in_chat

        index[ref_id] = meta
        _save_index(refs_dir, index)

        return _build_reference_summary(ref_id, filepath, meta, "project")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update reference: {str(e)}")


# Delete reference

@router.delete("/{ref_id}")
async def delete_reference(project_id: str, ref_id: str):
    """Delete a reference document."""
    ensure_project_exists(project_id)
    try:
        refs_dir = _get_refs_dir(project_id)
        index = _load_index(refs_dir)

        # Find file by ID
        filepath = None
        for fp in refs_dir.glob("*"):
            if fp.name.startswith("_") or fp.is_dir():
                continue
            if slugify(fp.stem) == ref_id:
                filepath = fp
                break

        if not filepath:
            raise HTTPException(status_code=404, detail=f"Reference not found: {ref_id}")

        # Delete file
        filepath.unlink()

        # Remove from index
        if ref_id in index:
            del index[ref_id]
            _save_index(refs_dir, index)

        return {"message": f"Reference '{ref_id}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete reference: {str(e)}")
