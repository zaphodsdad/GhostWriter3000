"""Series Memory Service - manages persistent context across generations."""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from app.models.memory import (
    MemoryManifest,
    SeriesMemory,
    SceneExtraction,
    CharacterStateChange,
    WorldFact,
    PlotEvent,
    ExtractionRequest,
    DecayConfig,
    StylePreference,
    StyleMemory,
    BookSummary,
)
from app.config import settings
from app.utils.prompt_templates import extract_json


class MemoryService:
    """Service for managing series memory layer."""

    def __init__(self):
        pass

    def _memory_dir(self, series_id: str) -> Path:
        """Get the memory directory for a series."""
        return settings.series_path(series_id) / "memory"

    def _ensure_memory_dir(self, series_id: str) -> Path:
        """Ensure memory directory exists and return path."""
        memory_dir = self._memory_dir(series_id)
        memory_dir.mkdir(parents=True, exist_ok=True)
        (memory_dir / "extractions").mkdir(exist_ok=True)
        return memory_dir

    def _manifest_path(self, series_id: str) -> Path:
        """Get path to manifest.json."""
        return self._memory_dir(series_id) / "manifest.json"

    def _load_manifest(self, series_id: str) -> MemoryManifest:
        """Load or create manifest for a series."""
        manifest_path = self._manifest_path(series_id)
        if manifest_path.exists():
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            return MemoryManifest(**data)
        return MemoryManifest()

    def _save_manifest(self, series_id: str, manifest: MemoryManifest):
        """Save manifest to disk."""
        self._ensure_memory_dir(series_id)
        manifest.last_updated = datetime.utcnow()
        manifest_path = self._manifest_path(series_id)
        manifest_path.write_text(
            json.dumps(manifest.model_dump(), default=str, indent=2),
            encoding="utf-8"
        )

    def initialize_memory(self, series_id: str) -> SeriesMemory:
        """Initialize memory structure for a series."""
        memory_dir = self._ensure_memory_dir(series_id)

        # Create initial empty files
        manifest = MemoryManifest()
        self._save_manifest(series_id, manifest)

        # Create empty state files
        (memory_dir / "character_states.md").write_text(
            "# Character States\n\n*No character states recorded yet.*\n",
            encoding="utf-8"
        )
        (memory_dir / "world_state.md").write_text(
            "# World State\n\n*No world facts recorded yet.*\n",
            encoding="utf-8"
        )
        (memory_dir / "timeline.md").write_text(
            "# Timeline\n\n*No plot events recorded yet.*\n",
            encoding="utf-8"
        )

        return SeriesMemory(series_id=series_id, manifest=manifest)

    def get_memory(self, series_id: str) -> Optional[SeriesMemory]:
        """Get the complete memory state for a series."""
        memory_dir = self._memory_dir(series_id)
        if not memory_dir.exists():
            return None

        manifest = self._load_manifest(series_id)

        # Load accumulated data
        memory = SeriesMemory(series_id=series_id, manifest=manifest)

        # Load extractions from all extraction files
        extractions_dir = memory_dir / "extractions"
        if extractions_dir.exists():
            for extraction_file in sorted(extractions_dir.glob("*.json")):
                data = json.loads(extraction_file.read_text(encoding="utf-8"))
                extraction = SceneExtraction(**data)
                memory.character_changes.extend(extraction.character_changes)
                memory.world_facts.extend(extraction.world_facts)
                memory.timeline.extend(extraction.plot_events)

        # Sort timeline by book/chapter/scene order
        memory.timeline.sort(key=lambda e: (
            e.book_number or 999,
            e.chapter_number or 999,
            e.scene_number or 999
        ))

        # Load generated summaries
        char_states_path = memory_dir / "character_states.md"
        if char_states_path.exists():
            memory.character_states_summary = char_states_path.read_text(encoding="utf-8")

        world_state_path = memory_dir / "world_state.md"
        if world_state_path.exists():
            memory.world_state_summary = world_state_path.read_text(encoding="utf-8")

        timeline_path = memory_dir / "timeline.md"
        if timeline_path.exists():
            memory.timeline_summary = timeline_path.read_text(encoding="utf-8")

        return memory

    def save_extraction(self, series_id: str, extraction: SceneExtraction):
        """Save an extraction result."""
        memory_dir = self._ensure_memory_dir(series_id)
        extractions_dir = memory_dir / "extractions"
        extractions_dir.mkdir(exist_ok=True)

        # Save extraction with scene ID as filename
        extraction_path = extractions_dir / f"{extraction.book_id}_{extraction.scene_id}.json"
        extraction_path.write_text(
            json.dumps(extraction.model_dump(), default=str, indent=2),
            encoding="utf-8"
        )

        # Update manifest
        manifest = self._load_manifest(series_id)
        manifest.last_extraction = datetime.utcnow()
        manifest.last_extraction_scene = extraction.scene_id
        self._save_manifest(series_id, manifest)

    def update_character_states(self, series_id: str, summary: str):
        """Update the character states summary."""
        memory_dir = self._ensure_memory_dir(series_id)
        (memory_dir / "character_states.md").write_text(summary, encoding="utf-8")

        manifest = self._load_manifest(series_id)
        manifest.character_states_updated = datetime.utcnow()
        self._save_manifest(series_id, manifest)

    def update_world_state(self, series_id: str, summary: str):
        """Update the world state summary."""
        memory_dir = self._ensure_memory_dir(series_id)
        (memory_dir / "world_state.md").write_text(summary, encoding="utf-8")

        manifest = self._load_manifest(series_id)
        manifest.world_state_updated = datetime.utcnow()
        self._save_manifest(series_id, manifest)

    def update_timeline(self, series_id: str, summary: str):
        """Update the timeline summary."""
        memory_dir = self._ensure_memory_dir(series_id)
        (memory_dir / "timeline.md").write_text(summary, encoding="utf-8")

        manifest = self._load_manifest(series_id)
        manifest.timeline_updated = datetime.utcnow()
        self._save_manifest(series_id, manifest)

    def compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of a file."""
        if not file_path.exists():
            return ""
        content = file_path.read_bytes()
        return hashlib.sha256(content).hexdigest()[:16]

    def check_staleness(self, series_id: str) -> Dict[str, bool]:
        """Check which summaries are stale (source files changed)."""
        memory_dir = self._memory_dir(series_id)
        if not memory_dir.exists():
            return {"characters": True, "world": True, "all": True}

        manifest = self._load_manifest(series_id)
        series_dir = settings.series_path(series_id)

        stale = {}

        # Check character files
        char_dir = series_dir / "characters"
        if char_dir.exists():
            current_hashes = {}
            for char_file in char_dir.glob("*.md"):
                current_hashes[char_file.name] = self.compute_file_hash(char_file)

            stored_char_hashes = {k: v for k, v in manifest.hashes.items() if k.startswith("char_")}
            expected = {f"char_{k}": v for k, v in current_hashes.items()}
            stale["characters"] = stored_char_hashes != expected
        else:
            stale["characters"] = False

        # Check world files
        world_dir = series_dir / "world"
        if world_dir.exists():
            current_hashes = {}
            for world_file in world_dir.glob("*.md"):
                current_hashes[world_file.name] = self.compute_file_hash(world_file)

            stored_world_hashes = {k: v for k, v in manifest.hashes.items() if k.startswith("world_")}
            expected = {f"world_{k}": v for k, v in current_hashes.items()}
            stale["world"] = stored_world_hashes != expected
        else:
            stale["world"] = False

        stale["all"] = stale.get("characters", False) or stale.get("world", False)

        return stale

    def update_hashes(self, series_id: str):
        """Update stored hashes for all source files."""
        manifest = self._load_manifest(series_id)
        series_dir = settings.series_path(series_id)

        new_hashes = {}

        # Hash character files
        char_dir = series_dir / "characters"
        if char_dir.exists():
            for char_file in char_dir.glob("*.md"):
                new_hashes[f"char_{char_file.name}"] = self.compute_file_hash(char_file)

        # Hash world files
        world_dir = series_dir / "world"
        if world_dir.exists():
            for world_file in world_dir.glob("*.md"):
                new_hashes[f"world_{world_file.name}"] = self.compute_file_hash(world_file)

        manifest.hashes = new_hashes
        self._save_manifest(series_id, manifest)

    def clear_memory(self, series_id: str):
        """Clear all memory for a series (keeps directory structure)."""
        memory_dir = self._memory_dir(series_id)
        if not memory_dir.exists():
            return

        # Clear extractions
        extractions_dir = memory_dir / "extractions"
        if extractions_dir.exists():
            for f in extractions_dir.glob("*.json"):
                f.unlink()

        # Reset state files
        (memory_dir / "character_states.md").write_text(
            "# Character States\n\n*No character states recorded yet.*\n",
            encoding="utf-8"
        )
        (memory_dir / "world_state.md").write_text(
            "# World State\n\n*No world facts recorded yet.*\n",
            encoding="utf-8"
        )
        (memory_dir / "timeline.md").write_text(
            "# Timeline\n\n*No plot events recorded yet.*\n",
            encoding="utf-8"
        )

        # Reset manifest
        manifest = MemoryManifest()
        self._save_manifest(series_id, manifest)

    def get_context_for_generation(
        self,
        series_id: str,
        current_book_number: Optional[int] = None,
        apply_decay: bool = True
    ) -> Dict[str, str]:
        """Get compact context summaries for use in generation prompts.

        Args:
            series_id: Series ID
            current_book_number: Book currently being written (for decay calculation)
            apply_decay: Whether to apply memory decay (filter low-relevance facts)

        Returns:
            Dict with character_states, world_state, timeline summaries
        """
        memory = self.get_memory(series_id)
        if not memory:
            return {}

        # If decay is enabled and we have a current book, recalculate relevance
        if apply_decay and current_book_number is not None:
            self._apply_decay_to_memory(memory, current_book_number)

        context = {}

        if memory.character_states_summary:
            context["character_states"] = memory.character_states_summary

        if memory.world_state_summary:
            context["world_state"] = memory.world_state_summary

        if memory.timeline_summary:
            context["timeline"] = memory.timeline_summary

        return context

    def _apply_decay_to_memory(
        self,
        memory: SeriesMemory,
        current_book_number: int
    ):
        """Apply decay calculation to all memory items.

        Modifies relevance_score on each item based on:
        - Distance from current book
        - Significance level
        - Reference frequency
        """
        config = memory.manifest.decay_config

        # Apply decay to character changes
        for change in memory.character_changes:
            change.relevance_score = self._calculate_relevance(
                book_number=change.book_number,
                current_book=current_book_number,
                significance="moderate",  # Character changes are moderate by default
                reference_count=change.reference_count,
                config=config,
                is_foundational=False
            )

        # Apply decay to world facts
        for fact in memory.world_facts:
            fact.relevance_score = self._calculate_relevance(
                book_number=fact.book_number,
                current_book=current_book_number,
                significance="moderate",
                reference_count=fact.reference_count,
                config=config,
                is_foundational=fact.is_foundational
            )

        # Apply decay to timeline events
        for event in memory.timeline:
            event.relevance_score = self._calculate_relevance(
                book_number=event.book_number,
                current_book=current_book_number,
                significance=event.significance,
                reference_count=event.reference_count,
                config=config,
                is_foundational=False
            )

    def _calculate_relevance(
        self,
        book_number: Optional[int],
        current_book: int,
        significance: str,
        reference_count: int,
        config: DecayConfig,
        is_foundational: bool = False
    ) -> float:
        """Calculate relevance score for a memory item.

        Formula:
            base_weight = significance_weight
            distance_decay = decay_rate ^ book_distance
            reference_boost = reference_count * boost_per_reference
            relevance = max(min_relevance, base_weight * distance_decay + reference_boost)

        Args:
            book_number: Book where this was established
            current_book: Current book being written
            significance: minor, moderate, major, climactic
            reference_count: Times referenced in later scenes
            config: Decay configuration
            is_foundational: If True, never decays below 0.5

        Returns:
            Relevance score (0.0-1.0)
        """
        # Get base weight from significance
        base_weight = config.significance_weights.get(significance, 0.5)

        # Calculate book distance (if unknown, assume 0 distance)
        if book_number is None:
            book_distance = 0
        else:
            book_distance = max(0, current_book - book_number)

        # Apply distance decay
        distance_decay = config.book_distance_decay_rate ** book_distance

        # Calculate reference boost
        reference_boost = reference_count * config.reference_boost

        # Combine: base relevance + reference boost
        relevance = (base_weight * distance_decay) + reference_boost

        # Apply minimum relevance (foundational facts have higher minimum)
        min_rel = 0.5 if is_foundational else config.min_relevance

        # Clamp to [min_relevance, 1.0]
        return max(min_rel, min(1.0, relevance))

    def get_filtered_memory(
        self,
        series_id: str,
        current_book_number: int,
        min_relevance: float = 0.3
    ) -> SeriesMemory:
        """Get memory filtered by relevance threshold.

        Returns only items with relevance_score >= min_relevance.
        Useful for token optimization - drop low-relevance facts.

        Args:
            series_id: Series ID
            current_book_number: Current book being written
            min_relevance: Minimum relevance score to include (0.0-1.0)

        Returns:
            SeriesMemory with filtered items
        """
        memory = self.get_memory(series_id)
        if not memory:
            return None

        # Apply decay calculation
        self._apply_decay_to_memory(memory, current_book_number)

        # Filter by relevance
        memory.character_changes = [
            c for c in memory.character_changes
            if c.relevance_score >= min_relevance
        ]
        memory.world_facts = [
            f for f in memory.world_facts
            if f.relevance_score >= min_relevance
        ]
        memory.timeline = [
            e for e in memory.timeline
            if e.relevance_score >= min_relevance
        ]

        return memory

    def set_current_book(self, series_id: str, book_number: int):
        """Set the current book number for decay calculation."""
        manifest = self._load_manifest(series_id)
        manifest.current_book_number = book_number
        self._save_manifest(series_id, manifest)

    def update_decay_config(self, series_id: str, config: DecayConfig):
        """Update the decay configuration for a series."""
        manifest = self._load_manifest(series_id)
        manifest.decay_config = config
        self._save_manifest(series_id, manifest)

    def increment_reference_count(
        self,
        series_id: str,
        scene_id: str,
        book_id: str,
        item_type: str,
        item_index: int
    ):
        """Increment reference count for a memory item.

        Call this when a fact is referenced in generation context.
        Helps boost relevance of frequently-used facts.
        """
        memory_dir = self._memory_dir(series_id)
        extraction_path = memory_dir / "extractions" / f"{book_id}_{scene_id}.json"

        if not extraction_path.exists():
            return

        data = json.loads(extraction_path.read_text(encoding="utf-8"))

        if item_type == "character_change" and item_index < len(data.get("character_changes", [])):
            data["character_changes"][item_index]["reference_count"] = \
                data["character_changes"][item_index].get("reference_count", 0) + 1
            data["character_changes"][item_index]["last_referenced"] = datetime.utcnow().isoformat()

        elif item_type == "world_fact" and item_index < len(data.get("world_facts", [])):
            data["world_facts"][item_index]["reference_count"] = \
                data["world_facts"][item_index].get("reference_count", 0) + 1

        elif item_type == "plot_event" and item_index < len(data.get("plot_events", [])):
            data["plot_events"][item_index]["reference_count"] = \
                data["plot_events"][item_index].get("reference_count", 0) + 1

        extraction_path.write_text(
            json.dumps(data, default=str, indent=2),
            encoding="utf-8"
        )

    async def get_context_with_auto_refresh(
        self,
        series_id: str,
        auto_regenerate: bool = True,
        current_book_number: Optional[int] = None,
        apply_decay: bool = True
    ) -> Dict[str, str]:
        """
        Get context for generation, optionally auto-regenerating stale summaries.

        Args:
            series_id: Series ID
            auto_regenerate: If True, check staleness and regenerate if needed
            current_book_number: Book currently being written (for decay calculation)
            apply_decay: Whether to apply memory decay (filter low-relevance facts)

        Returns:
            Dict with character_states, world_state, timeline summaries
        """
        if auto_regenerate:
            staleness = self.check_staleness(series_id)
            if staleness.get("all", False):
                # Source files have changed, regenerate summaries
                try:
                    from app.utils.logging import get_logger
                    logger = get_logger(__name__)
                    logger.info(
                        f"Auto-regenerating stale memory summaries for series {series_id}",
                        extra={"staleness": staleness}
                    )
                    # Pass current_book_number for decay-aware summary generation
                    await self.generate_summaries(
                        series_id,
                        current_book_number=current_book_number
                    )
                except Exception as e:
                    # Don't fail generation if auto-regeneration fails
                    from app.utils.logging import get_logger
                    logger = get_logger(__name__)
                    logger.warning(
                        f"Failed to auto-regenerate summaries for {series_id}: {e}"
                    )

        return self.get_context_for_generation(
            series_id,
            current_book_number=current_book_number,
            apply_decay=apply_decay
        )

    async def extract_from_scene(
        self,
        series_id: str,
        book_id: str,
        scene_id: str,
        prose: str,
        scene_title: Optional[str] = None,
        chapter_title: Optional[str] = None,
        book_number: Optional[int] = None,
        chapter_number: Optional[int] = None,
        scene_number: Optional[int] = None,
        character_names: Optional[List[str]] = None,
        model: Optional[str] = None
    ) -> SceneExtraction:
        """
        Extract memory facts from a scene using LLM.

        Called when marking a scene as canon. Extracts:
        - Character state changes (emotional, physical, relational, knowledge, status)
        - World facts established (locations, rules, history, culture)
        - Plot events for timeline

        Args:
            series_id: Series this scene belongs to
            book_id: Book/project containing the scene
            scene_id: Scene ID
            prose: The scene prose text
            scene_title: Optional scene title for context
            chapter_title: Optional chapter title for context
            book_number: Book position in series (for timeline ordering)
            chapter_number: Chapter position (for timeline ordering)
            scene_number: Scene position (for timeline ordering)
            character_names: Known character names to help extraction
            model: Optional model override

        Returns:
            SceneExtraction with extracted facts
        """
        from app.services.llm_service import get_llm_service
        llm = get_llm_service()

        # Build context hints
        context_parts = []
        if scene_title:
            context_parts.append(f"Scene: {scene_title}")
        if chapter_title:
            context_parts.append(f"Chapter: {chapter_title}")
        context_hint = " | ".join(context_parts) if context_parts else ""

        char_hint = ""
        if character_names:
            char_hint = f"\n\nKnown characters in this series: {', '.join(character_names)}"

        system_prompt = """You are a literary analyst extracting narrative facts for continuity tracking.
