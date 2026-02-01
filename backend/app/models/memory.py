"""Series Memory Layer models for persistent context across generations.

Memory Enhancement Features:
- Relevance scoring: Facts weighted by recency, significance, and reference frequency
- Memory decay: Older facts automatically deprioritized based on distance from current book
- Causal chains: Plot events linked by cause and consequence relationships
- Style learning: Track and apply learned writing preferences from user edits
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# Decay Configuration
# ============================================================================

class DecayConfig(BaseModel):
    """Configuration for memory decay calculation."""

    # Book distance decay: relevance = base * (decay_rate ^ book_distance)
    book_distance_decay_rate: float = Field(
        default=0.7,
        description="Decay rate per book distance (0.7 = 30% decay per book)"
    )

    # Significance weights
    significance_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "climactic": 1.0,  # Never decay below 50%
            "major": 0.8,
            "moderate": 0.5,
            "minor": 0.3
        },
        description="Base weight by significance level"
    )

    # Minimum relevance (facts never go below this)
    min_relevance: float = Field(
        default=0.1,
        description="Minimum relevance score (prevents complete forgetting)"
    )

    # Reference boost
    reference_boost: float = Field(
        default=0.1,
        description="Bonus per reference to this fact in later scenes"
    )


class MemoryManifest(BaseModel):
    """Manifest tracking the state of series memory."""

    version: str = Field(default="2.0", description="Memory schema version (2.0 = decay support)")
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

    # Decay configuration
    decay_config: DecayConfig = Field(
        default_factory=DecayConfig,
        description="Configuration for memory decay calculation"
    )
    current_book_number: Optional[int] = Field(
        None,
        description="Current book being written (for decay calculation)"
    )
    last_decay_calculation: Optional[datetime] = Field(
        None,
        description="When decay was last recalculated"
    )

    # Style learning tracking
    style_learning_enabled: bool = Field(
        default=True,
        description="Whether to learn from user edits"
    )
    total_edits_analyzed: int = Field(
        default=0,
        description="Total number of user edits analyzed"
    )
    last_style_learning: Optional[datetime] = Field(
        None,
        description="When style preferences were last updated"
    )


class CharacterStateChange(BaseModel):
    """A change to a character's state extracted from a scene."""

    character_id: str = Field(..., description="Character ID (slug)")
    character_name: str = Field(..., description="Character name for display")
    change_type: str = Field(..., description="Type: emotional, physical, relational, knowledge, status")
    description: str = Field(..., description="What changed")
    scene_id: str = Field(..., description="Scene where this was established")
    book_id: str = Field(..., description="Book/project containing the scene")

    # Decay/relevance fields
    book_number: Optional[int] = Field(None, description="Book number for decay calculation")
    relevance_score: float = Field(
        default=1.0,
        description="Current relevance (0.0-1.0), decays based on recency"
    )
    reference_count: int = Field(
        default=0,
        description="Times this fact was referenced in later scenes"
    )
    last_referenced: Optional[datetime] = Field(
        None,
        description="When this fact was last referenced in generation"
    )


class WorldFact(BaseModel):
    """A world fact established in a scene."""

    category: str = Field(..., description="Category: location, rule, history, culture, magic, technology")
    fact: str = Field(..., description="The fact established")
    scene_id: str = Field(..., description="Scene where this was established")
    book_id: str = Field(..., description="Book/project containing the scene")

    # Decay/relevance fields
    book_number: Optional[int] = Field(None, description="Book number for decay calculation")
    relevance_score: float = Field(
        default=1.0,
        description="Current relevance (0.0-1.0), decays based on recency"
    )
    reference_count: int = Field(
        default=0,
        description="Times this fact was referenced in later scenes"
    )
    is_foundational: bool = Field(
        default=False,
        description="If True, never decays below 0.5 (core world rules)"
    )


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

    # Decay/relevance fields
    relevance_score: float = Field(
        default=1.0,
        description="Current relevance (0.0-1.0), decays based on recency and significance"
    )
    reference_count: int = Field(
        default=0,
        description="Times this event was referenced in later scenes"
    )

    # Causal chain fields
    event_id: Optional[str] = Field(
        None,
        description="Unique event ID for causal linking (auto-generated if not provided)"
    )
    causes: List[str] = Field(
        default_factory=list,
        description="Event IDs that caused/led to this event"
    )
    consequences: List[str] = Field(
        default_factory=list,
        description="Event IDs that resulted from this event"
    )
    causal_summary: Optional[str] = Field(
        None,
        description="Brief explanation of WHY this happened (causal narrative)"
    )


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


