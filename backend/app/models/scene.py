"""Scene outline data models."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class Scene(BaseModel):
    """Scene outline model."""

    id: str = Field(..., description="Unique scene identifier", min_length=1, max_length=100)
    title: str = Field(..., description="Scene title", min_length=1, max_length=200)
    outline: str = Field(..., description="Scene outline/description", min_length=10)

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate scene ID format."""
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("ID must contain only alphanumeric characters, hyphens, and underscores")
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate scene title."""
        if not v.strip():
            raise ValueError("Title cannot be empty or whitespace only")
        return v.strip()

    @field_validator("outline")
    @classmethod
    def validate_outline(cls, v: str) -> str:
        """Validate scene outline."""
        if not v.strip():
            raise ValueError("Outline cannot be empty or whitespace only")
        return v.strip()
    chapter_id: Optional[str] = Field(None, description="Chapter this scene belongs to")
    scene_number: Optional[int] = Field(None, description="Scene number within chapter (for ordering)")
    character_ids: List[str] = Field(default_factory=list, description="List of character IDs involved")
    world_context_ids: List[str] = Field(default_factory=list, description="List of world context IDs")
    previous_scene_ids: List[str] = Field(default_factory=list, description="Previous scene IDs for continuity")
    tags: List[str] = Field(default_factory=list, description="Scene tags")
    additional_notes: Optional[str] = Field(None, description="Additional notes or instructions")
    tone: Optional[str] = Field(None, description="Desired tone for the scene")
    pov: Optional[str] = Field(None, description="Point of view")
    target_length: Optional[str] = Field(None, description="Target word count or length")
    is_canon: bool = Field(False, description="Whether this scene has been accepted as canon")
    prose: Optional[str] = Field(None, description="Final prose (if canon)")
    summary: Optional[str] = Field(None, description="Scene summary (if canon)")

    # Edit mode fields - for revising existing prose instead of generating from scratch
    edit_mode: bool = Field(False, description="Whether this scene is in edit mode (imported prose)")
    original_prose: Optional[str] = Field(None, description="Original imported prose (edit mode only)")
    edit_mode_started_at: Optional[datetime] = Field(None, description="When edit mode was initiated")

    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "scene-001",
                "title": "Discovery in the Wastes",
                "outline": "Elena and her team discover the entrance to the Lost Temple...",
                "character_ids": ["elena-blackwood", "theron-guide"],
                "world_context_ids": ["shattered-empire"],
                "tags": ["discovery", "tension", "cliffhanger"],
                "additional_notes": "Establish physical danger and rivalry with Cult",
                "tone": "Suspenseful with moments of wonder",
                "pov": "Third person limited (Elena's perspective)",
                "target_length": "1500-2000 words",
                "created_at": "2026-01-12T09:00:00Z",
                "updated_at": "2026-01-12T09:30:00Z"
            }
        }


class SceneCreate(BaseModel):
    """Model for creating a new scene."""

    title: str = Field(..., description="Scene title")
    outline: str = Field(..., description="Scene outline/description")
    chapter_id: str = Field(..., description="Chapter this scene belongs to")
    scene_number: Optional[int] = Field(None, description="Scene number within chapter (for ordering)")
    character_ids: List[str] = Field(default_factory=list, description="List of character IDs involved")
    world_context_ids: List[str] = Field(default_factory=list, description="List of world context IDs")
    previous_scene_ids: List[str] = Field(default_factory=list, description="Previous scene IDs for continuity")
    tags: List[str] = Field(default_factory=list, description="Scene tags")
    additional_notes: Optional[str] = Field(None, description="Additional notes or instructions")
    tone: Optional[str] = Field(None, description="Desired tone for the scene")
    pov: Optional[str] = Field(None, description="Point of view")
    target_length: Optional[str] = Field(None, description="Target word count or length")

    # Edit mode - import existing prose instead of generating
    prose: Optional[str] = Field(None, description="Imported prose for edit mode")
    edit_mode: bool = Field(False, description="Start in edit mode with imported prose")


class SceneUpdate(BaseModel):
    """Model for updating a scene."""

    title: Optional[str] = Field(None, description="Scene title")
    outline: Optional[str] = Field(None, description="Scene outline/description")
    chapter_id: Optional[str] = Field(None, description="Chapter this scene belongs to")
    scene_number: Optional[int] = Field(None, description="Scene number within chapter (for ordering)")
    character_ids: Optional[List[str]] = Field(None, description="List of character IDs involved")
    world_context_ids: Optional[List[str]] = Field(None, description="List of world context IDs")
    previous_scene_ids: Optional[List[str]] = Field(None, description="Previous scene IDs for continuity")
    tags: Optional[List[str]] = Field(None, description="Scene tags")
    additional_notes: Optional[str] = Field(None, description="Additional notes or instructions")
    tone: Optional[str] = Field(None, description="Desired tone for the scene")
    pov: Optional[str] = Field(None, description="Point of view")
    target_length: Optional[str] = Field(None, description="Target word count or length")
    prose: Optional[str] = Field(None, description="Scene prose content")
    summary: Optional[str] = Field(None, description="Scene summary for continuity")
    is_canon: Optional[bool] = Field(None, description="Whether scene is accepted as canon")

    # Edit mode fields
    edit_mode: Optional[bool] = Field(None, description="Toggle edit mode")
    original_prose: Optional[str] = Field(None, description="Original imported prose")
