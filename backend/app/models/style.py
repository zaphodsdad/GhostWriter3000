"""Style guide models."""

from typing import Optional
from pydantic import BaseModel, Field


class StyleGuide(BaseModel):
    """Project style guide for prose generation."""

    # Quick reference fields
    pov: Optional[str] = Field(None, description="Point of view (e.g., First Person, Third Limited)")
    tense: Optional[str] = Field(None, description="Tense (e.g., Past, Present)")
    tone: Optional[str] = Field(None, description="Overall tone (e.g., Dark, Light, Humorous)")
    heat_level: Optional[str] = Field(None, description="Heat/spice level for romance")

    # The main style guide content
    guide: str = Field("", description="Full style guide text (markdown)")

    class Config:
        json_schema_extra = {
            "example": {
                "pov": "First Person",
                "tense": "Past",
                "tone": "Dark Romantasy",
                "heat_level": "Tier 2 (Sensual)",
                "guide": "# Style Guide\n\nWrite natural, human-sounding prose..."
            }
        }


class StyleGuideUpdate(BaseModel):
    """Model for updating style guide."""

    pov: Optional[str] = Field(None, description="Point of view")
    tense: Optional[str] = Field(None, description="Tense")
    tone: Optional[str] = Field(None, description="Overall tone")
    heat_level: Optional[str] = Field(None, description="Heat/spice level")
    guide: Optional[str] = Field(None, description="Full style guide text")
