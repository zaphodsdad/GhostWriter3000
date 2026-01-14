"""Application configuration management."""

import json
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

# Check for global config override before Settings class is instantiated
GLOBAL_CONFIG_FILE = Path.home() / ".prose-pipeline-config.json"


def _get_data_dir_override() -> Path | None:
    """Check global config for data_dir override."""
    if GLOBAL_CONFIG_FILE.exists():
        try:
            config = json.loads(GLOBAL_CONFIG_FILE.read_text())
            if "data_dir" in config and config["data_dir"]:
                return Path(config["data_dir"])
        except (json.JSONDecodeError, IOError):
            pass
    return None


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM API Configuration
    llm_provider: str = "openrouter"  # "anthropic" or "openrouter"
    anthropic_api_key: str = "placeholder"  # Only needed if llm_provider = "anthropic"
    openrouter_api_key: str = ""  # Only needed if llm_provider = "openrouter"

    # Generation Settings
    max_iterations: int = 5
    generation_model: str = "anthropic/claude-opus-4-20250514"  # OpenRouter format
    critique_model: str = "anthropic/claude-sonnet-4-20250514"  # OpenRouter format
    generation_temperature: float = 0.7
    critique_temperature: float = 0.3
    generation_max_tokens: int = 4000
    critique_max_tokens: int = 2000

    # Application Settings
    log_level: str = "info"
    data_dir: Path = _get_data_dir_override() or Path("./data")  # Check global config, then .env, then default
    cors_origins: List[str] = ["http://localhost:8000"]
    api_auth_key: str = ""  # Optional API key for authentication (empty = no auth)

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    @property
    def projects_dir(self) -> Path:
        """Path to projects directory."""
        return self.data_dir / "projects"

    def project_dir(self, project_id: str) -> Path:
        """Path to a specific project directory."""
        return self.projects_dir / project_id

    def characters_dir(self, project_id: str) -> Path:
        """Path to characters directory for a project."""
        return self.project_dir(project_id) / "characters"

    def world_dir(self, project_id: str) -> Path:
        """Path to world context directory for a project."""
        return self.project_dir(project_id) / "world"

    def scenes_dir(self, project_id: str) -> Path:
        """Path to scenes directory for a project."""
        return self.project_dir(project_id) / "scenes"

    def generations_dir(self, project_id: str) -> Path:
        """Path to generations directory for a project."""
        return self.project_dir(project_id) / "generations"


# Global settings instance
settings = Settings()