Analyze the provided scene and extract factual changes that matter for story continuity.
Be specific and factual. Only extract things that are explicitly established in the text.
Output valid JSON only, no markdown formatting or explanation."""

        user_prompt = f"""Analyze this scene and extract continuity-relevant facts.
{context_hint}
{char_hint}

Extract three types of information:

1. CHARACTER STATE CHANGES - How characters changed in this scene:
   - emotional: Mood/emotional state changes
   - physical: Injuries, appearance changes, fatigue
   - relational: Relationship changes with other characters
   - knowledge: What they learned or discovered
   - status: Role changes, power shifts, new responsibilities

2. WORLD FACTS - New information established about the world:
   - location: New places described or details about existing places
   - rule: Rules of magic, society, physics established
   - history: Historical events mentioned
   - culture: Cultural practices, beliefs, customs
   - technology/magic: How things work
   - is_foundational: True if this is a core world rule that should always be remembered

3. PLOT EVENTS - Significant story events (for timeline):
   - What happened (brief, factual)
   - Who was involved
   - Significance: minor, moderate, major, or climactic
   - CAUSAL CHAINS: For each event, identify:
     - WHY it happened (what caused it)
     - What it might lead to (potential consequences)
   - Give each event a unique ID like "evt_scene_N" for linking

Output as JSON:
{{
  "character_changes": [
    {{
      "character_id": "character-slug-or-name",
      "character_name": "Display Name",
      "change_type": "emotional|physical|relational|knowledge|status",
      "description": "What changed"
    }}
  ],
  "world_facts": [
    {{
      "category": "location|rule|history|culture|magic|technology",
      "fact": "The fact established",
      "is_foundational": false
    }}
  ],
  "plot_events": [
    {{
      "event_id": "evt_unique_id",
      "event": "What happened",
      "characters_involved": ["char1", "char2"],
      "significance": "minor|moderate|major|climactic",
      "causal_summary": "Brief explanation of WHY this happened",
      "causes": ["evt_id_of_cause"],
      "consequences": ["potential_consequence_description"]
    }}
  ]
}}

