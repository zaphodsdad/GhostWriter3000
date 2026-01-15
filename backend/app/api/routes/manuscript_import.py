"""Manuscript import API endpoints for importing existing prose into the project."""

import io
import re
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import List, Optional

from app.config import settings
from app.utils.file_utils import write_json_file, read_json_file

router = APIRouter()


class ManuscriptPreview(BaseModel):
    """Preview of imported manuscript."""
    filename: str
    format: str
    total_words: int
    total_chars: int
    text_preview: str  # First 2000 chars
    full_text: str


class ChapterSplit(BaseModel):
    """A chapter split from the manuscript."""
    chapter_number: int
    title: str
    content: str
    word_count: int


class ManuscriptSplitPreview(BaseModel):
    """Preview of manuscript split into chapters."""
    chapters: List[ChapterSplit]
    total_chapters: int
    total_words: int


class ImportAsSceneRequest(BaseModel):
    """Request to import manuscript text as a scene in edit mode."""
    text: str = Field(..., description="The manuscript text to import")
    scene_title: str = Field(..., description="Title for the new scene")
    chapter_id: str = Field(..., description="Chapter to create the scene in")
    scene_number: Optional[int] = None


class ImportResult(BaseModel):
    """Result of manuscript import."""
    scene_id: str
    title: str
    word_count: int
    edit_mode: bool
    message: str


class BulkImportRequest(BaseModel):
    """Request to import multiple chapters as scenes."""
    chapters: List[ChapterSplit]
    chapter_id: Optional[str] = Field(None, description="Chapter to create scenes in (legacy)")
    act_id: Optional[str] = Field(None, description="Act to create chapters in (optional)")
    enable_edit_mode: bool = Field(True, description="Enable edit mode for each scene")
    create_chapters: bool = Field(True, description="Create chapters from manuscript structure")


class BulkImportResult(BaseModel):
    """Result of bulk manuscript import."""
    chapters_created: int = 0
    scenes_created: int = 0
    total_words: int = 0
    chapter_ids: List[str] = []
    scene_ids: List[str] = []
    message: str


def ensure_project_exists(project_id: str):
    """Check that project exists, raise 404 if not."""
    if not settings.project_dir(project_id).exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")


def validate_chapter_exists(project_id: str, chapter_id: str):
    """Validate that a chapter exists in the project."""
    chapters_dir = settings.project_dir(project_id) / "chapters"
    chapter_file = chapters_dir / f"{chapter_id}.json"
    if not chapter_file.exists():
        raise HTTPException(status_code=400, detail=f"Chapter not found: {chapter_id}")


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text[:50]  # Limit length


def convert_docx_to_text(file_bytes: bytes) -> str:
    """Convert .docx file to plain text using mammoth."""
    try:
        import mammoth
        result = mammoth.extract_raw_text(io.BytesIO(file_bytes))
        return result.value
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="mammoth library not installed. Run: pip install mammoth"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse .docx file: {str(e)}")


def detect_chapter_splits(text: str) -> List[ChapterSplit]:
    """
    Attempt to split text into chapters based on common patterns.

    Looks for patterns like:
    - "Chapter 1" / "CHAPTER 1" / "Chapter One"
    - "Chapter 1: Title" / "Chapter 1 - Title"
    - "# Chapter 1" (markdown)
    """
    # Pattern to match chapter headings
    chapter_pattern = re.compile(
        r'^(?:#\s*)?(?:CHAPTER|Chapter)\s+(\d+|[A-Za-z]+)(?:\s*[-:]\s*(.+?))?$',
        re.MULTILINE | re.IGNORECASE
    )

    matches = list(chapter_pattern.finditer(text))

    if not matches:
        # No chapter markers found, return entire text as one chapter
        word_count = len(text.split())
        return [ChapterSplit(
            chapter_number=1,
            title="Imported Manuscript",
            content=text.strip(),
            word_count=word_count
        )]

    chapters = []
    for i, match in enumerate(matches):
        # Get chapter number (convert word numbers like "One" to digits)
        chapter_num_str = match.group(1)
        try:
            chapter_num = int(chapter_num_str)
        except ValueError:
            # Try to convert word to number
            word_to_num = {
                'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
                'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
                'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
                'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18,
                'nineteen': 19, 'twenty': 20
            }
            chapter_num = word_to_num.get(chapter_num_str.lower(), i + 1)

        # Get title if present
        title = match.group(2).strip() if match.group(2) else f"Chapter {chapter_num}"

        # Get content (from end of this match to start of next, or end of text)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()

        word_count = len(content.split())

        chapters.append(ChapterSplit(
            chapter_number=chapter_num,
            title=title,
            content=content,
            word_count=word_count
        ))

    return chapters


@router.post("/upload", response_model=ManuscriptPreview)
async def upload_manuscript(
    project_id: str,
    file: UploadFile = File(...)
):
    """
    Upload a manuscript file and get a preview of its contents.

    Supports: .docx, .txt, .md files

    Returns the full text content for client-side processing.
    """
    ensure_project_exists(project_id)

    # Check file extension
    filename = file.filename or "unknown"
    ext = filename.lower().split('.')[-1] if '.' in filename else ''

    if ext not in ['docx', 'txt', 'md', 'markdown']:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: .{ext}. Supported: .docx, .txt, .md"
        )

    try:
        # Read file content
        file_bytes = await file.read()

        # Convert based on format
        if ext == 'docx':
            text = convert_docx_to_text(file_bytes)
            file_format = "docx"
        else:
            # Plain text or markdown
            text = file_bytes.decode('utf-8')
            file_format = "txt" if ext == 'txt' else "markdown"

        # Calculate stats
        total_words = len(text.split())
        total_chars = len(text)
        preview = text[:2000] + ("..." if len(text) > 2000 else "")

        return ManuscriptPreview(
            filename=filename,
            format=file_format,
            total_words=total_words,
            total_chars=total_chars,
            text_preview=preview,
            full_text=text
        )

    except HTTPException:
        raise
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Failed to decode file. Ensure it's UTF-8 encoded.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")


@router.post("/split", response_model=ManuscriptSplitPreview)
async def split_manuscript(
    project_id: str,
    text: str = Form(...)
):
    """
    Split manuscript text into chapters based on chapter markers.

    Looks for patterns like "Chapter 1", "CHAPTER ONE", "Chapter 1: Title", etc.

    Returns a list of chapter splits that can be imported as scenes.
    """
    ensure_project_exists(project_id)

    if not text or len(text.strip()) < 10:
        raise HTTPException(status_code=400, detail="Text is too short to process")

    try:
        chapters = detect_chapter_splits(text)
        total_words = sum(c.word_count for c in chapters)

        return ManuscriptSplitPreview(
            chapters=chapters,
            total_chapters=len(chapters),
            total_words=total_words
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to split manuscript: {str(e)}")


@router.post("/import-scene", response_model=ImportResult)
async def import_as_scene(
    project_id: str,
    request: ImportAsSceneRequest
):
    """
    Import manuscript text as a single scene in edit mode.

    Creates a new scene with the imported text set as original_prose,
    ready for the critique-revision loop.
    """
    ensure_project_exists(project_id)
    validate_chapter_exists(project_id, request.chapter_id)

    try:
        scenes_dir = settings.scenes_dir(project_id)
        scenes_dir.mkdir(parents=True, exist_ok=True)

        # Generate scene ID
        scene_id = slugify(request.scene_title)
        if not scene_id:
            scene_id = f"scene-{datetime.utcnow().timestamp():.0f}"

        filepath = scenes_dir / f"{scene_id}.json"

        # Ensure unique ID
        if filepath.exists():
            scene_id = f"{scene_id}-{int(datetime.utcnow().timestamp())}"
            filepath = scenes_dir / f"{scene_id}.json"

        # Auto-assign scene_number if not provided
        scene_number = request.scene_number
        if scene_number is None:
            existing_count = 0
            for f in scenes_dir.glob("*.json"):
                try:
                    data = await read_json_file(f)
                    if data.get("chapter_id") == request.chapter_id:
                        existing_count += 1
                except:
                    continue
            scene_number = existing_count + 1

        now = datetime.utcnow()
        word_count = len(request.text.split())

        # Create scene in edit mode
        scene_data = {
            "id": scene_id,
            "title": request.scene_title,
            "outline": f"[Imported manuscript - {word_count} words]",
            "chapter_id": request.chapter_id,
            "scene_number": scene_number,
            "character_ids": [],
            "world_context_ids": [],
            "previous_scene_ids": [],
            "tags": ["imported"],
            "additional_notes": None,
            "tone": None,
            "pov": None,
            "target_length": None,
            "is_canon": False,
            "prose": None,
            "summary": None,
            "edit_mode": True,
            "original_prose": request.text,
            "edit_mode_started_at": now.isoformat(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }

        await write_json_file(filepath, scene_data)

        return ImportResult(
            scene_id=scene_id,
            title=request.scene_title,
            word_count=word_count,
            edit_mode=True,
            message=f"Scene created with {word_count} words in edit mode. Ready for critique."
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create scene: {str(e)}")


@router.post("/import-bulk", response_model=BulkImportResult)
async def import_bulk_scenes(
    project_id: str,
    request: BulkImportRequest
):
    """
    Import multiple chapter splits, creating chapters and scenes.

    For each detected chapter in the manuscript:
    - Creates a Chapter in the project structure
    - Creates a Scene within that chapter with the prose in edit mode
    """
    ensure_project_exists(project_id)

    if not request.chapters:
        raise HTTPException(status_code=400, detail="No chapters provided")

    try:
        chapters_dir = settings.project_dir(project_id) / "chapters"
        chapters_dir.mkdir(parents=True, exist_ok=True)
        scenes_dir = settings.scenes_dir(project_id)
        scenes_dir.mkdir(parents=True, exist_ok=True)

        # Get starting chapter number
        existing_chapters = list(chapters_dir.glob("*.json"))
        starting_chapter_num = len(existing_chapters) + 1

        chapter_ids = []
        scene_ids = []
        total_words = 0
        now = datetime.utcnow()

        for i, manuscript_chapter in enumerate(request.chapters):
            chapter_number = starting_chapter_num + i
            word_count = len(manuscript_chapter.content.split())
            total_words += word_count

            # Create Chapter
            chapter_id = slugify(manuscript_chapter.title)
            if not chapter_id:
                chapter_id = f"chapter-{chapter_number}"

            chapter_filepath = chapters_dir / f"{chapter_id}.json"

            # Ensure unique chapter ID
            if chapter_filepath.exists():
                chapter_id = f"{chapter_id}-{int(datetime.utcnow().timestamp())}"
                chapter_filepath = chapters_dir / f"{chapter_id}.json"

            chapter_data = {
                "id": chapter_id,
                "title": manuscript_chapter.title,
                "chapter_number": chapter_number,
                "act_id": request.act_id,  # May be None
                "description": f"Imported from manuscript ({word_count} words)",
                "notes": None,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }

            await write_json_file(chapter_filepath, chapter_data)
            chapter_ids.append(chapter_id)

            # Create Scene within the chapter
            scene_id = f"{chapter_id}-scene-1"
            scene_filepath = scenes_dir / f"{scene_id}.json"

            # Ensure unique scene ID
            if scene_filepath.exists():
                scene_id = f"{scene_id}-{int(datetime.utcnow().timestamp())}"
                scene_filepath = scenes_dir / f"{scene_id}.json"

            scene_data = {
                "id": scene_id,
                "title": f"{manuscript_chapter.title}",
                "outline": f"[Imported manuscript chapter - {word_count} words]",
                "chapter_id": chapter_id,
                "scene_number": 1,
                "character_ids": [],
                "world_context_ids": [],
                "previous_scene_ids": [],
                "tags": ["imported"],
                "additional_notes": None,
                "tone": None,
                "pov": None,
                "target_length": None,
                "is_canon": False,
                "prose": None,
                "summary": None,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }

            # Add edit mode fields if requested
            if request.enable_edit_mode:
                scene_data["edit_mode"] = True
                scene_data["original_prose"] = manuscript_chapter.content
                scene_data["edit_mode_started_at"] = now.isoformat()

            await write_json_file(scene_filepath, scene_data)
            scene_ids.append(scene_id)

        return BulkImportResult(
            chapters_created=len(chapter_ids),
            scenes_created=len(scene_ids),
            total_words=total_words,
            chapter_ids=chapter_ids,
            scene_ids=scene_ids,
            message=f"Created {len(chapter_ids)} chapters and {len(scene_ids)} scenes with {total_words} total words."
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import manuscript: {str(e)}")
