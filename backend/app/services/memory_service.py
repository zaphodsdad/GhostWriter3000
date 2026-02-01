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


# Singleton instance
memory_service = MemoryService()