For causes/consequences:
- "causes" should reference event_ids from previous scenes if known
- "consequences" can be descriptions of what this event might lead to
- If unknown, use empty arrays

If nothing notable in a category, use an empty array.

SCENE TEXT:
{prose[:30000]}"""  # Limit to ~30k chars

        result = await llm.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=model,
            max_tokens=2000,
            temperature=0.2  # Low temperature for factual extraction
        )

        # Parse the JSON response
        try:
            data = extract_json(result["content"])
        except (json.JSONDecodeError, ValueError):
            # If JSON parsing fails, return empty extraction
            data = {"character_changes": [], "world_facts": [], "plot_events": []}

        # Build the extraction object
        extraction = SceneExtraction(
            scene_id=scene_id,
            book_id=book_id,
            extracted_at=datetime.utcnow()
        )

        # Process character changes
        for change in data.get("character_changes", []):
            extraction.character_changes.append(CharacterStateChange(
                character_id=change.get("character_id", "unknown"),
                character_name=change.get("character_name", "Unknown"),
                change_type=change.get("change_type", "emotional"),
                description=change.get("description", ""),
                scene_id=scene_id,
                book_id=book_id
            ))

        # Process world facts
        for fact in data.get("world_facts", []):
            extraction.world_facts.append(WorldFact(
                category=fact.get("category", "rule"),
                fact=fact.get("fact", ""),
                scene_id=scene_id,
                book_id=book_id,
                book_number=book_number,
                is_foundational=fact.get("is_foundational", False)
            ))

        # Process plot events with causal chain support
        for i, event in enumerate(data.get("plot_events", [])):
            # Generate event_id if not provided
            event_id = event.get("event_id")
            if not event_id:
                event_id = f"evt_{scene_id}_{i}"

            extraction.plot_events.append(PlotEvent(
                event=event.get("event", ""),
                characters_involved=event.get("characters_involved", []),
                significance=event.get("significance", "minor"),
                scene_id=scene_id,
                book_id=book_id,
                book_number=book_number,
                chapter_number=chapter_number,
                scene_number=scene_number,
                event_id=event_id,
                causes=event.get("causes", []),
                consequences=event.get("consequences", []),
                causal_summary=event.get("causal_summary")
            ))

        # Save the extraction
        self.save_extraction(series_id, extraction)

        return extraction

    async def generate_summaries(
        self,
        series_id: str,
        model: Optional[str] = None,
        current_book_number: Optional[int] = None,
        min_relevance: float = 0.2
    ) -> Dict[str, str]:
        """
        Generate all summaries from accumulated extractions.

        Generates:
        - character_states.md: Current state of all characters
        - world_state.md: Established world facts
        - timeline.md: Chronological plot events

        Args:
            series_id: Series to generate summaries for
            model: Optional model override
            current_book_number: If provided, apply decay and filter by relevance
            min_relevance: Minimum relevance to include when filtering (0.0-1.0)

        Returns:
            Dict with generated summary content for each type
        """
        memory = self.get_memory(series_id)
        if not memory:
            return {}

        # Apply decay if current book is specified
        if current_book_number is not None:
            self._apply_decay_to_memory(memory, current_book_number)

            # Filter to items above minimum relevance
            memory.character_changes = [
                c for c in memory.character_changes
                if c.relevance_score >= min_relevance
            ]
            memory.world_facts = [
                f for f in memory.world_facts
                if f.relevance_score >= min_relevance
            ]
            memory.timeline = [
                e for e in memory.timeline
                if e.relevance_score >= min_relevance
            ]

            # Update manifest with current book
            manifest = self._load_manifest(series_id)
            manifest.current_book_number = current_book_number
            manifest.last_decay_calculation = datetime.utcnow()
            self._save_manifest(series_id, manifest)

        results = {}

        # Generate character states summary
        if memory.character_changes:
            results["character_states"] = await self._generate_character_summary(
                memory.character_changes, model
            )
            self.update_character_states(series_id, results["character_states"])

        # Generate world state summary
        if memory.world_facts:
            results["world_state"] = await self._generate_world_summary(
                memory.world_facts, model
            )
            self.update_world_state(series_id, results["world_state"])

        # Generate timeline summary
        if memory.timeline:
            results["timeline"] = await self._generate_timeline_summary(
                memory.timeline, model
            )
            self.update_timeline(series_id, results["timeline"])

        # Update hashes after regeneration
        self.update_hashes(series_id)

        return results

    async def _generate_character_summary(
        self,
        changes: List[CharacterStateChange],
        model: Optional[str] = None
    ) -> str:
        """Generate a summary of character states from changes."""
        from app.services.llm_service import get_llm_service
        llm = get_llm_service()

        # Group changes by character
        by_character: Dict[str, List[CharacterStateChange]] = {}
        for change in changes:
            char_name = change.character_name
            if char_name not in by_character:
                by_character[char_name] = []
            by_character[char_name].append(change)

        # Build input for LLM
        changes_text = ""
        for char_name, char_changes in by_character.items():
            changes_text += f"\n## {char_name}\n"
            for c in char_changes:
                changes_text += f"- [{c.change_type}] {c.description} (Scene: {c.scene_id})\n"

        system_prompt = """You are a literary analyst creating a character state reference.
