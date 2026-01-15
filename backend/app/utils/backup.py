"""Backup utilities for protecting project data."""

import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)

# Configuration
MAX_SCENE_VERSIONS = 10
MAX_SNAPSHOTS = 5


def get_backup_dir(project_id: str) -> Path:
    """Get the backup directory for a project, creating if needed."""
    backup_dir = settings.project_dir(project_id) / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def get_scene_backup_dir(project_id: str, scene_id: str) -> Path:
    """Get the backup directory for a specific scene."""
    scene_backup_dir = get_backup_dir(project_id) / "scenes" / scene_id
    scene_backup_dir.mkdir(parents=True, exist_ok=True)
    return scene_backup_dir


def get_snapshots_dir(project_id: str) -> Path:
    """Get the snapshots directory for a project."""
    snapshots_dir = get_backup_dir(project_id) / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    return snapshots_dir


def timestamp_str() -> str:
    """Generate a filesystem-safe timestamp string."""
    return datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")


async def backup_scene(project_id: str, scene_id: str, reason: str = "manual") -> Optional[str]:
    """
    Backup a scene before modification.

    Args:
        project_id: Project ID
        scene_id: Scene ID to backup
        reason: Why the backup was created (e.g., "pre-revision", "pre-delete")

    Returns:
        Path to backup file, or None if scene doesn't exist
    """
    scene_file = settings.scenes_dir(project_id) / f"{scene_id}.json"

    if not scene_file.exists():
        logger.warning(f"Cannot backup scene {scene_id} - file does not exist")
        return None

    try:
        # Read current scene data
        with open(scene_file, 'r') as f:
            scene_data = json.load(f)

        # Add backup metadata
        backup_data = {
            "backup_timestamp": datetime.utcnow().isoformat(),
            "backup_reason": reason,
            "scene_data": scene_data
        }

        # Write to backup directory
        backup_dir = get_scene_backup_dir(project_id, scene_id)
        backup_filename = f"{timestamp_str()}_{reason}.json"
        backup_path = backup_dir / backup_filename

        with open(backup_path, 'w') as f:
            json.dump(backup_data, f, indent=2)

        logger.info(f"Backed up scene {scene_id} to {backup_path}")

        # Cleanup old versions
        await cleanup_scene_versions(project_id, scene_id)

        return str(backup_path)

    except Exception as e:
        logger.error(f"Failed to backup scene {scene_id}: {e}")
        return None


async def backup_chapter(project_id: str, chapter_id: str, reason: str = "manual") -> Optional[str]:
    """Backup a chapter before modification."""
    chapter_file = settings.project_dir(project_id) / "chapters" / f"{chapter_id}.json"

    if not chapter_file.exists():
        return None

    try:
        with open(chapter_file, 'r') as f:
            chapter_data = json.load(f)

        backup_data = {
            "backup_timestamp": datetime.utcnow().isoformat(),
            "backup_reason": reason,
            "chapter_data": chapter_data
        }

        backup_dir = get_backup_dir(project_id) / "chapters" / chapter_id
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_filename = f"{timestamp_str()}_{reason}.json"
        backup_path = backup_dir / backup_filename

        with open(backup_path, 'w') as f:
            json.dump(backup_data, f, indent=2)

        logger.info(f"Backed up chapter {chapter_id} to {backup_path}")
        return str(backup_path)

    except Exception as e:
        logger.error(f"Failed to backup chapter {chapter_id}: {e}")
        return None


