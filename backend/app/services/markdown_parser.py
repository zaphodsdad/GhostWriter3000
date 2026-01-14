"""Markdown parser service for files with YAML frontmatter."""

from pathlib import Path
from typing import Dict, Any
import frontmatter


class MarkdownParser:
    """Parser for markdown files with YAML frontmatter."""

    @staticmethod
    def parse_file(filepath: Path) -> Dict[str, Any]:
        """
        Parse a markdown file with YAML frontmatter.

        Args:
            filepath: Path to the markdown file

        Returns:
            Dictionary with 'metadata' and 'content' keys

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file cannot be parsed
        """
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)

            return {
                "metadata": dict(post.metadata),
                "content": post.content
            }
        except Exception as e:
            raise ValueError(f"Failed to parse markdown file {filepath}: {str(e)}")

    @staticmethod
    def write_file(filepath: Path, metadata: Dict[str, Any], content: str) -> None:
        """
        Write a markdown file with YAML frontmatter.

        Args:
            filepath: Path where to write the file
            metadata: Dictionary of metadata for frontmatter
            content: Markdown content

        Raises:
            ValueError: If write fails
        """
        try:
            post = frontmatter.Post(content, **metadata)
            filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(frontmatter.dumps(post))
        except Exception as e:
            raise ValueError(f"Failed to write markdown file {filepath}: {str(e)}")