Synthesize the character changes into a current-state summary for each character.
Focus on their current emotional state, physical condition, relationships, and knowledge.
Write in present tense. Be concise but complete. Output markdown."""

        user_prompt = f"""Based on these character changes throughout the story, write a current-state summary for each character.

CHANGES RECORDED:
{changes_text}

Write a markdown document with a section for each character showing their CURRENT state (as of the latest changes).
Format:
# Character States

## Character Name
**Emotional State:** ...
**Physical Condition:** ...
**Key Relationships:** ...
**Current Knowledge:** ...
**Status/Role:** ...

Keep each character section to 3-5 sentences max."""

        result = await llm.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=model,
            max_tokens=2000,
            temperature=0.3
        )

        return result["content"]

    async def _generate_world_summary(
        self,
        facts: List[WorldFact],
        model: Optional[str] = None
    ) -> str:
        """Generate a summary of world state from facts."""
        from app.services.llm_service import get_llm_service
        llm = get_llm_service()

        # Group by category
        by_category: Dict[str, List[WorldFact]] = {}
        for fact in facts:
            cat = fact.category
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(fact)

        # Build input
        facts_text = ""
        for category, cat_facts in by_category.items():
            facts_text += f"\n## {category.title()}\n"
            for f in cat_facts:
                facts_text += f"- {f.fact}\n"

        system_prompt = """You are a worldbuilding analyst creating a world reference document.
