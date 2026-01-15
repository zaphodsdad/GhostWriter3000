"""Backup management API endpoints."""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel

from app.config import settings
from app.utils.backup import (
    list_scene_versions,
    list_snapshots,
    restore_scene_version,
    restore_snapshot,
    create_snapshot,
    backup_scene
)

router = APIRouter()


class SceneVersion(BaseModel):
    """A backup version of a scene."""
    filename: str
    timestamp: str
    reason: str
    word_count: int
    is_canon: bool


class Snapshot(BaseModel):
    """A project snapshot."""
    directory: str
    name: str
    timestamp: str
    reason: str
    scene_count: int


class RestoreRequest(BaseModel):
    """Request to restore from backup."""
    version: str  # filename for scene, directory for snapshot


class CheckpointRequest(BaseModel):
    """Request to create a manual checkpoint."""
    name: str


def ensure_project_exists(project_id: str):
    """Check that project exists, raise 404 if not."""
    if not settings.project_dir(project_id).exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")


@router.get("/scenes/{scene_id}/versions", response_model=List[SceneVersion])
async def get_scene_versions(project_id: str, scene_id: str):
    """
    List all backup versions for a scene.

    Args:
        project_id: Project ID
        scene_id: Scene ID

    Returns:
        List of backup versions, newest first
    """
    ensure_project_exists(project_id)

    versions = await list_scene_versions(project_id, scene_id)
    return versions


@router.post("/scenes/{scene_id}/restore")
async def restore_scene(project_id: str, scene_id: str, request: RestoreRequest):
    """
    Restore a scene from a backup version.

    Creates a backup of current state before restoring.

    Args:
        project_id: Project ID
        scene_id: Scene ID
        request: Contains version filename to restore

    Returns:
        Success message
    """
    ensure_project_exists(project_id)

    success = await restore_scene_version(project_id, scene_id, request.version)

    if not success:
        raise HTTPException(status_code=404, detail=f"Backup version not found: {request.version}")

    return {"message": f"Scene {scene_id} restored from {request.version}"}


@router.get("/snapshots", response_model=List[Snapshot])
async def get_snapshots(project_id: str):
    """
    List all project snapshots.

    Args:
        project_id: Project ID

    Returns:
        List of snapshots, newest first
    """
    ensure_project_exists(project_id)

    snapshots = await list_snapshots(project_id)
    return snapshots


@router.post("/snapshots/restore")
async def restore_from_snapshot(project_id: str, request: RestoreRequest):
    """
    Restore entire project from a snapshot.

    WARNING: This overwrites current project structure!
    Creates a backup before restoring.

    Args:
        project_id: Project ID
        request: Contains snapshot directory to restore

    Returns:
        Success message
    """
    ensure_project_exists(project_id)

    success = await restore_snapshot(project_id, request.version)

    if not success:
        raise HTTPException(status_code=404, detail=f"Snapshot not found: {request.version}")

    return {"message": f"Project restored from snapshot {request.version}"}


@router.post("/checkpoint")
async def create_checkpoint(project_id: str, request: CheckpointRequest):
    """
    Create a manual checkpoint (named snapshot).

    Checkpoints are never auto-deleted - use for important milestones.

    Args:
        project_id: Project ID
        request: Contains checkpoint name

    Returns:
        Created snapshot info
    """
    ensure_project_exists(project_id)

    snapshot_path = await create_snapshot(project_id, request.name, reason="checkpoint")

    if not snapshot_path:
        raise HTTPException(status_code=500, detail="Failed to create checkpoint")

    return {
        "message": f"Checkpoint '{request.name}' created",
        "path": snapshot_path
    }


@router.post("/scenes/{scene_id}/backup")
async def manual_scene_backup(project_id: str, scene_id: str):
    """
    Manually create a backup of a scene.

    Args:
        project_id: Project ID
        scene_id: Scene ID

    Returns:
        Backup path
    """
    ensure_project_exists(project_id)

    backup_path = await backup_scene(project_id, scene_id, reason="manual")

    if not backup_path:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    return {
        "message": f"Scene {scene_id} backed up",
        "path": backup_path
    }
