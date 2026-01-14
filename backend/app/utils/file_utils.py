"""File operation utilities."""

import json
from pathlib import Path
from typing import Any, Dict, List
import aiofiles


async def read_json_file(filepath: Path) -> Dict[str, Any]:
    """
    Read and parse a JSON file asynchronously.

    Args:
        filepath: Path to JSON file

    Returns:
        Parsed JSON data

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If JSON is invalid
    """
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    try:
        async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
            content = await f.read()
            return json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {filepath}: {str(e)}")


async def write_json_file(filepath: Path, data: Dict[str, Any], indent: int = 2) -> None:
    """
    Write data to a JSON file asynchronously with atomic writes.

    Args:
        filepath: Path to JSON file
        data: Data to write
        indent: JSON indentation level

    Raises:
        ValueError: If write fails
    """
    try:
        # Ensure directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Write to temporary file first
        temp_filepath = filepath.with_suffix('.json.tmp')
        async with aiofiles.open(temp_filepath, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, indent=indent, default=str))

        # Atomic rename
        temp_filepath.rename(filepath)
    except Exception as e:
        raise ValueError(f"Failed to write JSON file {filepath}: {str(e)}")


async def delete_file(filepath: Path) -> None:
    """
    Delete a file.

    Args:
        filepath: Path to file to delete

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    filepath.unlink()


def validate_filepath(filepath: str, base_dir: Path) -> Path:
    """
    Validate that filepath is within base_dir (prevent directory traversal).

    Args:
        filepath: Relative filepath
        base_dir: Base directory

    Returns:
        Resolved Path within base_dir

    Raises:
        ValueError: If filepath is outside base_dir
    """
    full_path = (base_dir / filepath).resolve()
    if not str(full_path).startswith(str(base_dir.resolve())):
        raise ValueError(f"Invalid file path: {filepath}")
    return full_path


def list_files(directory: Path, extension: str = None) -> List[Path]:
    """
    List all files in a directory, optionally filtered by extension.

    Args:
        directory: Directory to list
        extension: Optional file extension filter (e.g., '.md', '.json')

    Returns:
        List of file paths
    """
    if not directory.exists():
        return []

    if extension:
        return sorted(directory.glob(f"*{extension}"))
    return sorted([f for f in directory.iterdir() if f.is_file()])


def generate_id_from_filename(filename: str) -> str:
    """
    Generate an ID from a filename by removing extension and normalizing.

    Args:
        filename: Filename (with or without extension)

    Returns:
        Normalized ID

    Example:
        "Elena Blackwood.md" -> "elena-blackwood"
    """
    # Remove extension
    name = Path(filename).stem
    # Convert to lowercase and replace spaces with hyphens
    return name.lower().replace(" ", "-")