Synthesize the facts into a coherent world state summary.
Organize by category. Remove duplicates. Note any contradictions.
Output clean markdown."""

        user_prompt = f"""Based on these world facts established in the story, create a world state reference document.

FACTS RECORDED:
{facts_text}

Write a markdown document organizing the world state by category.
Combine related facts. Remove redundancy. Keep it reference-friendly.

Format:
# World State

## Locations
- ...

## Rules & Laws
- ...

## History
- ...

## Culture & Society
- ...

## Magic/Technology
- ...

Only include categories that have facts. Be concise."""

        result = await llm.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=model,
            max_tokens=2000,
            temperature=0.3
        )

        return result["content"]

    async def _generate_timeline_summary(
        self,
        events: List[PlotEvent],
        model: Optional[str] = None
    ) -> str:
        """Generate a timeline summary from plot events."""
        from app.services.llm_service import get_llm_service
        llm = get_llm_service()

        # Events should already be sorted by book/chapter/scene
        events_text = ""
        current_book = None
        for event in events:
            # Add book header if changed
            if event.book_number != current_book:
                current_book = event.book_number
                events_text += f"\n### Book {current_book or '?'}\n"

            significance_marker = {
                "minor": "",
                "moderate": "*",
                "major": "**",
                "climactic": "***"
            }.get(event.significance, "")

            chars = ", ".join(event.characters_involved) if event.characters_involved else "—"
            events_text += f"- {significance_marker}{event.event}{significance_marker} [{chars}]\n"

        system_prompt = """You are a story analyst creating a timeline reference.
