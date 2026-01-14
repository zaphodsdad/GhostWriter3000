"""Generation pipeline orchestration service (project-scoped)."""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.models.generation import GenerationState, GenerationStatus, Iteration
from app.models.scene import Scene
from app.services.llm_service import get_llm_service
from app.services.state_manager import get_state_manager
from app.services.markdown_parser import MarkdownParser
from app.services.series_service import get_series_service
from app.utils.prompt_templates import build_system_prompt, build_generation_prompt, clean_prose_output
from app.utils.file_utils import read_json_file, write_json_file
from app.utils.logging import get_logger
from app.config import settings

logger = get_logger(__name__)


class GenerationService:
    """Orchestrates the generation pipeline."""

    def __init__(self):
        """Initialize generation service."""
        self.llm = get_llm_service()
        self.state_manager = get_state_manager()
        self.parser = MarkdownParser()
        self.series_service = get_series_service()

    async def start_generation(
        self,
        project_id: str,
        scene_id: str,
        max_iterations: int = 5,
        generation_model: Optional[str] = None,
        critique_model: Optional[str] = None
    ) -> GenerationState:
        """
        Start a new generation pipeline for a scene.

        Args:
            project_id: Project ID
            scene_id: Scene ID to generate
            max_iterations: Maximum revision iterations allowed
            generation_model: Optional model for prose generation (uses .env default if None)
            critique_model: Optional model for critique (uses .env default if None)

        Returns:
            Initial generation state

        Raises:
            FileNotFoundError: If scene not found
            ValueError: If scene data invalid
        """
        # Load scene
        scene = await self._load_scene(project_id, scene_id)

        # Auto-calculate previous canon scenes based on structural order
        previous_scene_ids = await self._get_previous_canon_scenes(project_id, scene_id)

        logger.info(
            f"Found {len(previous_scene_ids)} previous canon scenes for continuity",
            extra={"scene_id": scene_id, "previous_count": len(previous_scene_ids)}
        )

        # Create new generation state
        generation_id = str(uuid.uuid4())
        state = GenerationState(
            generation_id=generation_id,
            project_id=project_id,
            scene_id=scene_id,
            status=GenerationStatus.INITIALIZED,
            max_iterations=max_iterations,
            character_ids=scene.character_ids,
            world_context_ids=scene.world_context_ids,
            previous_scene_ids=previous_scene_ids,
            generation_model=generation_model,
            critique_model=critique_model
        )

        # Save initial state
        await self.state_manager.save_state(state)

        logger.info(
            f"Starting generation for scene {scene_id}",
            extra={"generation_id": generation_id, "project_id": project_id, "scene_id": scene_id}
        )

        # Start generation in background (don't await)
        import asyncio
        asyncio.create_task(self._run_generation(project_id, generation_id))

        return state

    async def start_edit_mode_generation(
        self,
        project_id: str,
        scene_id: str,
        max_iterations: int = 5,
        generation_model: Optional[str] = None,
        critique_model: Optional[str] = None
    ) -> GenerationState:
        """
        Start edit mode generation for a scene with imported prose.

        This skips initial generation and goes directly to critique.
        The scene must be in edit mode with original_prose set.

        Args:
            project_id: Project ID
            scene_id: Scene ID to edit
            max_iterations: Maximum revision iterations allowed
            generation_model: Optional model for revisions
            critique_model: Optional model for critique

        Returns:
            Initial generation state

        Raises:
            FileNotFoundError: If scene not found
            ValueError: If scene not in edit mode or missing prose
        """
        # Load scene
        scene = await self._load_scene(project_id, scene_id)

        # Validate edit mode
        if not scene.edit_mode:
            raise ValueError(f"Scene {scene_id} is not in edit mode. Enable edit mode first.")

        if not scene.original_prose:
            raise ValueError(f"Scene {scene_id} has no imported prose. Import prose first.")

        # Auto-calculate previous canon scenes based on structural order
        previous_scene_ids = await self._get_previous_canon_scenes(project_id, scene_id)

        logger.info(
            f"Found {len(previous_scene_ids)} previous canon scenes for edit mode continuity",
            extra={"scene_id": scene_id, "previous_count": len(previous_scene_ids)}
        )

        # Create new generation state
        generation_id = str(uuid.uuid4())
        state = GenerationState(
            generation_id=generation_id,
            project_id=project_id,
            scene_id=scene_id,
            status=GenerationStatus.INITIALIZED,
            max_iterations=max_iterations,
            character_ids=scene.character_ids,
            world_context_ids=scene.world_context_ids,
            previous_scene_ids=previous_scene_ids,
            generation_model=generation_model,
            critique_model=critique_model,
            edit_mode=True
        )

        # Save initial state
        await self.state_manager.save_state(state)

        logger.info(
            f"Starting edit mode generation for scene {scene_id}",
            extra={"generation_id": generation_id, "project_id": project_id, "scene_id": scene_id}
        )

        # Start edit mode generation in background
        import asyncio
        asyncio.create_task(self._run_edit_mode_generation(project_id, generation_id))

        return state

    async def _run_edit_mode_generation(self, project_id: str, generation_id: str) -> None:
        """
        Run edit mode generation - skip initial generation, go straight to critique.

        Args:
            project_id: Project ID
            generation_id: Generation ID
        """
        try:
            # Load state
            state = await self.state_manager.load_state(project_id, generation_id)
            state.status = GenerationStatus.GENERATING
            state.updated_at = datetime.utcnow()
            await self.state_manager.save_state(state)

            # Load scene to get the original prose
            scene = await self._load_scene(project_id, state.scene_id)

            # Use the imported original prose as the first iteration
            iteration = Iteration(
                iteration_number=1,
                prose=scene.original_prose,
                critique=None,
                approved=None,
                timestamp=datetime.utcnow()
            )

            # Update state
            state.current_iteration = 1
            state.iterations.append(iteration)
            state.status = GenerationStatus.GENERATION_COMPLETE
            state.updated_at = datetime.utcnow()
            await self.state_manager.save_state(state)

            # Go directly to critique
            await self._run_critique(project_id, generation_id)

        except Exception as e:
            logger.error(
                f"Edit mode generation failed: {str(e)}",
                extra={"generation_id": generation_id, "project_id": project_id},
                exc_info=True
            )
            # Update state with error
            state = await self.state_manager.load_state(project_id, generation_id)
            state.status = GenerationStatus.ERROR
            state.error_message = str(e)
            state.updated_at = datetime.utcnow()
            await self.state_manager.save_state(state)

    async def _run_generation(self, project_id: str, generation_id: str) -> None:
        """
        Run the initial generation process.

        Args:
            project_id: Project ID
            generation_id: Generation ID
        """
        try:
            # Load state
            state = await self.state_manager.load_state(project_id, generation_id)
            state.status = GenerationStatus.GENERATING
            state.updated_at = datetime.utcnow()
            await self.state_manager.save_state(state)

            # Load scene
            scene = await self._load_scene(project_id, state.scene_id)

            # Load combined context (handles series inheritance and references)
            combined_context = await self.series_service.get_combined_context(project_id)

            # Also load scene-specific characters/world that may not be in combined context
            scene_characters = await self._load_characters(project_id, state.character_ids)
            scene_worlds = await self._load_world_contexts(project_id, state.world_context_ids)
            previous_summaries = await self._load_previous_summaries(project_id, state.previous_scene_ids)

            # Merge scene-specific context with combined context
            all_characters = combined_context.get("characters", []) + scene_characters
            all_worlds = combined_context.get("worlds", []) + scene_worlds
            all_references = [r for r in combined_context.get("references", []) if r.get("use_in_generation", True)]
            previous_books = combined_context.get("previous_books", [])
            style_guide = combined_context.get("style_guide")

            # Build prompts with full context including references
            system_prompt = build_system_prompt(
                all_characters,
                all_worlds,
                previous_summaries,
                style_guide,
                references=all_references,
                previous_books=previous_books
            )
            user_prompt = build_generation_prompt(scene.model_dump())

            # Generate prose (use custom model if specified)
            prose = await self.llm.generate_prose(
                system_prompt, user_prompt, model=state.generation_model
            )

            # Clean any AI preambles from the output
            prose = clean_prose_output(prose)

            # Create iteration
            iteration = Iteration(
                iteration_number=1,
                prose=prose,
                critique=None,
                approved=None,
                timestamp=datetime.utcnow()
            )

            # Update state
            state.current_iteration = 1
            state.iterations.append(iteration)
            state.status = GenerationStatus.GENERATION_COMPLETE
            state.updated_at = datetime.utcnow()
            await self.state_manager.save_state(state)

            # Auto-run critique
            await self._run_critique(project_id, generation_id)

        except Exception as e:
            logger.error(
                f"Generation failed: {str(e)}",
                extra={"generation_id": generation_id, "project_id": project_id},
                exc_info=True
            )
            # Update state with error
            state = await self.state_manager.load_state(project_id, generation_id)
            state.status = GenerationStatus.ERROR
            state.error_message = str(e)
            state.updated_at = datetime.utcnow()
            await self.state_manager.save_state(state)

    async def _run_critique(self, project_id: str, generation_id: str) -> None:
        """
        Run critique on current prose.

        Args:
            project_id: Project ID
            generation_id: Generation ID
        """
        try:
            # Load state
            state = await self.state_manager.load_state(project_id, generation_id)
            state.status = GenerationStatus.CRITIQUING
            state.updated_at = datetime.utcnow()
            await self.state_manager.save_state(state)

            # Get current prose
            current_prose = state.iterations[-1].prose

            # Load style guide for critique reference
            style_guide = await self._load_style_guide(project_id)

            # Generate critique (use custom model if specified)
            critique = await self.llm.critique_prose(
                current_prose, model=state.critique_model, style_guide=style_guide
            )

            # Update iteration with critique
            state.iterations[-1].critique = critique
            state.status = GenerationStatus.AWAITING_APPROVAL
            state.updated_at = datetime.utcnow()
            await self.state_manager.save_state(state)

        except Exception as e:
            # Update state with error
            state = await self.state_manager.load_state(project_id, generation_id)
            state.status = GenerationStatus.ERROR
            state.error_message = str(e)
            state.updated_at = datetime.utcnow()
            await self.state_manager.save_state(state)

    async def approve_and_revise(self, project_id: str, generation_id: str) -> GenerationState:
        """
        Approve current iteration and start revision.

        Args:
            project_id: Project ID
            generation_id: Generation ID

        Returns:
            Updated generation state

        Raises:
            ValueError: If generation not awaiting approval or max iterations reached
        """
        state = await self.state_manager.load_state(project_id, generation_id)

        if state.status != GenerationStatus.AWAITING_APPROVAL:
            raise ValueError(f"Generation not awaiting approval (status: {state.status})")

        if state.current_iteration >= state.max_iterations:
            raise ValueError(f"Max iterations ({state.max_iterations}) reached")

        # Mark current iteration as approved
        state.iterations[-1].approved = True
        await self.state_manager.save_state(state)

        # Start revision in background
        import asyncio
        asyncio.create_task(self._run_revision(project_id, generation_id))

        return state

    async def _run_revision(self, project_id: str, generation_id: str) -> None:
        """
        Run revision based on critique.

        Args:
            project_id: Project ID
            generation_id: Generation ID
        """
        try:
            # Load state
            state = await self.state_manager.load_state(project_id, generation_id)
            state.status = GenerationStatus.REVISING
            state.updated_at = datetime.utcnow()
            await self.state_manager.save_state(state)

            # Load scene and context
            scene = await self._load_scene(project_id, state.scene_id)
            characters = await self._load_characters(project_id, state.character_ids)
            world_contexts = await self._load_world_contexts(project_id, state.world_context_ids)
            previous_summaries = await self._load_previous_summaries(project_id, state.previous_scene_ids)
            style_guide = await self._load_style_guide(project_id)

            # Build system prompt
            system_prompt = build_system_prompt(characters, world_contexts, previous_summaries, style_guide)

            # Get current prose and critique
            current_prose = state.iterations[-1].prose
            critique = state.iterations[-1].critique

            # Revise prose (use custom model if specified)
            revised_prose = await self.llm.revise_prose(
                current_prose, critique, system_prompt, model=state.generation_model
            )

            # Clean any AI preambles from the output
            revised_prose = clean_prose_output(revised_prose)

            # Create new iteration
            iteration = Iteration(
                iteration_number=state.current_iteration + 1,
                prose=revised_prose,
                critique=None,
                approved=None,
                timestamp=datetime.utcnow()
            )

            # Update state
            state.current_iteration += 1
            state.iterations.append(iteration)
            state.status = GenerationStatus.GENERATION_COMPLETE
            state.updated_at = datetime.utcnow()
            await self.state_manager.save_state(state)

            # Auto-run critique
            await self._run_critique(project_id, generation_id)

        except Exception as e:
            # Update state with error
            state = await self.state_manager.load_state(project_id, generation_id)
            state.status = GenerationStatus.ERROR
            state.error_message = str(e)
            state.updated_at = datetime.utcnow()
            await self.state_manager.save_state(state)

    async def accept_final(self, project_id: str, generation_id: str) -> GenerationState:
        """
        Accept current prose as final and generate summary.

        Args:
            project_id: Project ID
            generation_id: Generation ID

        Returns:
            Updated generation state

        Raises:
            ValueError: If generation not awaiting approval
        """
        state = await self.state_manager.load_state(project_id, generation_id)

        if state.status != GenerationStatus.AWAITING_APPROVAL:
            raise ValueError(f"Generation not awaiting approval (status: {state.status})")

        # Mark current iteration as approved
        state.iterations[-1].approved = True

        # Save final prose
        state.final_prose = state.iterations[-1].prose

        await self.state_manager.save_state(state)

        # Generate summary in background
        import asyncio
        asyncio.create_task(self._generate_summary(project_id, generation_id))

        return state

    async def _generate_summary(self, project_id: str, generation_id: str) -> None:
        """
        Generate scene summary.

        Args:
            project_id: Project ID
            generation_id: Generation ID
        """
        try:
            # Load state
            state = await self.state_manager.load_state(project_id, generation_id)
            state.status = GenerationStatus.GENERATING_SUMMARY
            state.updated_at = datetime.utcnow()
            await self.state_manager.save_state(state)

            # Load scene for title
            scene = await self._load_scene(project_id, state.scene_id)

            # Generate summary
            summary = await self.llm.generate_summary(scene.title, state.final_prose)

            # Update state
            state.scene_summary = summary
            state.status = GenerationStatus.COMPLETED
            state.updated_at = datetime.utcnow()
            await self.state_manager.save_state(state)

            # Update scene with final prose, summary, and mark as canon
            await self._update_scene_as_canon(
                project_id=project_id,
                scene_id=state.scene_id,
                prose=state.final_prose,
                summary=summary
            )

            logger.info(
                f"Generation completed and scene marked as canon",
                extra={"generation_id": generation_id, "project_id": project_id, "scene_id": state.scene_id}
            )

        except Exception as e:
            # Update state with error
            state = await self.state_manager.load_state(project_id, generation_id)
            state.status = GenerationStatus.ERROR
            state.error_message = str(e)
            state.updated_at = datetime.utcnow()
            await self.state_manager.save_state(state)

    async def reject_generation(self, project_id: str, generation_id: str) -> GenerationState:
        """
        Reject generation and mark as rejected.

        Args:
            project_id: Project ID
            generation_id: Generation ID

        Returns:
            Updated generation state
        """
        state = await self.state_manager.load_state(project_id, generation_id)

        # Mark current iteration as not approved
        if state.iterations:
            state.iterations[-1].approved = False

        state.status = GenerationStatus.REJECTED
        state.updated_at = datetime.utcnow()
        await self.state_manager.save_state(state)

        return state

    async def get_state(self, project_id: str, generation_id: str) -> GenerationState:
        """
        Get current generation state.

        Args:
            project_id: Project ID
            generation_id: Generation ID

        Returns:
            Generation state
        """
        return await self.state_manager.load_state(project_id, generation_id)

    # Helper methods for loading data

    async def _load_scene(self, project_id: str, scene_id: str) -> Scene:
        """Load scene from file."""
        filepath = settings.scenes_dir(project_id) / f"{scene_id}.json"
        data = await read_json_file(filepath)
        return Scene.model_validate(data)

    async def _load_characters(self, project_id: str, character_ids: List[str]) -> List[Dict[str, Any]]:
        """Load characters from markdown files."""
        characters = []
        for char_id in character_ids:
            filepath = settings.characters_dir(project_id) / f"{char_id}.md"
            if filepath.exists():
                parsed = self.parser.parse_file(filepath)
                characters.append(parsed)
        return characters

    async def _load_world_contexts(self, project_id: str, world_ids: List[str]) -> List[Dict[str, Any]]:
        """Load world contexts from markdown files."""
        contexts = []
        for world_id in world_ids:
            filepath = settings.world_dir(project_id) / f"{world_id}.md"
            if filepath.exists():
                parsed = self.parser.parse_file(filepath)
                contexts.append(parsed)
        return contexts

    async def _load_previous_summaries(self, project_id: str, scene_ids: List[str]) -> List[Dict[str, Any]]:
        """Load previous scene summaries for continuity."""
        summaries = []
        for scene_id in scene_ids:
            filepath = settings.scenes_dir(project_id) / f"{scene_id}.json"
            if filepath.exists():
                data = await read_json_file(filepath)
                scene = Scene.model_validate(data)

                # Only include if scene is canon and has a summary
                if scene.is_canon and scene.summary:
                    summaries.append({
                        "title": scene.title,
                        "summary": scene.summary
                    })

        return summaries

    async def _get_previous_canon_scenes(
        self,
        project_id: str,
        current_scene_id: str,
        max_scenes: int = 10
    ) -> List[str]:
        """
        Get IDs of previous canon scenes based on structural order.

        Scenes are ordered by: act_number → chapter_number → scene_number

        Args:
            project_id: Project ID
            current_scene_id: The scene we're generating (to find position)
            max_scenes: Maximum number of previous scenes to return

        Returns:
            List of scene IDs for previous canon scenes, in chronological order
        """
        # Load all acts
        acts_dir = settings.project_dir(project_id) / "acts"
        acts = {}
        if acts_dir.exists():
            for filepath in acts_dir.glob("*.json"):
                try:
                    data = await read_json_file(filepath)
                    acts[data["id"]] = data.get("act_number", 999)
                except Exception:
                    pass

        # Load all chapters
        chapters_dir = settings.project_dir(project_id) / "chapters"
        chapters = {}
        if chapters_dir.exists():
            for filepath in chapters_dir.glob("*.json"):
                try:
                    data = await read_json_file(filepath)
                    chapter_id = data["id"]
                    act_id = data.get("act_id", "")
                    act_number = acts.get(act_id, 999)
                    chapter_number = data.get("chapter_number", 999)
                    chapters[chapter_id] = (act_number, chapter_number)
                except Exception:
                    pass

        # Load all scenes
        scenes_dir = settings.scenes_dir(project_id)
        scenes_with_order = []
        if scenes_dir.exists():
            for filepath in scenes_dir.glob("*.json"):
                try:
                    data = await read_json_file(filepath)
                    scene_id = data["id"]
                    chapter_id = data.get("chapter_id", "")
                    scene_number = data.get("scene_number", 999)
                    is_canon = data.get("is_canon", False)
                    has_summary = bool(data.get("summary"))

                    # Get ordering from chapter
                    act_number, chapter_number = chapters.get(chapter_id, (999, 999))

                    scenes_with_order.append({
                        "id": scene_id,
                        "act_number": act_number,
                        "chapter_number": chapter_number,
                        "scene_number": scene_number,
                        "is_canon": is_canon,
                        "has_summary": has_summary
                    })
                except Exception:
                    pass

        # Sort by act → chapter → scene
        scenes_with_order.sort(key=lambda s: (s["act_number"], s["chapter_number"], s["scene_number"]))

        # Find current scene's position
        current_index = -1
        for i, scene in enumerate(scenes_with_order):
            if scene["id"] == current_scene_id:
                current_index = i
                break

        if current_index <= 0:
            return []

        # Get previous canon scenes (up to max_scenes)
        previous_canon = []
        for scene in scenes_with_order[:current_index]:
            if scene["is_canon"] and scene["has_summary"]:
                previous_canon.append(scene["id"])

        # Return last N scenes
        return previous_canon[-max_scenes:]

    async def _load_style_guide(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Load style guide for the project."""
        filepath = settings.project_dir(project_id) / "style.json"
        if filepath.exists():
            try:
                data = await read_json_file(filepath)
                return data
            except Exception:
                return None
        return None

    async def _update_scene_as_canon(
        self,
        project_id: str,
        scene_id: str,
        prose: str,
        summary: str
    ) -> None:
        """
        Update scene with final prose, summary, and mark as canon.

        Args:
            project_id: Project ID
            scene_id: Scene ID to update
            prose: Final prose text
            summary: Generated summary
        """
        filepath = settings.scenes_dir(project_id) / f"{scene_id}.json"
        data = await read_json_file(filepath)

        # Update scene fields
        data["prose"] = prose
        data["summary"] = summary
        data["is_canon"] = True
        data["updated_at"] = datetime.utcnow().isoformat()

        # Save back to file
        await write_json_file(filepath, data)


# Global service instance
_generation_service: Optional['GenerationService'] = None


def get_generation_service() -> GenerationService:
    """Get or create the global generation service instance."""
    global _generation_service
    if _generation_service is None:
        _generation_service = GenerationService()
    return _generation_service
