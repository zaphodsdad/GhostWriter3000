"""Act data model for organizing chapters."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Act(BaseModel):
    """An act within a project (optional organizational layer)."""

    id: str = Field(..., description="Unique act identifier")
    title: str = Field(..., description="Act title", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="Act description/summary")
    act_number: int = Field(..., description="Act order number", ge=1)

    # Enhanced metadata (from structured outline import)
    function: Optional[str] = Field(None, description="Structural function of this act in the story")
    target_word_count: Optional[int] = Field(None, ge=0, description="Target word count for this act")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ActCreate(BaseModel):
    """Request model to create a new act."""

    title: str = Field(..., description="Act title", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="Act description/summary")
    act_number: Optional[int] = Field(None, description="Act order number (auto-assigned if not provided)")

    # Enhanced metadata (from structured outline import)
    function: Optional[str] = Field(None, description="Structural function of this act")
    target_word_count: Optional[int] = Field(None, ge=0, description="Target word count")


class ActUpdate(BaseModel):
    """Request model to update an act."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None)
    act_number: Optional[int] = Field(None, ge=1)

    # Enhanced metadata
    function: Optional[str] = Field(None, description="Structural function of this act")
    target_word_count: Optional[int] = Field(None, ge=0, description="Target word count")


class ActSummary(BaseModel):
    """Summary of an act with chapter count."""

    id: str
    title: str
    description: Optional[str]
    act_number: int
    function: Optional[str] = None
    target_word_count: Optional[int] = None
    chapter_count: int = 0
    scene_count: int = 0
    canon_scene_count: int = 0
