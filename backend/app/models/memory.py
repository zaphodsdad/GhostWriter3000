"""Series Memory Layer models for persistent context across generations."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class MemoryManifest(BaseModel):
    """Manifest tracking the state of series memory."""

    version: str = Field(default="1.0", description="Memory schema version")
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    # Hashes for staleness detection
    hashes: Dict[str, str] = Field(default_factory=dict, description="SHA256 hashes of source files")

    # Last extraction info
    last_extraction: Optional[datetime] = Field(None, description="When extraction last ran")
    last_extraction_scene: Optional[str] = Field(None, description="Scene ID that triggered last extraction")

    # Summary generation timestamps
    character_states_updated: Optional[datetime] = None
    world_state_updated: Optional[datetime] = None
    timeline_updated: Optional[datetime] = None


class CharacterStateChange(BaseModel):
    """A change to a character's state extracted from a scene."""

    character_id: str = Field(..., description="Character ID (slug)")
    character_name: str = Field(..., description="Character name for display")
    change_type: str = Field(..., description="Type: emotional, physical, relational, knowledge, status")
    description: str = Field(..., description="What changed")
    scene_id: str = Field(..., description="Scene where this was established")
    book_id: str = Field(..., description="Book/project containing the scene")


class WorldFact(BaseModel):
    """A world fact established in a scene."""

    category: str = Field(..., description="Category: location, rule, history, culture, magic, technology")
    fact: str = Field(..., description="The fact established")
    scene_id: str = Field(..., description="Scene where this was established")
    book_id: str = Field(..., description="Book/project containing the scene")


class PlotEvent(BaseModel):
    """A plot event for the timeline."""

    event: str = Field(..., description="What happened")
    characters_involved: List[str] = Field(default_factory=list, description="Character IDs involved")
    significance: str = Field(default="minor", description="minor, moderate, major, climactic")
    scene_id: str = Field(..., description="Scene where this occurred")
    book_id: str = Field(..., description="Book/project containing the scene")
    book_number: Optional[int] = Field(None, description="Book number for ordering")
    chapter_number: Optional[int] = Field(None, description="Chapter number for ordering")
    scene_number: Optional[int] = Field(None, description="Scene number for ordering")


class SceneExtraction(BaseModel):
    """Extraction results from a single scene."""

    scene_id: str
    book_id: str
    extracted_at: datetime = Field(default_factory=datetime.utcnow)

    character_changes: List[CharacterStateChange] = Field(default_factory=list)
    world_facts: List[WorldFact] = Field(default_factory=list)
    plot_events: List[PlotEvent] = Field(default_factory=list)


class SeriesMemory(BaseModel):
    """Complete series memory state."""

    series_id: str
    manifest: MemoryManifest = Field(default_factory=MemoryManifest)

    # Accumulated extractions
    character_changes: List[CharacterStateChange] = Field(default_factory=list)
    world_facts: List[WorldFact] = Field(default_factory=list)
    timeline: List[PlotEvent] = Field(default_factory=list)

    # Generated summaries (compact context for prompts)
    character_states_summary: Optional[str] = Field(None, description="Generated summary of character states")
    world_state_summary: Optional[str] = Field(None, description="Generated summary of world state")
    timeline_summary: Optional[str] = Field(None, description="Generated timeline summary")


class ExtractionRequest(BaseModel):
    """Request to extract memory from a scene."""

    scene_id: str = Field(..., description="Scene to extract from")
    book_id: str = Field(..., description="Book containing the scene")
    prose: str = Field(..., description="Scene prose text")
    scene_summary: Optional[str] = Field(None, description="Scene summary if available")
    chapter_title: Optional[str] = Field(None, description="Chapter title for context")
