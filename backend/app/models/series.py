"""Series data models for grouping related books/projects."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
import re


class Series(BaseModel):
    """Series model for grouping related books."""

    id: str = Field(..., description="Unique series identifier (slug)")
    title: str = Field(..., description="Series title", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="Series description/premise")
    author: Optional[str] = Field(None, description="Author name")
    genre: Optional[str] = Field(None, description="Genre")
    total_planned_books: Optional[int] = Field(None, description="Planned number of books in series")
    project_ids: List[str] = Field(default_factory=list, description="Ordered list of project IDs in series")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', v):
            raise ValueError("ID must be a valid slug (lowercase alphanumeric with hyphens)")
        return v


class SeriesCreate(BaseModel):
    """Model for creating a new series."""

    title: str = Field(..., description="Series title", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="Series description/premise")
    author: Optional[str] = Field(None, description="Author name")
    genre: Optional[str] = Field(None, description="Genre")
    total_planned_books: Optional[int] = Field(None, ge=1, description="Planned number of books")


class SeriesUpdate(BaseModel):
    """Model for updating a series."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    author: Optional[str] = None
    genre: Optional[str] = None
    total_planned_books: Optional[int] = Field(None, ge=1)


class SeriesSummary(BaseModel):
    """Summary of a series for listing."""

    id: str
    title: str
    description: Optional[str] = None
    author: Optional[str] = None
    genre: Optional[str] = None
    book_count: int = 0
    total_planned_books: Optional[int] = None
    total_word_count: int = 0
    created_at: datetime
    updated_at: datetime


class AddBookToSeries(BaseModel):
    """Model for adding a project/book to a series."""

    project_id: str = Field(..., description="Project ID to add to series")
    book_number: Optional[int] = Field(None, ge=0, description="Position in series (0 for prequel, auto-assigned if not provided)")


class ReorderBooks(BaseModel):
    """Model for reordering books in a series."""

    project_ids: List[str] = Field(..., description="Ordered list of project IDs")
