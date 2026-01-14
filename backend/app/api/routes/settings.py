"""Settings API routes for managing user configuration."""

import json
import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Settings file location (inside data dir)
SETTINGS_FILE = settings.data_dir / "settings.json"

# Global config file location (fixed, outside data dir)
# This allows changing data_dir without losing the setting
GLOBAL_CONFIG_FILE = Path.home() / ".prose-pipeline-config.json"


class UserSettings(BaseModel):
    """User-configurable settings."""
    openrouter_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    custom_endpoint_url: Optional[str] = None
    custom_endpoint_key: Optional[str] = None
    default_generation_model: Optional[str] = None
    default_critique_model: Optional[str] = None


class DataDirSettings(BaseModel):
    """Data directory settings."""
    data_dir: str


class UserSettingsResponse(BaseModel):
    """Settings response (masks sensitive keys)."""
    openrouter_api_key_set: bool = False
    anthropic_api_key_set: bool = False
    custom_endpoint_url: Optional[str] = None
    custom_endpoint_key_set: bool = False
    default_generation_model: Optional[str] = None
    default_critique_model: Optional[str] = None
    data_dir: str = ""
    data_dir_from: str = ""  # "default", "env", "config"


def load_user_settings() -> dict:
    """Load user settings from file."""
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_user_settings(data: dict) -> None:
    """Save user settings to file."""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, indent=2))


def load_global_config() -> dict:
    """Load global config from fixed location."""
    if GLOBAL_CONFIG_FILE.exists():
        try:
            return json.loads(GLOBAL_CONFIG_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_global_config(data: dict) -> None:
    """Save global config to fixed location."""
    GLOBAL_CONFIG_FILE.write_text(json.dumps(data, indent=2))


def get_data_dir_info() -> tuple[str, str]:
    """
    Get current data directory and its source.

    Returns:
        Tuple of (data_dir_path, source) where source is "config", "env", or "default"
    """
    global_config = load_global_config()

    # Check global config first
    if "data_dir" in global_config and global_config["data_dir"]:
        return global_config["data_dir"], "config"

    # Check if DATA_DIR env var is set (different from default)
    env_data_dir = os.environ.get("DATA_DIR")
    if env_data_dir:
        return env_data_dir, "env"

    # Return current settings value (which may be from .env or default)
    return str(settings.data_dir.absolute()), "default"


def get_api_key(key_name: str) -> Optional[str]:
    """Get API key - check user settings first, then env."""
    user_settings = load_user_settings()

    # Check user settings first
    if key_name in user_settings and user_settings[key_name]:
        return user_settings[key_name]

    # Fall back to environment settings
    if key_name == "openrouter_api_key":
        return settings.openrouter_api_key if settings.openrouter_api_key else None
    elif key_name == "anthropic_api_key":
        return settings.anthropic_api_key if settings.anthropic_api_key != "placeholder" else None

    return None


@router.get("", response_model=UserSettingsResponse)
async def get_settings():
    """Get current settings (with masked keys)."""
    user_settings = load_user_settings()
    data_dir, data_dir_from = get_data_dir_info()

    return UserSettingsResponse(
        openrouter_api_key_set=bool(user_settings.get("openrouter_api_key") or settings.openrouter_api_key),
        anthropic_api_key_set=bool(user_settings.get("anthropic_api_key") or (settings.anthropic_api_key and settings.anthropic_api_key != "placeholder")),
        custom_endpoint_url=user_settings.get("custom_endpoint_url"),
        custom_endpoint_key_set=bool(user_settings.get("custom_endpoint_key")),
        default_generation_model=user_settings.get("default_generation_model"),
        default_critique_model=user_settings.get("default_critique_model"),
        data_dir=data_dir,
        data_dir_from=data_dir_from,
    )


@router.put("")
async def update_settings(new_settings: UserSettings):
    """Update settings. Only provided fields are updated."""
    current = load_user_settings()

    # Only update fields that were explicitly provided (not None)
    update_data = new_settings.model_dump(exclude_none=True)

    # Merge with current settings
    current.update(update_data)

    save_user_settings(current)

    return {"status": "ok", "message": "Settings updated"}


@router.delete("/key/{key_name}")
async def delete_key(key_name: str):
    """Remove a specific key from settings."""
    allowed_keys = ["openrouter_api_key", "anthropic_api_key", "custom_endpoint_url", "custom_endpoint_key"]
    if key_name not in allowed_keys:
        raise HTTPException(status_code=400, detail=f"Invalid key name: {key_name}")

    current = load_user_settings()
    if key_name in current:
        del current[key_name]
        save_user_settings(current)

    return {"status": "ok", "message": f"Key {key_name} removed"}


@router.put("/data-dir")
async def update_data_dir(data_dir_settings: DataDirSettings):
    """
    Update data directory location.

    Note: Requires server restart to take effect.
    """
    new_path = data_dir_settings.data_dir.strip()

    if not new_path:
        raise HTTPException(status_code=400, detail="Data directory path cannot be empty")

    # Validate path exists or can be created
    path = Path(new_path)
    if not path.exists():
        try:
            path.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as e:
            raise HTTPException(status_code=400, detail=f"Cannot create directory: {str(e)}")

    if not path.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    # Save to global config
    global_config = load_global_config()
    global_config["data_dir"] = str(path.absolute())
    save_global_config(global_config)

    return {
        "status": "ok",
        "message": "Data directory updated. Restart the server for changes to take effect.",
        "data_dir": str(path.absolute()),
        "restart_required": True
    }


@router.delete("/data-dir")
async def reset_data_dir():
    """
    Reset data directory to default (remove override).

    Note: Requires server restart to take effect.
    """
    global_config = load_global_config()

    if "data_dir" in global_config:
        del global_config["data_dir"]
        save_global_config(global_config)

    return {
        "status": "ok",
        "message": "Data directory reset to default. Restart the server for changes to take effect.",
        "restart_required": True
    }