# ============================================================================
# Style Learning Models
# ============================================================================

class StylePreference(BaseModel):
    """A learned writing preference from user edits."""

    category: str = Field(
        ...,
        description="Category: vocabulary, sentence_structure, dialogue, pacing, description, tone"
    )
    preference: str = Field(..., description="The learned preference/rule")
    confidence: float = Field(
        default=0.5,
        description="Confidence (0.0-1.0), increases with more examples"
    )
    examples: List[str] = Field(
        default_factory=list,
        description="Example corrections that taught this preference"
    )
    learned_from_count: int = Field(
        default=1,
        description="Number of edits that reinforced this preference"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_reinforced: datetime = Field(default_factory=datetime.utcnow)


class EditAnalysis(BaseModel):
    """Analysis of a user edit for style learning."""

    scene_id: str = Field(..., description="Scene that was edited")
    book_id: str = Field(..., description="Book containing the scene")
    original_text: str = Field(..., description="Text before user edit")
    edited_text: str = Field(..., description="Text after user edit")
    edit_type: str = Field(
        ...,
        description="Type: word_change, sentence_restructure, deletion, addition, dialogue_change"
    )
    detected_pattern: Optional[str] = Field(
        None,
        description="Pattern detected (e.g., 'removes adverbs', 'shortens sentences')"
    )
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class StyleMemory(BaseModel):
    """Accumulated style preferences for a series."""

    series_id: str = Field(..., description="Series these preferences apply to")
    preferences: List[StylePreference] = Field(
        default_factory=list,
        description="Learned style preferences"
    )
    edit_history: List[EditAnalysis] = Field(
        default_factory=list,
        description="History of analyzed edits (for learning)"
    )
    last_learned: Optional[datetime] = Field(
        None,
        description="When preferences were last updated from edits"
    )

    # Vocabulary tracking
    preferred_vocabulary: Dict[str, str] = Field(
        default_factory=dict,
        description="Word replacements learned (original -> preferred)"
    )
    avoided_vocabulary: List[str] = Field(
        default_factory=list,
        description="Words the author consistently removes"
    )

    def get_preferences_summary(self) -> str:
        """Generate a summary of learned preferences for prompts."""
        if not self.preferences:
            return ""

        lines = ["## Learned Style Preferences (from author edits)\n"]

        # Group by category
        by_category: Dict[str, List[StylePreference]] = {}
        for pref in self.preferences:
            if pref.category not in by_category:
                by_category[pref.category] = []
            by_category[pref.category].append(pref)

        for category, prefs in by_category.items():
            # Only include preferences with decent confidence
            confident_prefs = [p for p in prefs if p.confidence >= 0.5]
            if confident_prefs:
                lines.append(f"**{category.replace('_', ' ').title()}:**")
                for pref in sorted(confident_prefs, key=lambda x: -x.confidence)[:5]:
                    lines.append(f"- {pref.preference}")
                lines.append("")

        # Add vocabulary if significant
        if self.preferred_vocabulary:
            lines.append("**Vocabulary Preferences:**")
            for orig, pref in list(self.preferred_vocabulary.items())[:10]:
                lines.append(f"- Use \"{pref}\" instead of \"{orig}\"")
            lines.append("")

        if self.avoided_vocabulary:
            lines.append(f"**Avoid these words:** {', '.join(self.avoided_vocabulary[:10])}")
            lines.append("")

        return "\n".join(lines) if len(lines) > 1 else ""
