"""Series service for managing book series and context merging."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings
from app.models.series import Series, SeriesCreate, SeriesSummary
from app.services.markdown_parser import MarkdownParser
from app.services.memory_service import memory_service


class SeriesService:
    """Service for series operations and context merging."""

    def __init__(self):
        self.parser = MarkdownParser()

    async def list_series(self) -> List[SeriesSummary]:
        """List all series with summary info."""
        series_list = []
        series_base_dir = settings.series_dir

        if not series_base_dir.exists():
            return series_list

        for series_path in series_base_dir.iterdir():
            if series_path.is_dir():
                series_file = series_path / "series.json"
                if series_file.exists():
                    try:
                        with open(series_file) as f:
                            data = json.load(f)

                        # Count books and word count
                        book_count = len(data.get("project_ids", []))
                        total_word_count = await self._calculate_series_word_count(
                            data.get("project_ids", [])
                        )

                        series_list.append(SeriesSummary(
                            id=data["id"],
                            title=data["title"],
                            description=data.get("description"),
                            author=data.get("author"),
                            genre=data.get("genre"),
                            book_count=book_count,
                            total_planned_books=data.get("total_planned_books"),
                            total_word_count=total_word_count,
                            created_at=datetime.fromisoformat(data["created_at"]),
                            updated_at=datetime.fromisoformat(data["updated_at"])
                        ))
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue

        series_list.sort(key=lambda s: s.updated_at, reverse=True)
        return series_list

    async def get_series(self, series_id: str) -> Optional[Series]:
        """Get a series by ID."""
        series_file = settings.series_path(series_id) / "series.json"
        if not series_file.exists():
            return None

        with open(series_file) as f:
            data = json.load(f)

        return Series(**data)

    async def create_series(self, series_data: SeriesCreate, series_id: str) -> Series:
        """Create a new series."""
        series_dir = settings.series_path(series_id)
        series_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (series_dir / "characters").mkdir(exist_ok=True)
        (series_dir / "world").mkdir(exist_ok=True)
        (series_dir / "references").mkdir(exist_ok=True)

        now = datetime.utcnow()
        series = Series(
            id=series_id,
            title=series_data.title,
            description=series_data.description,
            author=series_data.author,
            genre=series_data.genre,
            total_planned_books=series_data.total_planned_books,
            project_ids=[],
            created_at=now,
            updated_at=now
        )

        # Save series.json
        series_file = series_dir / "series.json"
        with open(series_file, "w") as f:
            json.dump(series.model_dump(mode="json"), f, indent=2, default=str)

        return series

    async def update_series(self, series_id: str, updates: Dict[str, Any]) -> Optional[Series]:
        """Update a series."""
        series = await self.get_series(series_id)
        if not series:
            return None

        # Apply updates
        series_dict = series.model_dump()
        for key, value in updates.items():
            if value is not None and key in series_dict:
                series_dict[key] = value

        series_dict["updated_at"] = datetime.utcnow()

        # Save
        series_file = settings.series_path(series_id) / "series.json"
        with open(series_file, "w") as f:
            json.dump(series_dict, f, indent=2, default=str)

        return Series(**series_dict)

    async def delete_series(self, series_id: str) -> bool:
        """Delete a series (removes series directory but not associated projects)."""
        import shutil
        series_dir = settings.series_path(series_id)
        if not series_dir.exists():
            return False

        # First, remove series_id from all associated projects
        series = await self.get_series(series_id)
        if series:
            for project_id in series.project_ids:
                await self._remove_series_from_project(project_id)

        shutil.rmtree(series_dir)
        return True

    async def add_book_to_series(
        self,
        series_id: str,
        project_id: str,
        book_number: Optional[int] = None
    ) -> Optional[Series]:
        """Add a project/book to a series."""
        series = await self.get_series(series_id)
        if not series:
            return None

        # Check project exists
        project_dir = settings.project_dir(project_id)
        if not project_dir.exists():
            raise ValueError(f"Project not found: {project_id}")

        # Add to series if not already there
        if project_id not in series.project_ids:
            series.project_ids.append(project_id)

        # Determine book number
        if book_number is None:
            book_number = len(series.project_ids)

        # Update project with series info
        await self._update_project_series_info(project_id, series_id, book_number)

        # Save series
        return await self.update_series(series_id, {"project_ids": series.project_ids})

    async def remove_book_from_series(self, series_id: str, project_id: str) -> Optional[Series]:
        """Remove a project/book from a series."""
        series = await self.get_series(series_id)
        if not series:
            return None

        if project_id in series.project_ids:
            series.project_ids.remove(project_id)

        # Remove series info from project
        await self._remove_series_from_project(project_id)

        # Save series
        return await self.update_series(series_id, {"project_ids": series.project_ids})

    async def reorder_books(self, series_id: str, project_ids: List[str]) -> Optional[Series]:
        """Reorder books in a series."""
        series = await self.get_series(series_id)
        if not series:
            return None

        # Validate all project_ids are in series
        if set(project_ids) != set(series.project_ids):
            raise ValueError("Project IDs must match existing series books")

        # Update book numbers
        for idx, project_id in enumerate(project_ids, start=1):
            await self._update_project_series_info(project_id, series_id, idx)

        return await self.update_series(series_id, {"project_ids": project_ids})

    async def get_combined_context(self, project_id: str) -> Dict[str, Any]:
        """
        Get combined context from series (if any) + project.
        Series resources come first, project resources extend/override.
        Includes memory context from marked-as-canon scenes.
        Includes learned style preferences from user edits.
        """
        context = {
            "characters": [],
            "worlds": [],
            "style_guide": None,
            "references": [],
            "previous_books": [],
            "memory_context": {},
            "style_preferences": ""
        }

        # Load project to check for series
        project = await self._load_project(project_id)
        if not project:
            return context

        series_id = project.get("series_id")
        book_number = project.get("book_number")

        if series_id:
            # Load series-level resources
            series_chars = await self._load_characters(settings.series_characters_dir(series_id))
            series_worlds = await self._load_worlds(settings.series_world_dir(series_id))
            series_style = await self._load_style_guide(settings.series_path(series_id))
            series_refs = await self._load_references(settings.series_references_dir(series_id), "series", series_id)

            context["characters"].extend(series_chars)
            context["worlds"].extend(series_worlds)
            context["style_guide"] = series_style
            context["references"].extend(series_refs)

            # Load memory context from series (accumulated canon knowledge)
            # Uses auto-refresh to regenerate stale summaries when source files change
            # Pass current book number for decay calculation
            context["memory_context"] = await memory_service.get_context_with_auto_refresh(
                series_id,
                current_book_number=book_number
            )

            # Load learned style preferences from user edits
            from app.services.style_learning_service import get_style_learning_service
            style_service = get_style_learning_service()
            context["style_preferences"] = style_service.get_preferences_for_prompt(series_id)

            # Load summaries from previous books in series
            if book_number and book_number > 1:
                previous_books = await self._load_previous_book_summaries(series_id, book_number)
                context["previous_books"] = previous_books

        # Load project-level resources (extend/override)
        project_chars = await self._load_characters(settings.characters_dir(project_id))
        project_worlds = await self._load_worlds(settings.world_dir(project_id))
        project_style = await self._load_style_guide(settings.project_dir(project_id))
        project_refs = await self._load_references(settings.project_references_dir(project_id), "project", project_id)

        context["characters"].extend(project_chars)
        context["worlds"].extend(project_worlds)
        if project_style:
            context["style_guide"] = project_style  # Project overrides series
        context["references"].extend(project_refs)

        return context

    # Helper methods

    async def _load_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Load project JSON."""
        project_file = settings.project_dir(project_id) / "project.json"
        if not project_file.exists():
            return None
        with open(project_file) as f:
            return json.load(f)

    async def _update_project_series_info(self, project_id: str, series_id: str, book_number: int):
        """Update project with series info."""
        project_file = settings.project_dir(project_id) / "project.json"
        if not project_file.exists():
            return

        with open(project_file) as f:
            data = json.load(f)

        data["series_id"] = series_id
        data["book_number"] = book_number
        data["updated_at"] = datetime.utcnow().isoformat()

        with open(project_file, "w") as f:
            json.dump(data, f, indent=2)

    async def _remove_series_from_project(self, project_id: str):
        """Remove series info from a project."""
        project_file = settings.project_dir(project_id) / "project.json"
        if not project_file.exists():
            return

        with open(project_file) as f:
            data = json.load(f)

        data["series_id"] = None
        data["book_number"] = None
        data["updated_at"] = datetime.utcnow().isoformat()

        with open(project_file, "w") as f:
            json.dump(data, f, indent=2)

    async def _load_characters(self, chars_dir: Path) -> List[Dict[str, Any]]:
        """Load all characters from a directory."""
        characters = []
        if not chars_dir.exists():
            return characters

        for filepath in chars_dir.glob("*.md"):
            try:
                parsed = self.parser.parse_file(filepath)
                characters.append({
                    "id": filepath.stem,
                    "metadata": parsed.get("metadata", {}),
                    "content": parsed.get("content", "")
                })
            except Exception:
                continue

        return characters

    async def _load_worlds(self, world_dir: Path) -> List[Dict[str, Any]]:
        """Load all world contexts from a directory."""
        worlds = []
        if not world_dir.exists():
            return worlds

        for filepath in world_dir.glob("*.md"):
            try:
                parsed = self.parser.parse_file(filepath)
                worlds.append({
                    "id": filepath.stem,
                    "metadata": parsed.get("metadata", {}),
                    "content": parsed.get("content", "")
                })
            except Exception:
                continue

        return worlds

    async def _load_style_guide(self, base_dir: Path) -> Optional[Dict[str, Any]]:
        """Load style guide from directory."""
        style_file = base_dir / "style.json"
        if not style_file.exists():
            return None

        with open(style_file) as f:
            return json.load(f)

    async def _load_references(self, refs_dir: Path, scope: str, scope_id: str) -> List[Dict[str, Any]]:
        """Load all reference documents from a directory."""
        references = []
        if not refs_dir.exists():
            return references

        # Load reference index if exists
        index_file = refs_dir / "_index.json"
        index_data = {}
        if index_file.exists():
            with open(index_file) as f:
                index_data = json.load(f)

        for filepath in refs_dir.glob("*"):
            if filepath.name.startswith("_") or filepath.is_dir():
                continue

            try:
                content = filepath.read_text(encoding="utf-8")
                ref_id = filepath.stem.lower().replace(" ", "-")

                # Get metadata from index or defaults
                meta = index_data.get(ref_id, {})

                references.append({
                    "id": ref_id,
                    "filename": filepath.name,
                    "title": meta.get("title", filepath.stem),
                    "description": meta.get("description"),
                    "doc_type": meta.get("doc_type", "other"),
                    "use_in_generation": meta.get("use_in_generation", True),
                    "use_in_chat": meta.get("use_in_chat", True),
                    "scope": scope,
                    "scope_id": scope_id,
                    "content": content,
                    "word_count": len(content.split())
                })
            except Exception:
                continue

        return references

    async def _load_previous_book_summaries(self, series_id: str, current_book_number: int) -> List[Dict[str, Any]]:
        """Load summaries from books earlier in the series."""
        summaries = []
        series = await self.get_series(series_id)
        if not series:
            return summaries

        for project_id in series.project_ids:
            project = await self._load_project(project_id)
            if not project:
                continue

            book_num = project.get("book_number", 0)
            if book_num >= current_book_number:
                continue

            # Load project summary or compile from canon scenes
            summary = await self._get_project_summary(project_id, project)
            if summary:
                summaries.append({
                    "project_id": project_id,
                    "title": project.get("title", project_id),
                    "book_number": book_num,
                    "summary": summary
                })

        summaries.sort(key=lambda x: x.get("book_number", 0))
        return summaries

    async def _get_project_summary(self, project_id: str, project: Dict[str, Any]) -> Optional[str]:
        """Get or generate a summary for a project."""
        # Check for explicit project summary file
        summary_file = settings.project_dir(project_id) / "summary.md"
        if summary_file.exists():
            return summary_file.read_text(encoding="utf-8")

        # Compile from scene summaries
        scenes_dir = settings.scenes_dir(project_id)
        if not scenes_dir.exists():
            return None

        scene_summaries = []
        for scene_file in scenes_dir.glob("*.json"):
            try:
                with open(scene_file) as f:
                    scene = json.load(f)
                if scene.get("is_canon") and scene.get("summary"):
                    scene_summaries.append({
                        "number": scene.get("scene_number", 0),
                        "title": scene.get("title", ""),
                        "summary": scene.get("summary", "")
                    })
            except Exception:
                continue

        if not scene_summaries:
            return None

        scene_summaries.sort(key=lambda x: x["number"])

        # Compile into a book summary
        summary_parts = [f"# {project.get('title', project_id)}\n"]
        for scene in scene_summaries:
            summary_parts.append(f"**{scene['title']}**: {scene['summary']}\n")

        return "\n".join(summary_parts)

    async def _calculate_series_word_count(self, project_ids: List[str]) -> int:
        """Calculate total word count across all books in series."""
        total = 0
        for project_id in project_ids:
            scenes_dir = settings.scenes_dir(project_id)
            if not scenes_dir.exists():
                continue

            for scene_file in scenes_dir.glob("*.json"):
                try:
                    with open(scene_file) as f:
                        scene = json.load(f)
                    if scene.get("is_canon") and scene.get("prose"):
                        total += len(scene["prose"].split())
                except Exception:
                    continue

        return total


# Singleton instance
_series_service: Optional[SeriesService] = None


def get_series_service() -> SeriesService:
    """Get or create series service instance."""
    global _series_service
    if _series_service is None:
        _series_service = SeriesService()
    return _series_service