Organize events chronologically. Group by story arc if apparent.
Mark major events clearly. Keep it scannable.
Output clean markdown."""

        user_prompt = f"""Based on these plot events, create a timeline summary.

EVENTS (in story order, * = moderate, ** = major, *** = climactic):
{events_text}

Write a clean timeline document. Group events into story beats or arcs if patterns emerge.
Highlight the major/climactic events. Keep it concise and reference-friendly.

Format:
# Timeline

## [Arc/Phase Name]
- Event 1
- **Major Event**
- Event 3

## [Next Arc]
..."""

        result = await llm.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=model,
            max_tokens=2000,
            temperature=0.3
        )

        return result["content"]

    def trace_causal_chain(
        self,
        series_id: str,
        event_id: str,
        direction: str = "causes",
        max_depth: int = 5
    ) -> List[PlotEvent]:
        """
        Trace the causal chain for an event.

        Args:
            series_id: Series ID
            event_id: Starting event ID
            direction: "causes" (trace backwards) or "consequences" (trace forwards)
            max_depth: Maximum depth to trace

        Returns:
            List of PlotEvent objects in causal order (oldest cause first if tracing causes)
        """
        memory = self.get_memory(series_id)
        if not memory:
            return []

        # Build event lookup by ID
        events_by_id: Dict[str, PlotEvent] = {}
        for event in memory.timeline:
            if event.event_id:
                events_by_id[event.event_id] = event

        # Find starting event
        start_event = events_by_id.get(event_id)
        if not start_event:
            return []

        # Trace chain
        chain = []
        visited = set()
        queue = [(start_event, 0)]

        while queue:
            current, depth = queue.pop(0)

            if current.event_id in visited or depth > max_depth:
                continue

            visited.add(current.event_id)
            chain.append(current)

            # Get linked events
            if direction == "causes":
                linked_ids = current.causes
            else:
                linked_ids = current.consequences

            for linked_id in linked_ids:
                if linked_id in events_by_id and linked_id not in visited:
                    queue.append((events_by_id[linked_id], depth + 1))

        # Sort chain by story order
        chain.sort(key=lambda e: (
            e.book_number or 999,
            e.chapter_number or 999,
            e.scene_number or 999
        ))

        return chain

    def get_causal_narrative(
        self,
        series_id: str,
        event_id: str
    ) -> str:
        """
        Generate a narrative explanation of why an event happened.

        Traces the causal chain and builds a readable explanation.

        Args:
            series_id: Series ID
            event_id: Event to explain

        Returns:
            Narrative string explaining the causal chain
        """
        chain = self.trace_causal_chain(series_id, event_id, direction="causes")

        if not chain:
            return ""

        # Build narrative
        lines = []
        for i, event in enumerate(chain):
            if i == 0 and event.causal_summary:
                lines.append(f"Root cause: {event.event}")
                lines.append(f"  Why: {event.causal_summary}")
            elif i == len(chain) - 1:
                lines.append(f"Result: {event.event}")
                if event.causal_summary:
                    lines.append(f"  Why: {event.causal_summary}")
            else:
                lines.append(f"→ {event.event}")
                if event.causal_summary:
                    lines.append(f"  (Because: {event.causal_summary})")

        return "\n".join(lines)

    def link_events(
        self,
        series_id: str,
        cause_event_id: str,
        effect_event_id: str
    ):
        """
        Manually link two events in a causal relationship.

        Args:
            series_id: Series ID
            cause_event_id: Event that caused the effect
            effect_event_id: Event that resulted from the cause
        """
        memory_dir = self._memory_dir(series_id)
        extractions_dir = memory_dir / "extractions"

        if not extractions_dir.exists():
            return

        # Find and update both events
        for extraction_file in extractions_dir.glob("*.json"):
            data = json.loads(extraction_file.read_text(encoding="utf-8"))
            modified = False

            for event in data.get("plot_events", []):
                if event.get("event_id") == cause_event_id:
                    if effect_event_id not in event.get("consequences", []):
                        if "consequences" not in event:
                            event["consequences"] = []
                        event["consequences"].append(effect_event_id)
                        modified = True

                elif event.get("event_id") == effect_event_id:
                    if cause_event_id not in event.get("causes", []):
                        if "causes" not in event:
                            event["causes"] = []
                        event["causes"].append(cause_event_id)
                        modified = True

            if modified:
                extraction_file.write_text(
                    json.dumps(data, default=str, indent=2),
                    encoding="utf-8"
                )

    async def generate_tiered_book_summary(
        self,
        series_id: str,
        book_id: str,
        book_title: str = "",
        book_number: int = 0,
        model: Optional[str] = None,
        tier: str = "both"
    ) -> Optional[BookSummary]:
        """
        Generate tiered book summaries from accumulated memory.

        Creates two versions:
        - Essential (~500 words): Key plot points, major changes only
        - Full (~2500 words): Complete details for reference

        Args:
            series_id: Series ID
            book_id: Book/project ID to summarize
            book_title: Book title for the summary
            book_number: Book number in series
            model: Optional model override
            tier: Which tier(s) to generate: "essential", "full", or "both"

        Returns:
            BookSummary with generated summaries, or None if no data
        """
        from app.services.llm_service import get_llm_service
        llm = get_llm_service()

        memory = self.get_memory(series_id)
        if not memory:
            return None

        # Filter to just this book's data
        book_changes = [c for c in memory.character_changes if c.book_id == book_id]
        book_facts = [f for f in memory.world_facts if f.book_id == book_id]
        book_events = [e for e in memory.timeline if e.book_id == book_id]

        if not book_events and not book_changes:
            return None

        # Build input text from memory
        input_text = self._build_summary_input(book_events, book_changes, book_facts)

        # Get or create book summary entry
        summary = memory.book_summaries.get(book_id) or BookSummary(
            book_id=book_id,
            book_number=book_number,
            title=book_title
        )

        # Generate essential summary (~500 words)
        if tier in ("essential", "both"):
            essential = await self._generate_essential_summary(
                llm, input_text, book_title, model
            )
            summary.essential = essential
            summary.essential_word_count = len(essential.split())

        # Generate full summary (~2500 words)
        if tier in ("full", "both"):
            full = await self._generate_full_summary(
                llm, input_text, book_title, model
            )
            summary.full = full
            summary.full_word_count = len(full.split())

        summary.generated_at = datetime.utcnow()

        # Store in memory
        memory.book_summaries[book_id] = summary
        self._save_memory(series_id, memory)

        return summary

    def _build_summary_input(
        self,
        events: List[PlotEvent],
        changes: List[CharacterStateChange],
        facts: List[WorldFact]
    ) -> str:
        """Build input text for summary generation."""
        input_text = "## Plot Events (in chronological order)\n"
        for event in events:
            significance = f" [{event.significance}]" if event.significance else ""
            input_text += f"- {event.event}{significance}\n"
            if event.causal_summary:
                input_text += f"  (Consequence: {event.causal_summary})\n"

        input_text += "\n## Character Developments\n"
        # Group by character
        by_char: Dict[str, List[CharacterStateChange]] = {}
        for change in changes:
            if change.character_name not in by_char:
                by_char[change.character_name] = []
            by_char[change.character_name].append(change)

        for char_name, char_changes in by_char.items():
            input_text += f"\n### {char_name}\n"
            for c in char_changes:
                input_text += f"- [{c.change_type}] {c.description}\n"

        input_text += "\n## World Elements Established\n"
        # Group by category
        by_cat: Dict[str, List[WorldFact]] = {}
        for fact in facts:
            cat = fact.category or "general"
            if cat not in by_cat:
                by_cat[cat] = []
            by_cat[cat].append(fact)

        for cat, cat_facts in by_cat.items():
            input_text += f"\n### {cat.title()}\n"
            for f in cat_facts:
                foundational = " [foundational]" if f.is_foundational else ""
                input_text += f"- {f.fact}{foundational}\n"

        return input_text

    async def _generate_essential_summary(
        self,
        llm,
        input_text: str,
        book_title: str,
        model: Optional[str] = None
    ) -> str:
        """Generate essential summary (~500 words, key points only)."""
        system_prompt = """You are a story analyst creating a CONCISE book summary for series continuity.
