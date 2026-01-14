"""State management service for generation pipeline (project-scoped)."""

from pathlib import Path
from typing import List, Optional
from app.models.generation import GenerationState
from app.utils.file_utils import read_json_file, write_json_file, list_files
from app.config import settings


class StateManager:
    """Manages persistence of generation pipeline state."""

    def _get_storage_path(self, project_id: str) -> Path:
        """Get the storage path for a project's generations."""
        path = settings.generations_dir(project_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    async def save_state(self, state: GenerationState) -> None:
        """
        Save generation state to disk atomically.

        Args:
            state: Generation state to save (must include project_id)

        Raises:
            ValueError: If save fails
        """
        storage_path = self._get_storage_path(state.project_id)
        filepath = storage_path / f"{state.generation_id}.json"

        # Convert to dict for JSON serialization
        state_dict = state.model_dump(mode='json')

        await write_json_file(filepath, state_dict)

    async def load_state(self, project_id: str, generation_id: str) -> GenerationState:
        """
        Load generation state from disk.

        Args:
            project_id: Project ID
            generation_id: Unique generation identifier

        Returns:
            Generation state

        Raises:
            FileNotFoundError: If state file doesn't exist
            ValueError: If state is invalid
        """
        storage_path = self._get_storage_path(project_id)
        filepath = storage_path / f"{generation_id}.json"

        data = await read_json_file(filepath)

        return GenerationState.model_validate(data)

    async def list_generations(self, project_id: str) -> List[str]:
        """
        List all generation IDs in a project.

        Args:
            project_id: Project ID

        Returns:
            List of generation IDs
        """
        storage_path = self._get_storage_path(project_id)
        files = list_files(storage_path, extension=".json")
        return [f.stem for f in files]

    async def get_generations_by_status(
        self, project_id: str, status: Optional[str] = None
    ) -> List[GenerationState]:
        """
        Get all generations for a project, optionally filtered by status.

        Args:
            project_id: Project ID
            status: Optional status to filter by (e.g., 'awaiting_approval')

        Returns:
            List of GenerationState objects, sorted by created_at (newest first)
        """
        generation_ids = await self.list_generations(project_id)
        generations = []

        for gen_id in generation_ids:
            try:
                state = await self.load_state(project_id, gen_id)
                if status is None or state.status.value == status:
                    generations.append(state)
            except (FileNotFoundError, ValueError):
                # Skip invalid or missing files
                continue

        # Sort by created_at descending (newest first)
        generations.sort(key=lambda g: g.created_at, reverse=True)
        return generations

    async def delete_state(self, project_id: str, generation_id: str) -> None:
        """
        Delete generation state from disk.

        Args:
            project_id: Project ID
            generation_id: Unique generation identifier

        Raises:
            FileNotFoundError: If state file doesn't exist
        """
        storage_path = self._get_storage_path(project_id)
        filepath = storage_path / f"{generation_id}.json"

        if not filepath.exists():
            raise FileNotFoundError(f"Generation state not found: {generation_id}")

        filepath.unlink()

    def state_exists(self, project_id: str, generation_id: str) -> bool:
        """
        Check if generation state exists.

        Args:
            project_id: Project ID
            generation_id: Unique generation identifier

        Returns:
            True if state exists, False otherwise
        """
        storage_path = self._get_storage_path(project_id)
        filepath = storage_path / f"{generation_id}.json"
        return filepath.exists()


# Global service instance
_state_manager: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    """Get or create the global state manager instance."""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager
