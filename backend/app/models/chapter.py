"""Chapter data model for organizing scenes."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Chapter(BaseModel):
    """A chapter within a project, optionally belonging to an act."""

    id: str = Field(..., description="Unique chapter identifier")
    title: str = Field(..., description="Chapter title", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="Chapter description/summary")
    notes: Optional[str] = Field(None, description="Planning notes for this chapter")
    chapter_number: int = Field(..., description="Chapter order number", ge=1)
    act_id: Optional[str] = Field(None, description="Parent act ID (optional)")

    # Enhanced metadata (from structured outline import)
    pov_pattern: Optional[str] = Field(None, description="POV pattern for chapter (e.g., 'Alternating', 'atla')")
    target_word_count: Optional[int] = Field(None, ge=0, description="Target word count for this chapter")
    function: Optional[str] = Field(None, description="What this chapter accomplishes in the story")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ChapterCreate(BaseModel):
    """Request model to create a new chapter."""

    title: str = Field(..., description="Chapter title", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="Chapter description/summary")
    notes: Optional[str] = Field(None, description="Planning notes")
    chapter_number: Optional[int] = Field(None, description="Chapter order number (auto-assigned if not provided)")
    act_id: Optional[str] = Field(None, description="Parent act ID (optional)")

    # Enhanced metadata (from structured outline import)
    pov_pattern: Optional[str] = Field(None, description="POV pattern for chapter")
    target_word_count: Optional[int] = Field(None, ge=0, description="Target word count")
    function: Optional[str] = Field(None, description="Chapter function in story")


class ChapterUpdate(BaseModel):
    """Request model to update a chapter."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None)
    notes: Optional[str] = Field(None)
    chapter_number: Optional[int] = Field(None, ge=1)
    act_id: Optional[str] = Field(None)

    # Enhanced metadata
    pov_pattern: Optional[str] = Field(None, description="POV pattern for chapter")
    target_word_count: Optional[int] = Field(None, ge=0, description="Target word count")
    function: Optional[str] = Field(None, description="Chapter function in story")


class ChapterSummary(BaseModel):
    """Summary of a chapter with scene count."""

    id: str
    title: str
    description: Optional[str]
    chapter_number: int
    act_id: Optional[str]
    pov_pattern: Optional[str] = None
    target_word_count: Optional[int] = None
    function: Optional[str] = None
    scene_count: int = 0
    canon_scene_count: int = 0
    word_count: int = 0
