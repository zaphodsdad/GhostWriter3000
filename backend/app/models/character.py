"""Character data models."""

from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class Character(BaseModel):
    """Character model parsed from markdown file."""

    id: str = Field(..., description="Unique character identifier")
    filename: str = Field(..., description="Markdown filename")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="YAML frontmatter metadata")
    content: str = Field(..., description="Markdown content body")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "elena-blackwood",
                "filename": "elena-blackwood.md",
                "metadata": {
                    "name": "Elena Blackwood",
                    "age": 28,
                    "role": "protagonist",
                    "personality_traits": ["Curious", "Determined", "Skeptical"]
                },
                "content": "# Elena Blackwood\n\n## Background\nElena grew up...",
                "updated_at": "2026-01-12T10:00:00Z"
            }
        }


class CharacterCreate(BaseModel):
    """Model for creating a new character."""

    filename: str = Field(..., description="Markdown filename (without path)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="YAML frontmatter metadata")
    content: str = Field(..., description="Markdown content body")


class CharacterUpdate(BaseModel):
    """Model for updating a character."""

    metadata: Optional[Dict[str, Any]] = Field(None, description="YAML frontmatter metadata")
    content: Optional[str] = Field(None, description="Markdown content body")
