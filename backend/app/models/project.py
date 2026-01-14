"""Project data models."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re


class Project(BaseModel):
    """Project/book model that contains characters, worlds, and scenes."""

    id: str = Field(..., description="Unique project identifier (slug)")
    title: str = Field(..., description="Project title", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="Project description")
    author: Optional[str] = Field(None, description="Author name")
    genre: Optional[str] = Field(None, description="Genre (e.g., Fantasy, Sci-Fi)")

    # Series integration
    series_id: Optional[str] = Field(None, description="Series this project belongs to (if any)")
    book_number: Optional[int] = Field(None, ge=1, description="Book number within series (1, 2, 3...)")

    # Word count goal
    word_count_goal: Optional[int] = Field(None, ge=0, description="Target word count for the project")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate project ID format (slug-friendly)."""
        if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', v):
            raise ValueError("ID must be a valid slug (lowercase alphanumeric with hyphens)")
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate project title."""
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "id": "my-fantasy-novel",
                "title": "My Fantasy Novel",
                "description": "An epic tale of adventure and magic",
                "author": "John Doe",
                "genre": "Fantasy",
                "created_at": "2026-01-13T00:00:00Z",
                "updated_at": "2026-01-13T00:00:00Z"
            }
        }


class ProjectCreate(BaseModel):
    """Model for creating a new project."""

    title: str = Field(..., description="Project title", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="Project description")
    author: Optional[str] = Field(None, description="Author name")
    genre: Optional[str] = Field(None, description="Genre")

    # Series integration (optional - project can be standalone)
    series_id: Optional[str] = Field(None, description="Series to add this project to")
    book_number: Optional[int] = Field(None, ge=1, description="Book number in series")

    # Word count goal
    word_count_goal: Optional[int] = Field(None, ge=0, description="Target word count")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate project title."""
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()


class ProjectUpdate(BaseModel):
    """Model for updating a project."""

    title: Optional[str] = Field(None, description="Project title")
    description: Optional[str] = Field(None, description="Project description")
    author: Optional[str] = Field(None, description="Author name")
    genre: Optional[str] = Field(None, description="Genre")

    # Series integration
    series_id: Optional[str] = Field(None, description="Series this project belongs to")
    book_number: Optional[int] = Field(None, ge=1, description="Book number in series")

    # Word count goal
    word_count_goal: Optional[int] = Field(None, ge=0, description="Target word count")


class ProjectSummary(BaseModel):
    """Summary of a project for listing."""

    id: str
    title: str
    description: Optional[str]
    genre: Optional[str]

    # Series info
    series_id: Optional[str] = None
    book_number: Optional[int] = None

    # Counts
    character_count: int = 0
    world_count: int = 0
    scene_count: int = 0
    canon_scene_count: int = 0
    total_word_count: int = 0
    word_count_goal: Optional[int] = None

    created_at: datetime
    updated_at: datetime
