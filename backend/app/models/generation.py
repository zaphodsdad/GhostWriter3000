"""Generation pipeline data models."""

from datetime import datetime
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class GenerationStatus(str, Enum):
    """Generation pipeline status."""

    QUEUED = "queued"  # Waiting in batch queue, not yet started
    INITIALIZED = "initialized"
    GENERATING = "generating"
    GENERATION_COMPLETE = "generation_complete"
    CRITIQUING = "critiquing"
    AWAITING_APPROVAL = "awaiting_approval"
    REVISING = "revising"
    GENERATING_SUMMARY = "generating_summary"  # NEW: Creating scene summary
    COMPLETED = "completed"
    REJECTED = "rejected"
    ERROR = "error"


class Iteration(BaseModel):
    """Single iteration in the generation pipeline."""

    iteration_number: int = Field(..., description="Iteration number (1-indexed)")
    prose: str = Field(..., description="Generated prose text")
    critique: Optional[str] = Field(None, description="Critique of the prose")
    approved: Optional[bool] = Field(None, description="Whether user approved this iteration")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When this iteration was created")


class GenerationState(BaseModel):
    """Complete state of a generation pipeline."""

    generation_id: str = Field(..., description="Unique generation identifier")
    project_id: str = Field(..., description="Project this generation belongs to")
    scene_id: str = Field(..., description="Scene being generated")
    status: GenerationStatus = Field(..., description="Current pipeline status")
    current_iteration: int = Field(0, description="Current iteration number")
    max_iterations: int = Field(5, description="Maximum allowed iterations")
    character_ids: List[str] = Field(default_factory=list, description="Character IDs used")
    world_context_ids: List[str] = Field(default_factory=list, description="World context IDs used")
    previous_scene_ids: List[str] = Field(default_factory=list, description="Previous scene IDs for continuity")
    generation_model: Optional[str] = Field(None, description="Model used for prose generation")
    critique_model: Optional[str] = Field(None, description="Model used for critique")
    edit_mode: bool = Field(False, description="Whether this is an edit mode generation (started with existing prose)")
    revision_mode: str = Field("full", description="Revision approach: 'full' (structural) or 'polish' (line-edits)")
    iterations: List[Iteration] = Field(default_factory=list, description="List of all iterations")
    final_prose: Optional[str] = Field(None, description="Final accepted prose (when status=COMPLETED)")
    scene_summary: Optional[str] = Field(None, description="Auto-generated scene summary (when status=COMPLETED)")
    error_message: Optional[str] = Field(None, description="Error message if status is ERROR")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When generation started")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    @property
    def current_prose(self) -> Optional[str]:
        """Get the prose from the current iteration."""
        if not self.iterations:
            return None
        return self.iterations[-1].prose

    @property
    def current_critique(self) -> Optional[str]:
        """Get the critique from the current iteration."""
        if not self.iterations:
            return None
        return self.iterations[-1].critique

    @property
    def can_revise(self) -> bool:
        """Check if another revision is possible."""
        return self.current_iteration < self.max_iterations and self.status == GenerationStatus.AWAITING_APPROVAL

    class Config:
        json_schema_extra = {
            "example": {
                "generation_id": "gen-123",
                "scene_id": "scene-001",
                "status": "awaiting_approval",
                "current_iteration": 2,
                "max_iterations": 5,
                "character_ids": ["elena-blackwood"],
                "world_context_ids": ["shattered-empire"],
                "iterations": [
                    {
                        "iteration_number": 1,
                        "prose": "The desert sun beat down mercilessly...",
                        "critique": "Good opening, but pacing could be improved...",
                        "approved": True,
                        "timestamp": "2026-01-12T10:00:00Z"
                    },
                    {
                        "iteration_number": 2,
                        "prose": "Revised version with better pacing...",
                        "critique": "Much improved. Consider adding more sensory details...",
                        "approved": None,
                        "timestamp": "2026-01-12T10:05:00Z"
                    }
                ],
                "created_at": "2026-01-12T09:55:00Z",
                "updated_at": "2026-01-12T10:05:00Z"
            }
        }


class GenerationStart(BaseModel):
    """Request model to start a new generation."""

    scene_id: str = Field(..., description="Scene ID to generate prose for")
    max_iterations: int = Field(5, description="Maximum allowed iterations", ge=1, le=100)
    generation_model: Optional[str] = Field(None, description="Model for prose generation (uses .env default if not specified)")
    critique_model: Optional[str] = Field(None, description="Model for critique (uses .env default if not specified)")
    revision_mode: str = Field("full", description="Revision approach: 'full' (structural) or 'polish' (line-edits)")


class EditModeStart(BaseModel):
    """Request model to start edit mode generation (skip to critique)."""

    scene_id: str = Field(..., description="Scene ID with imported prose to edit")
    max_iterations: int = Field(5, description="Maximum allowed iterations", ge=1, le=100)
    generation_model: Optional[str] = Field(None, description="Model for revisions (uses .env default if not specified)")
    critique_model: Optional[str] = Field(None, description="Model for critique (uses .env default if not specified)")
    revision_mode: str = Field("full", description="Revision approach: 'full' (structural) or 'polish' (line-edits)")


class StartWithCritiqueRequest(BaseModel):
    """Request model to start revision with an existing critique (skip critique step)."""

    scene_id: str = Field(..., description="Scene ID to revise")
    critique: str = Field(..., description="Existing critique from evaluate endpoint")
    max_iterations: int = Field(5, description="Maximum allowed iterations", ge=1, le=100)
    generation_model: Optional[str] = Field(None, description="Model for revisions")
    revision_mode: str = Field("full", description="Revision approach: 'full' or 'polish'")


class GenerationResponse(BaseModel):
    """Response model for generation state."""

    generation_id: str
    project_id: str
    scene_id: str
    status: GenerationStatus
    current_iteration: int
    max_iterations: int
    can_revise: bool
    revision_mode: str = "full"
    current_prose: Optional[str]
    current_critique: Optional[str]
    final_prose: Optional[str]
    scene_summary: Optional[str]
    history: List[Iteration]
    created_at: datetime
    updated_at: datetime
