"""Data models for the GhostWriter 3000 application."""

from app.models.project import Project, ProjectCreate, ProjectUpdate, ProjectSummary
from app.models.scene import Scene, SceneCreate, SceneUpdate, Beat, BeatCreate, BeatUpdate
from app.models.character import Character, CharacterCreate, CharacterUpdate
from app.models.world import WorldContext, WorldContextCreate, WorldContextUpdate
from app.models.generation import GenerationState, GenerationStatus, Iteration
from app.models.series import Series, SeriesCreate, SeriesUpdate, SeriesSummary
from app.models.reference import ReferenceDocument, ReferenceCreate, ReferenceUpdate, ReferenceSummary

__all__ = [
    # Project
    "Project", "ProjectCreate", "ProjectUpdate", "ProjectSummary",
    # Scene
    "Scene", "SceneCreate", "SceneUpdate",
    # Beat (outline planning)
    "Beat", "BeatCreate", "BeatUpdate",
    # Character
    "Character", "CharacterCreate", "CharacterUpdate",
    # World
    "WorldContext", "WorldContextCreate", "WorldContextUpdate",
    # Generation
    "GenerationState", "GenerationStatus", "Iteration",
    # Series
    "Series", "SeriesCreate", "SeriesUpdate", "SeriesSummary",
    # Reference
    "ReferenceDocument", "ReferenceCreate", "ReferenceUpdate", "ReferenceSummary",
]