Write a focused summary that captures ONLY the most critical information:
- Major plot turning points (not every event)
- Significant character changes that matter for future books
- World facts that will be referenced later
Write in past tense. Be extremely selective. Target 400-600 words."""

        user_prompt = f"""Based on this extracted data from "{book_title or 'this book'}", write a CONCISE essential summary.

{input_text}

Write an essential summary (~500 words) covering ONLY:
1. **Critical Plot Points**: The 3-5 most important events that drive the story forward
2. **Major Character Changes**: Only changes that fundamentally alter a character's trajectory
3. **Key World Facts**: Only facts that will be essential for understanding future books

Be ruthlessly selective. This summary is used during generation and must be token-efficient.
Write as flowing prose, not bullets."""

        result = await llm.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=model,
            max_tokens=1000,
            temperature=0.3
        )
        return result["content"]

    async def _generate_full_summary(
        self,
        llm,
        input_text: str,
        book_title: str,
        model: Optional[str] = None
    ) -> str:
        """Generate full summary (~2500 words, complete details)."""
        system_prompt = """You are a story analyst creating a COMPREHENSIVE book summary for series continuity.
Write a detailed summary that captures the complete story:
- All major and minor plot events in order
- Complete character arcs with emotional and physical changes
- Full world building details and lore established
- Relationships formed, broken, or changed
Write in past tense. Be thorough and detailed. Target 2000-3000 words."""

        user_prompt = f"""Based on this extracted data from "{book_title or 'this book'}", write a COMPREHENSIVE full summary.

