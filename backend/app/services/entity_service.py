"""Service for managing story entities (characters, world) at series level with merge logic."""

import re
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.config import settings
from app.services.extraction_service import get_extraction_service


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text[:50]


def parse_markdown_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter and body from markdown content."""
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            try:
                metadata = yaml.safe_load(parts[1]) or {}
                body = parts[2].strip()
                return metadata, body
            except yaml.YAMLError:
                pass
    return {}, content


def build_markdown_with_frontmatter(metadata: Dict[str, Any], body: str) -> str:
    """Build markdown content with YAML frontmatter."""
    frontmatter = yaml.dump(metadata, default_flow_style=False, allow_unicode=True).strip()
    return f"---\n{frontmatter}\n---\n\n{body}"


class EntityService:
    """Service for managing characters and world elements with series-level storage and merge logic."""

    def __init__(self):
        self.extraction_service = get_extraction_service()

    async def extract_and_save_entities(
        self,
        series_id: str,
        book_id: str,
        book_number: int,
        prose: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract characters and world elements from prose and save to series level.

        Uses merge logic: if entity exists, append new facts tagged with book_number.

        Args:
            series_id: Series to save entities to
            book_id: Book the prose came from (for tagging)
            book_number: Book number in series (for chronology)
            prose: Text to extract from
            model: Optional model override

        Returns:
            Dict with counts of created/updated entities and usage stats
        """
        # Get existing entity names to help extraction avoid duplicates
        existing_chars = self._get_existing_character_names(series_id)
        existing_worlds = self._get_existing_world_names(series_id)

        # Extract entities
        char_result = await self.extraction_service.extract_characters(
            prose, model, existing_characters=None  # Don't skip - we'll merge instead
        )
        world_result = await self.extraction_service.extract_world(
            prose, model, existing_elements=None  # Don't skip - we'll merge instead
        )

        # Save with merge logic
        char_stats = await self._save_characters(
            series_id, book_id, book_number,
            char_result.get("characters", [])
        )
        world_stats = await self._save_world_elements(
            series_id, book_id, book_number,
            world_result.get("world_elements", [])
        )

        # Combine usage
        total_usage = {
            "prompt_tokens": char_result["usage"]["prompt_tokens"] + world_result["usage"]["prompt_tokens"],
            "completion_tokens": char_result["usage"]["completion_tokens"] + world_result["usage"]["completion_tokens"]
        }

        return {
            "characters": char_stats,
            "world_elements": world_stats,
            "usage": total_usage
        }

    def _get_existing_character_names(self, series_id: str) -> List[str]:
        """Get names of existing characters in series."""
        chars_dir = settings.series_characters_dir(series_id)
        names = []
        if chars_dir.exists():
            for filepath in chars_dir.glob("*.md"):
                content = filepath.read_text(encoding='utf-8')
                metadata, _ = parse_markdown_frontmatter(content)
                if 'name' in metadata:
                    names.append(metadata['name'])
        return names

    def _get_existing_world_names(self, series_id: str) -> List[str]:
        """Get names of existing world elements in series."""
        world_dir = settings.series_world_dir(series_id)
        names = []
        if world_dir.exists():
            for filepath in world_dir.glob("*.md"):
                content = filepath.read_text(encoding='utf-8')
                metadata, _ = parse_markdown_frontmatter(content)
                if 'name' in metadata:
                    names.append(metadata['name'])
        return names

    async def _save_characters(
        self,
        series_id: str,
        book_id: str,
        book_number: int,
        characters: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Save characters to series level with merge logic.

        Returns dict with created/updated counts.
        """
        chars_dir = settings.series_characters_dir(series_id)
        chars_dir.mkdir(parents=True, exist_ok=True)

        created = 0
        updated = 0

        for char in characters:
            name = char.get('name', 'Unknown')
            char_id = slugify(name)
            filepath = chars_dir / f"{char_id}.md"

            if filepath.exists():
                # Merge with existing
                content = filepath.read_text(encoding='utf-8')
                metadata, body = parse_markdown_frontmatter(content)

                # Append new information tagged with book number
                new_section = self._format_character_section(char, book_id, book_number)
                body = body + f"\n\n{new_section}"

                # Update metadata with any new info
                metadata = self._merge_character_metadata(metadata, char, book_number)

                filepath.write_text(
                    build_markdown_with_frontmatter(metadata, body),
                    encoding='utf-8'
                )
                updated += 1
            else:
                # Create new character
                metadata = {
                    'name': name,
                    'role': char.get('role', 'supporting'),
                    'first_seen_book': book_number,
                    'created_from': book_id
                }

                body = self._format_character_body(char, book_id, book_number)

                filepath.write_text(
                    build_markdown_with_frontmatter(metadata, body),
                    encoding='utf-8'
                )
                created += 1

        return {"created": created, "updated": updated}

    async def _save_world_elements(
        self,
        series_id: str,
        book_id: str,
        book_number: int,
        elements: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Save world elements to series level with merge logic.

        Returns dict with created/updated counts.
        """
        world_dir = settings.series_world_dir(series_id)
        world_dir.mkdir(parents=True, exist_ok=True)

        created = 0
        updated = 0

        for elem in elements:
            name = elem.get('name', 'Unknown')
            elem_id = slugify(name)
            filepath = world_dir / f"{elem_id}.md"

            if filepath.exists():
                # Merge with existing
                content = filepath.read_text(encoding='utf-8')
                metadata, body = parse_markdown_frontmatter(content)

                # Append new information tagged with book number
                new_section = self._format_world_section(elem, book_id, book_number)
                body = body + f"\n\n{new_section}"

                # Update metadata
                metadata = self._merge_world_metadata(metadata, elem, book_number)

                filepath.write_text(
                    build_markdown_with_frontmatter(metadata, body),
                    encoding='utf-8'
                )
                updated += 1
            else:
                # Create new element
                metadata = {
                    'name': name,
                    'category': elem.get('category', 'GENERAL'),
                    'first_seen_book': book_number,
                    'created_from': book_id
                }

                body = self._format_world_body(elem, book_id, book_number)

                filepath.write_text(
                    build_markdown_with_frontmatter(metadata, body),
                    encoding='utf-8'
                )
                created += 1

        return {"created": created, "updated": updated}

    def _format_character_body(self, char: Dict[str, Any], book_id: str, book_number: int) -> str:
        """Format initial character body content."""
        sections = []

        if char.get('physical_description'):
            sections.append(f"## Physical Description\n{char['physical_description']}")

        if char.get('personality_traits'):
            traits = char['personality_traits']
            if isinstance(traits, list):
                traits = ', '.join(traits)
            sections.append(f"## Personality\n{traits}")

        if char.get('relationships'):
            rels = char['relationships']
            if isinstance(rels, dict):
                rel_lines = [f"- **{k}**: {v}" for k, v in rels.items()]
                sections.append(f"## Relationships\n" + '\n'.join(rel_lines))

        if char.get('voice_patterns'):
            sections.append(f"## Voice\n{char['voice_patterns']}")

        if char.get('first_appearance'):
            sections.append(f"## First Appearance\n{char['first_appearance']}")

        if char.get('notes'):
            sections.append(f"## Notes\n{char['notes']}")

        # Tag the source
        sections.append(f"\n---\n*Initial extraction from Book {book_number} ({book_id})*")

        return '\n\n'.join(sections) if sections else "*No details extracted.*"

    def _format_character_section(self, char: Dict[str, Any], book_id: str, book_number: int) -> str:
        """Format additional character info as a section to append."""
        lines = [f"## Book {book_number} Updates ({book_id})"]

        if char.get('physical_description'):
            lines.append(f"**Physical**: {char['physical_description']}")

        if char.get('personality_traits'):
            traits = char['personality_traits']
            if isinstance(traits, list):
                traits = ', '.join(traits)
            lines.append(f"**Traits**: {traits}")

        if char.get('relationships'):
            rels = char['relationships']
            if isinstance(rels, dict):
                for k, v in rels.items():
                    lines.append(f"**Relationship with {k}**: {v}")

        if char.get('notes'):
            lines.append(f"**Notes**: {char['notes']}")

        return '\n'.join(lines)

    def _format_world_body(self, elem: Dict[str, Any], book_id: str, book_number: int) -> str:
        """Format initial world element body content."""
        sections = []

        if elem.get('description'):
            sections.append(f"## Description\n{elem['description']}")

        if elem.get('rules'):
            sections.append(f"## Rules & Constraints\n{elem['rules']}")

        if elem.get('connections'):
            conns = elem['connections']
            if isinstance(conns, list):
                conns = ', '.join(conns)
            sections.append(f"## Connections\n{conns}")

        if elem.get('notes'):
            sections.append(f"## Notes\n{elem['notes']}")

        # Tag the source
        sections.append(f"\n---\n*Initial extraction from Book {book_number} ({book_id})*")

        return '\n\n'.join(sections) if sections else "*No details extracted.*"

    def _format_world_section(self, elem: Dict[str, Any], book_id: str, book_number: int) -> str:
        """Format additional world info as a section to append."""
        lines = [f"## Book {book_number} Updates ({book_id})"]

        if elem.get('description'):
            lines.append(f"**Description**: {elem['description']}")

        if elem.get('rules'):
            lines.append(f"**Rules**: {elem['rules']}")

        if elem.get('connections'):
            conns = elem['connections']
            if isinstance(conns, list):
                conns = ', '.join(conns)
            lines.append(f"**Connections**: {conns}")

        if elem.get('notes'):
            lines.append(f"**Notes**: {elem['notes']}")

        return '\n'.join(lines)

    def _merge_character_metadata(
        self,
        existing: Dict[str, Any],
        new_char: Dict[str, Any],
        book_number: int
    ) -> Dict[str, Any]:
        """Merge new character info into existing metadata."""
        # Track which books this character appears in
        books_appeared = existing.get('books_appeared', [existing.get('first_seen_book', 0)])
        if book_number not in books_appeared:
            books_appeared.append(book_number)
            books_appeared.sort()
        existing['books_appeared'] = books_appeared

        # Update role if this is a more prominent role
        role_priority = {'protagonist': 4, 'antagonist': 3, 'supporting': 2, 'minor': 1, 'mentioned': 0}
        new_role = new_char.get('role', 'minor')
        old_role = existing.get('role', 'minor')
        if role_priority.get(new_role, 0) > role_priority.get(old_role, 0):
            existing['role'] = new_role

        existing['last_updated'] = datetime.utcnow().isoformat()

        return existing

    def _merge_world_metadata(
        self,
        existing: Dict[str, Any],
        new_elem: Dict[str, Any],
        book_number: int
    ) -> Dict[str, Any]:
        """Merge new world element info into existing metadata."""
        # Track which books this element appears in
        books_appeared = existing.get('books_appeared', [existing.get('first_seen_book', 0)])
        if book_number not in books_appeared:
            books_appeared.append(book_number)
            books_appeared.sort()
        existing['books_appeared'] = books_appeared

        existing['last_updated'] = datetime.utcnow().isoformat()

        return existing


# Global service instance
_entity_service: Optional[EntityService] = None


def get_entity_service() -> EntityService:
    """Get or create the global entity service instance."""
    global _entity_service
    if _entity_service is None:
        _entity_service = EntityService()
    return _entity_service