async def create_snapshot(project_id: str, name: str, reason: str = "manual") -> Optional[str]:
    """
    Create a full project snapshot.

    Args:
        project_id: Project ID
        name: Human-readable name for the snapshot
        reason: Why snapshot was created (e.g., "pre-import", "checkpoint")

    Returns:
        Path to snapshot directory, or None on failure
    """
    project_dir = settings.project_dir(project_id)

    if not project_dir.exists():
        logger.warning(f"Cannot snapshot project {project_id} - does not exist")
        return None

    try:
        # Create snapshot directory
        safe_name = "".join(c if c.isalnum() or c in "-_" else "-" for c in name)
        snapshot_name = f"{timestamp_str()}_{safe_name}"
        snapshot_dir = get_snapshots_dir(project_id) / snapshot_name
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        # Copy key directories
        dirs_to_backup = ["scenes", "chapters", "acts", "characters", "world"]

        for dir_name in dirs_to_backup:
            src_dir = project_dir / dir_name
            if src_dir.exists():
                dst_dir = snapshot_dir / dir_name
                shutil.copytree(src_dir, dst_dir)

        # Copy project.json if exists
        project_file = project_dir / "project.json"
        if project_file.exists():
            shutil.copy2(project_file, snapshot_dir / "project.json")

        # Write snapshot metadata
        metadata = {
            "snapshot_timestamp": datetime.utcnow().isoformat(),
            "snapshot_name": name,
            "snapshot_reason": reason,
            "project_id": project_id,
            "directories_backed_up": dirs_to_backup
        }

        with open(snapshot_dir / "snapshot_meta.json", 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Created snapshot '{name}' for project {project_id}")

        # Cleanup old snapshots
        await cleanup_old_snapshots(project_id)

        return str(snapshot_dir)

    except Exception as e:
        logger.error(f"Failed to create snapshot for project {project_id}: {e}")
        return None


async def cleanup_scene_versions(project_id: str, scene_id: str):
    """Remove old scene versions beyond MAX_SCENE_VERSIONS."""
    backup_dir = get_scene_backup_dir(project_id, scene_id)

    versions = sorted(backup_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    if len(versions) > MAX_SCENE_VERSIONS:
        for old_version in versions[MAX_SCENE_VERSIONS:]:
            old_version.unlink()
            logger.info(f"Pruned old backup: {old_version}")


async def cleanup_old_snapshots(project_id: str):
    """Remove old snapshots beyond MAX_SNAPSHOTS, keeping user checkpoints."""
    snapshots_dir = get_snapshots_dir(project_id)

    snapshots = []
    for snapshot_path in snapshots_dir.iterdir():
        if snapshot_path.is_dir():
            meta_file = snapshot_path / "snapshot_meta.json"
            if meta_file.exists():
                with open(meta_file, 'r') as f:
                    meta = json.load(f)
                # Don't auto-delete user checkpoints
                if meta.get("snapshot_reason") != "checkpoint":
                    snapshots.append((snapshot_path, meta_file.stat().st_mtime))

    # Sort by modification time, newest first
    snapshots.sort(key=lambda x: x[1], reverse=True)

    if len(snapshots) > MAX_SNAPSHOTS:
        for old_snapshot, _ in snapshots[MAX_SNAPSHOTS:]:
            shutil.rmtree(old_snapshot)
            logger.info(f"Pruned old snapshot: {old_snapshot}")


async def list_scene_versions(project_id: str, scene_id: str) -> List[Dict[str, Any]]:
    """List all backup versions for a scene."""
    backup_dir = get_scene_backup_dir(project_id, scene_id)

    if not backup_dir.exists():
        return []

    versions = []
    for backup_file in sorted(backup_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            with open(backup_file, 'r') as f:
                data = json.load(f)

            # Get word count from backed up prose
            scene_data = data.get("scene_data", {})
            prose = scene_data.get("prose") or scene_data.get("original_prose") or ""
            word_count = len(prose.split()) if prose else 0

            versions.append({
                "filename": backup_file.name,
                "timestamp": data.get("backup_timestamp"),
                "reason": data.get("backup_reason"),
                "word_count": word_count,
                "is_canon": scene_data.get("is_canon", False)
            })
        except Exception as e:
            logger.warning(f"Could not read backup {backup_file}: {e}")

    return versions


async def list_snapshots(project_id: str) -> List[Dict[str, Any]]:
    """List all snapshots for a project."""
    snapshots_dir = get_snapshots_dir(project_id)

    if not snapshots_dir.exists():
        return []

    snapshots = []
    for snapshot_path in sorted(snapshots_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if snapshot_path.is_dir():
            meta_file = snapshot_path / "snapshot_meta.json"
            if meta_file.exists():
                try:
                    with open(meta_file, 'r') as f:
                        meta = json.load(f)

                    # Count scenes in snapshot
                    scenes_dir = snapshot_path / "scenes"
                    scene_count = len(list(scenes_dir.glob("*.json"))) if scenes_dir.exists() else 0

                    snapshots.append({
                        "directory": snapshot_path.name,
                        "name": meta.get("snapshot_name"),
                        "timestamp": meta.get("snapshot_timestamp"),
                        "reason": meta.get("snapshot_reason"),
                        "scene_count": scene_count
                    })
                except Exception as e:
                    logger.warning(f"Could not read snapshot {snapshot_path}: {e}")

    return snapshots


async def restore_scene_version(project_id: str, scene_id: str, version_filename: str) -> bool:
    """
    Restore a scene from a backup version.

    Args:
        project_id: Project ID
        scene_id: Scene ID
        version_filename: Filename of the backup to restore

    Returns:
        True if successful, False otherwise
    """
    backup_dir = get_scene_backup_dir(project_id, scene_id)
    backup_file = backup_dir / version_filename

    if not backup_file.exists():
        logger.error(f"Backup file not found: {backup_file}")
        return False

    try:
        # First, backup the current version before restoring
        await backup_scene(project_id, scene_id, reason="pre-restore")

        # Read backup data
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)

        scene_data = backup_data.get("scene_data", {})

        # Update timestamp
        scene_data["updated_at"] = datetime.utcnow().isoformat()

        # Write restored data
        scene_file = settings.scenes_dir(project_id) / f"{scene_id}.json"
        with open(scene_file, 'w') as f:
            json.dump(scene_data, f, indent=2)

        logger.info(f"Restored scene {scene_id} from {version_filename}")
        return True

    except Exception as e:
        logger.error(f"Failed to restore scene {scene_id} from {version_filename}: {e}")
        return False


async def restore_snapshot(project_id: str, snapshot_directory: str) -> bool:
    """
    Restore a project from a snapshot.

    WARNING: This overwrites current project data!

    Args:
        project_id: Project ID
        snapshot_directory: Name of snapshot directory to restore

    Returns:
        True if successful, False otherwise
    """
    snapshots_dir = get_snapshots_dir(project_id)
    snapshot_path = snapshots_dir / snapshot_directory

    if not snapshot_path.exists():
        logger.error(f"Snapshot not found: {snapshot_path}")
        return False

    try:
        project_dir = settings.project_dir(project_id)

        # First, create a backup of current state
        await create_snapshot(project_id, "pre-restore-backup", reason="pre-restore")

        # Restore each directory
        dirs_to_restore = ["scenes", "chapters", "acts", "characters", "world"]

        for dir_name in dirs_to_restore:
            src_dir = snapshot_path / dir_name
            dst_dir = project_dir / dir_name

            if src_dir.exists():
                # Remove current directory
                if dst_dir.exists():
                    shutil.rmtree(dst_dir)
                # Copy from snapshot
                shutil.copytree(src_dir, dst_dir)

        # Restore project.json if in snapshot
        project_backup = snapshot_path / "project.json"
        if project_backup.exists():
            shutil.copy2(project_backup, project_dir / "project.json")

        logger.info(f"Restored project {project_id} from snapshot {snapshot_directory}")
        return True

    except Exception as e:
        logger.error(f"Failed to restore project {project_id} from snapshot: {e}")
        return False