{input_text}

Write a detailed summary (~2500 words) covering:
1. **Complete Plot Summary**: All events in chronological order, including causes and consequences
2. **Full Character Arcs**: How each significant character started, changed, and ended
3. **Relationship Dynamics**: How relationships evolved throughout the book
4. **World Building**: All world facts, lore, and rules established
5. **Carrying Forward**: Everything that matters for future books

Be thorough. This summary is the complete reference for this book.
Write as flowing prose with clear section transitions."""

        result = await llm.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=model,
            max_tokens=5000,
            temperature=0.4
        )
        return result["content"]

    def get_book_summary(
        self,
        series_id: str,
        book_id: str,
        tier: str = "essential"
    ) -> Optional[str]:
        """
        Get a specific tier of book summary.

        Args:
            series_id: Series ID
            book_id: Book/project ID
            tier: "essential" or "full"

        Returns:
            Summary text or None
        """
        memory = self.get_memory(series_id)
        if not memory:
            return None

        summary = memory.book_summaries.get(book_id)
        if not summary:
            return None

        if tier == "full":
            return summary.full if summary.full else summary.essential
        return summary.essential if summary.essential else summary.full

    async def generate_book_summary_from_memory(
        self,
        series_id: str,
        book_id: str,
        model: Optional[str] = None
    ) -> str:
        """
        Generate a book summary from accumulated memory.

        DEPRECATED: Use generate_tiered_book_summary() instead.
        This method is kept for backwards compatibility and generates
        the essential tier only.

        Args:
            series_id: Series ID
            book_id: Book/project ID to summarize
            model: Optional model override

        Returns:
            Generated book summary text (essential tier)
        """
        summary = await self.generate_tiered_book_summary(
            series_id=series_id,
            book_id=book_id,
            model=model,
            tier="essential"
        )
        return summary.essential if summary else ""


# Singleton instance
memory_service = MemoryService()
