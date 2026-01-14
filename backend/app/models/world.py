"""World context data models."""

from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class WorldContext(BaseModel):
    """World context model parsed from markdown file."""

    id: str = Field(..., description="Unique world context identifier")
    filename: str = Field(..., description="Markdown filename")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="YAML frontmatter metadata")
    content: str = Field(..., description="Markdown content body")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "shattered-empire",
                "filename": "shattered-empire.md",
                "metadata": {
                    "name": "The Shattered Empire",
                    "era": "Post-collapse",
                    "technology_level": "Medieval with ancient artifacts"
                },
                "content": "# The Shattered Empire\n\n## History\nTwo centuries ago...",
                "updated_at": "2026-01-12T10:00:00Z"
            }
        }


class WorldContextCreate(BaseModel):
    """Model for creating a new world context."""

    filename: str = Field(..., description="Markdown filename (without path)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="YAML frontmatter metadata")
    content: str = Field(..., description="Markdown content body")


class WorldContextUpdate(BaseModel):
    """Model for updating a world context."""

    metadata: Optional[Dict[str, Any]] = Field(None, description="YAML frontmatter metadata")
    content: Optional[str] = Field(None, description="Markdown content body")
