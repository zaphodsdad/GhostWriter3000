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

    def get_context_for_generation(self, series_id: str) -> Dict[str, str]:
        """Get compact context summaries for use in generation prompts."""
        memory = self.get_memory(series_id)
        if not memory:
            return {}

        context = {}

        if memory.character_states_summary:
            context["character_states"] = memory.character_states_summary

        if memory.world_state_summary:
            context["world_state"] = memory.world_state_summary

        if memory.timeline_summary:
            context["timeline"] = memory.timeline_summary

        return context

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

3. PLOT EVENTS - Significant story events (for timeline):
   - What happened (brief, factual)
   - Who was involved
   - Significance: minor, moderate, major, or climactic

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
      "fact": "The fact established"
    }}
  ],
  "plot_events": [
    {{
      "event": "What happened",
      "characters_involved": ["char1", "char2"],
      "significance": "minor|moderate|major|climactic"
    }}
  ]
}}

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
                book_id=book_id
            ))

        # Process plot events
        for event in data.get("plot_events", []):
            extraction.plot_events.append(PlotEvent(
                event=event.get("event", ""),
                characters_involved=event.get("characters_involved", []),
                significance=event.get("significance", "minor"),
                scene_id=scene_id,
                book_id=book_id,
                book_number=book_number,
                chapter_number=chapter_number,
                scene_number=scene_number
            ))

        # Save the extraction
        self.save_extraction(series_id, extraction)

        return extraction

    async def generate_summaries(
        self,
        series_id: str,
        model: Optional[str] = None
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

        Returns:
            Dict with generated summary content for each type
        """
        memory = self.get_memory(series_id)
        if not memory:
            return {}

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

    async def generate_book_summary_from_memory(
        self,
        series_id: str,
        book_id: str,
        model: Optional[str] = None
    ) -> str:
        """
        Generate a book summary from accumulated memory for that book.

        This creates a prose summary suitable for the Book Summary feature,
        compiled from all extractions for scenes in that book.

        Args:
            series_id: Series ID
            book_id: Book/project ID to summarize
            model: Optional model override

        Returns:
            Generated book summary text
        """
        from app.services.llm_service import get_llm_service
        llm = get_llm_service()

        memory = self.get_memory(series_id)
        if not memory:
            return ""

        # Filter to just this book's data
        book_changes = [c for c in memory.character_changes if c.book_id == book_id]
        book_facts = [f for f in memory.world_facts if f.book_id == book_id]
        book_events = [e for e in memory.timeline if e.book_id == book_id]

        if not book_events and not book_changes:
            return ""

        # Build input
        input_text = "## Plot Events (in order)\n"
        for event in book_events:
            input_text += f"- {event.event}\n"

        input_text += "\n## Character Developments\n"
        for change in book_changes:
            input_text += f"- {change.character_name}: {change.description}\n"

        input_text += "\n## World Elements Established\n"
        for fact in book_facts:
            input_text += f"- {fact.fact}\n"

        system_prompt = """You are a story analyst writing a book summary for series continuity.
Write a clear, prose summary that captures the essential plot, character arcs, and world developments.
This summary will be used as context when writing later books in the series.
Write in past tense. Be comprehensive but concise. Aim for 500-1500 words."""

        user_prompt = f"""Based on this extracted data from a book, write a comprehensive summary.

{input_text}

Write a prose summary covering:
1. **Plot Summary**: What happened in this book (major events, conflicts, resolution)
2. **Character Arcs**: How main characters changed/developed
3. **World State**: Important world facts established
4. **Carrying Forward**: What matters for future books

Write as flowing prose, not bullet points. This is for series continuity reference."""

        result = await llm.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=model,
            max_tokens=3000,
            temperature=0.4
        )

        return result["content"]


# Singleton instance
memory_service = MemoryService()
