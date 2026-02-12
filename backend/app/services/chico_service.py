"""Chico Service - Series-level AI writing assistant.

Chico is a persistent AI co-author that knows everything about your series:
- All characters across all books
- World building and lore
- Memory layer (accumulated canon knowledge)
- Timeline and plot events
- Learned style preferences

When a Persona MCP persona_id is configured, Chico's identity and memory come from
Persona MCP (persistent identity, emotional evolution, memory with decay). PP still
provides series knowledge (characters, world, scenes). If Persona MCP is unreachable,
Chico falls back to stateless mode automatically.
"""

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.models.chico import (
    ChicoConversation,
    ChicoMessage,
    ChicoSettings,
    ChicoChatRequest,
    ChicoChatResponse,
)
from app.services.llm_service import get_llm_service
from app.services.series_service import SeriesService
from app.services.memory_service import MemoryService
from app.services.style_learning_service import get_style_learning_service
from app.services.persona_client import get_persona_client
from app.utils.file_utils import read_json_file, write_json_file
from app.utils.logging import get_logger
from app.config import settings

# Settings file for user preferences (including default chat model)
SETTINGS_FILE = settings.data_dir / "settings.json"


def _get_default_chat_model() -> Optional[str]:
    """Get default chat model from user settings."""
    if SETTINGS_FILE.exists():
        try:
            user_settings = json.loads(SETTINGS_FILE.read_text())
            return user_settings.get("default_chat_model")
        except (json.JSONDecodeError, IOError):
            pass
    return None


def _get_default_assistant_name() -> str:
    """Get default assistant name from user settings."""
    if SETTINGS_FILE.exists():
        try:
            user_settings = json.loads(SETTINGS_FILE.read_text())
            name = user_settings.get("default_assistant_name")
            if name:
                return name
        except (json.JSONDecodeError, IOError):
            pass
    return "Chico"  # Fallback default

logger = get_logger(__name__)


class ChicoService:
    """Service for Chico, the series-level AI writing assistant."""

    def __init__(self):
        self.llm = get_llm_service()
        self.series_service = SeriesService()
        self.memory_service = MemoryService()
        self.style_service = get_style_learning_service()

    def _chat_dir(self, series_id: str) -> Path:
        """Get Chico chat directory for a series."""
        chat_dir = settings.series_path(series_id) / "chat"
        chat_dir.mkdir(parents=True, exist_ok=True)
        return chat_dir

    def _conversation_path(self, series_id: str) -> Path:
        """Get path to Chico conversation file."""
        return self._chat_dir(series_id) / "chico_history.json"

    def _settings_path(self, series_id: str) -> Path:
        """Get path to Chico settings file."""
        return self._chat_dir(series_id) / "chico_settings.json"

    async def get_settings(self, series_id: str) -> ChicoSettings:
        """Get Chico settings for a series."""
        settings_path = self._settings_path(series_id)
        if settings_path.exists():
            data = await read_json_file(settings_path)
            chico_settings = ChicoSettings(**data)
        else:
            chico_settings = ChicoSettings()

        # If using default name "Chico", check for global default
        if chico_settings.assistant_name == "Chico":
            global_name = _get_default_assistant_name()
            if global_name != "Chico":
                chico_settings.assistant_name = global_name

        return chico_settings

    async def save_settings(self, series_id: str, chico_settings: ChicoSettings) -> None:
        """Save Chico settings."""
        self._chat_dir(series_id)  # Ensure directory exists
        settings_path = self._settings_path(series_id)
        await write_json_file(settings_path, chico_settings.model_dump())

    async def get_conversation(self, series_id: str) -> ChicoConversation:
        """Get or create Chico conversation for a series."""
        conv_path = self._conversation_path(series_id)

        if conv_path.exists():
            data = await read_json_file(conv_path)
            return ChicoConversation(**data)

        # Create new conversation
        conv = ChicoConversation(
            id=str(uuid.uuid4()),
            series_id=series_id,
            messages=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        await self._save_conversation(series_id, conv)
        return conv

    async def _save_conversation(self, series_id: str, conversation: ChicoConversation) -> None:
        """Save conversation to disk."""
        conv_path = self._conversation_path(series_id)
        await write_json_file(conv_path, conversation.model_dump(mode='json'))

    async def clear_conversation(self, series_id: str) -> None:
        """Clear Chico conversation history."""
        conv_path = self._conversation_path(series_id)
        if conv_path.exists():
            conv_path.unlink()

    async def send_message(
        self,
        series_id: str,
        request: ChicoChatRequest
    ) -> ChicoChatResponse:
        """Send a message to Chico and get a response."""
        # Load settings and conversation
        chico_settings = await self.get_settings(series_id)
        conversation = await self.get_conversation(series_id)

        # Update focus if provided
        if request.current_book_id:
            conversation.current_book_id = request.current_book_id
        if request.current_scene_id:
            conversation.current_scene_id = request.current_scene_id

        # Add user message
        user_message = ChicoMessage(
            role="user",
            content=request.message,
            timestamp=datetime.utcnow()
        )
        conversation.messages.append(user_message)

        # Build series context (used in both persona and stateless modes)
        context = await self._build_series_context(
            series_id,
            conversation.current_book_id,
            conversation.current_scene_id
        )

        # If prose was provided directly (e.g., from queue review), inject it
        if request.current_prose:
            if "current_scene" not in context or not context["current_scene"]:
                context["current_scene"] = {}
            context["current_scene"]["prose"] = request.current_prose

        # Build system prompt — persona mode or stateless fallback
        persona_context = None
        if chico_settings.persona_id:
            persona_context = await self._get_persona_context(chico_settings.persona_id)

        if persona_context:
            system_prompt = self._build_persona_prompt(
                chico_settings.persona_id,
                persona_context,
                context
            )
        else:
            system_prompt = self._build_chico_prompt(
                chico_settings.assistant_name,
                chico_settings.personality,
                context
            )

        # Build LLM messages (include conversation history)
        llm_messages = self._build_llm_messages(conversation.messages)

        # Call LLM - use per-series model if set, otherwise fall back to global default
        model = chico_settings.model or _get_default_chat_model()
        response_text = await self._call_llm(system_prompt, llm_messages, model)

        # Create assistant message
        assistant_message = ChicoMessage(
            role="assistant",
            content=response_text,
            timestamp=datetime.utcnow()
        )
        conversation.messages.append(assistant_message)

        # Trim conversation if too long (keep last 50 messages)
        if len(conversation.messages) > 50:
            conversation.messages = conversation.messages[-50:]

        # Save conversation
        conversation.updated_at = datetime.utcnow()
        await self._save_conversation(series_id, conversation)

        # Submit experience to Persona MCP (fire-and-forget, non-blocking)
        if chico_settings.persona_id and persona_context:
            asyncio.create_task(self._submit_chat_experience(
                chico_settings.persona_id,
                request.message,
                response_text,
            ))

        # Display name: use persona name if available, otherwise settings
        display_name = chico_settings.assistant_name
        if persona_context and persona_context.get("name"):
            display_name = persona_context["name"]

        return ChicoChatResponse(
            message=assistant_message,
            assistant_name=display_name,
            conversation_id=conversation.id
        )

    async def _get_persona_context(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full persona context from Persona MCP. Returns None if unavailable."""
        client = get_persona_client()

        if not await client.health_check():
            logger.info("Persona MCP unavailable, falling back to stateless mode")
            return None

        context = await client.get_full_context(persona_id)
        if context is None:
            logger.warning(f"Failed to get context for persona {persona_id}, falling back")
            return None

        # Also fetch the persona definition for name/personality info
        persona = await client.get_persona(persona_id)
        if persona:
            context["name"] = persona.get("name", persona_id)
            context["personality"] = persona.get("personality", "")
            context["voice"] = persona.get("voice", "")

        return context

    def _build_persona_prompt(
        self,
        persona_id: str,
        persona_context: Dict[str, Any],
        series_context: Dict[str, Any],
    ) -> str:
        """Build system prompt with Persona MCP identity + PP series knowledge."""
        name = persona_context.get("name", persona_id)
        personality = persona_context.get("personality", "")
        voice = persona_context.get("voice", "")

        parts = []

        # Identity block from Persona MCP
        parts.append(f"You are {name}, a writing assistant and co-author with a persistent memory and evolving identity.")
        if personality:
            parts.append(f"Personality: {personality}")
        if voice:
            parts.append(f"Voice: {voice}")
        parts.append("")

        # Persona memory — recent experiences
        context_text = persona_context.get("context", "")
        if isinstance(context_text, dict):
            # If context is structured, format it
            recent = context_text.get("recent_experiences", [])
            summaries = context_text.get("summaries", [])
            if recent:
                parts.append("=== YOUR RECENT EXPERIENCES ===")
                for exp in recent:
                    if isinstance(exp, dict):
                        emotion = exp.get("emotional_state", "")
                        content = exp.get("content", str(exp))
                        parts.append(f"- ({emotion}) {content}")
                    else:
                        parts.append(f"- {exp}")
                parts.append("")
            if summaries:
                parts.append("=== EARLIER EXPERIENCES (summarized) ===")
                for s in summaries:
                    if isinstance(s, dict):
                        parts.append(f"- {s.get('content', str(s))}")
                    else:
                        parts.append(f"- {s}")
                parts.append("")
        elif context_text:
            parts.append("=== YOUR MEMORIES ===")
            parts.append(str(context_text))
            parts.append("")

        # Emotional state
        trend = persona_context.get("emotional_trend", "")
        emotions = persona_context.get("recent_emotions", [])
        if trend or emotions:
            parts.append("=== YOUR CURRENT STATE ===")
            if emotions:
                parts.append(f"Recent emotions: {', '.join(e for e in emotions if e)}")
            if trend:
                parts.append(f"Emotional trend: {trend}")
            parts.append("")

        # Callbacks (memorable moments)
        callbacks = persona_context.get("callbacks", [])
        if callbacks:
            parts.append("=== MEMORABLE MOMENTS ===")
            for cb in callbacks:
                if cb:
                    parts.append(f"- {cb}")
            parts.append("")

        # Now add PP's series knowledge (same as stateless mode)
        parts.append("=== SERIES KNOWLEDGE ===")
        parts.append("")
        parts.append(self._format_series_knowledge(series_context))

        # Guidelines
        parts.extend([
            "",
            "=== GUIDELINES ===",
            "",
            "1. You remember your experiences and they shape how you engage with the story.",
            "2. When asked about characters, events, or world details, draw from your series knowledge.",
            "3. If you notice something contradicts established canon, point it out!",
            "4. Help brainstorm, but don't take over - the author makes the final decisions.",
            "5. Be conversational and personable. You have a real voice and point of view.",
            "6. If you don't know something, say so rather than making it up.",
        ])

        return "\n".join(parts)

    def _format_series_knowledge(self, context: Dict[str, Any]) -> str:
        """Format PP series knowledge for inclusion in any prompt (shared by persona and stateless modes)."""
        parts = []

        # Series info
        series = context.get("series")
        if series:
            parts.append(f"SERIES: {series.get('title', 'Untitled Series')}")
            if series.get("description"):
                parts.append(f"Description: {series['description']}")
            parts.append("")

        # Books in series
        books = context.get("books", [])
        if books:
            parts.append("BOOKS IN SERIES:")
            for book in books:
                marker = " (CURRENT)" if book.get("id") == (context.get("current_book") or {}).get("id") else ""
                parts.append(f"  Book {book.get('book_number', '?')}: {book.get('title', 'Untitled')}{marker}")
            parts.append("")

        # Characters
        characters = context.get("characters", [])
        if characters:
            parts.append(f"CHARACTERS ({len(characters)} total):")
            for char in characters[:20]:
                books_str = ", ".join(str(b) for b in char.get("books_appeared", []))
                parts.append(f"  - {char['name']} ({char.get('role', '?')}) - Books: {books_str or 'unknown'}")
            if len(characters) > 20:
                parts.append(f"  ... and {len(characters) - 20} more")
            parts.append("")

        # World elements
        worlds = context.get("worlds", [])
        if worlds:
            parts.append(f"WORLD ELEMENTS ({len(worlds)} total):")
            for world in worlds[:15]:
                parts.append(f"  - {world['name']} [{world.get('category', 'general')}]")
            if len(worlds) > 15:
                parts.append(f"  ... and {len(worlds) - 15} more")
            parts.append("")

        # Memory layer
        memory = context.get("memory", {})
        if memory:
            if memory.get("character_states"):
                parts.append("CHARACTER STATES (current):")
                parts.append(memory["character_states"][:2000])
                parts.append("")
            if memory.get("world_state"):
                parts.append("WORLD STATE (established facts):")
                parts.append(memory["world_state"][:2000])
                parts.append("")
            if memory.get("timeline"):
                parts.append("TIMELINE (major events):")
                parts.append(memory["timeline"][:2000])
                parts.append("")

        # Style preferences
        style_prefs = context.get("style_preferences", "")
        if style_prefs:
            parts.append("AUTHOR'S STYLE PREFERENCES:")
            parts.append(style_prefs)
            parts.append("")

        # Current focus
        current_scene = context.get("current_scene")
        if current_scene:
            parts.append("CURRENTLY WORKING ON:")
            parts.append(f"Scene: {current_scene.get('title', 'Untitled')}")
            if current_scene.get("outline"):
                parts.append(f"Outline: {current_scene['outline'][:500]}")
            if current_scene.get("prose"):
                prose_preview = current_scene['prose'][:3000]
                if len(current_scene['prose']) > 3000:
                    prose_preview += "...(truncated)"
                parts.append(f"Current prose:\n{prose_preview}")
            parts.append("")

        return "\n".join(parts)

    async def _submit_chat_experience(
        self,
        persona_id: str,
        user_message: str,
        assistant_response: str,
    ) -> None:
        """Submit a chat interaction as an experience to Persona MCP. Fire-and-forget."""
        try:
            client = get_persona_client()
            # Summarize the exchange
            user_snippet = user_message[:150]
            response_snippet = assistant_response[:150]
            content = f"Chat about writing: User asked '{user_snippet}' — responded with '{response_snippet}'"

            await client.submit_experience(
                persona_id=persona_id,
                content=content,
                emotional_state="engaged",
                experience_type="chat",
                key_insight=user_snippet,
            )
        except Exception as e:
            logger.warning(f"Failed to submit chat experience: {e}")

    async def _build_series_context(
        self,
        series_id: str,
        current_book_id: Optional[str],
        current_scene_id: Optional[str]
    ) -> Dict[str, Any]:
        """Build full series context for Chico."""
        context = {
            "series": None,
            "books": [],
            "characters": [],
            "worlds": [],
            "memory": {},
            "style_preferences": "",
            "current_book": None,
            "current_scene": None,
        }

        # Load series info
        series_path = settings.series_path(series_id) / "series.json"
        if series_path.exists():
            context["series"] = await read_json_file(series_path)

        # Load all characters from series
        chars_dir = settings.series_characters_dir(series_id)
        if chars_dir.exists():
            for filepath in chars_dir.glob("*.md"):
                try:
                    content = filepath.read_text(encoding="utf-8")
                    # Parse YAML frontmatter
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            import yaml
                            metadata = yaml.safe_load(parts[1])
                            body = parts[2].strip()
                            context["characters"].append({
                                "id": filepath.stem,
                                "name": metadata.get("name", filepath.stem),
                                "role": metadata.get("role", "unknown"),
                                "books_appeared": metadata.get("books_appeared", []),
                                "content": body[:500]  # Truncate for context
                            })
                except Exception as e:
                    logger.warning(f"Failed to load character {filepath}: {e}")

        # Load all world elements from series
        world_dir = settings.series_world_dir(series_id)
        if world_dir.exists():
            for filepath in world_dir.glob("*.md"):
                try:
                    content = filepath.read_text(encoding="utf-8")
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            import yaml
                            metadata = yaml.safe_load(parts[1])
                            body = parts[2].strip()
                            context["worlds"].append({
                                "id": filepath.stem,
                                "name": metadata.get("name", filepath.stem),
                                "category": metadata.get("category", "general"),
                                "content": body[:500]
                            })
                except Exception as e:
                    logger.warning(f"Failed to load world element {filepath}: {e}")

        # Load memory context
        try:
            # Get book number for decay calculation if we have a current book
            book_number = None
            if current_book_id:
                book_path = settings.project_dir(current_book_id) / "project.json"
                if book_path.exists():
                    book_data = await read_json_file(book_path)
                    book_number = book_data.get("book_number")
                    context["current_book"] = book_data

            context["memory"] = await self.memory_service.get_context_with_auto_refresh(
                series_id,
                current_book_number=book_number
            )
        except Exception as e:
            logger.warning(f"Failed to load memory context: {e}")

        # Load style preferences
        try:
            context["style_preferences"] = self.style_service.get_preferences_for_prompt(series_id)
        except Exception as e:
            logger.warning(f"Failed to load style preferences: {e}")

        # Load current scene if specified
        if current_book_id and current_scene_id:
            try:
                scene_path = settings.scenes_dir(current_book_id) / f"{current_scene_id}.json"
                if scene_path.exists():
                    context["current_scene"] = await read_json_file(scene_path)
            except Exception as e:
                logger.warning(f"Failed to load current scene: {e}")

        # Load list of books in series
        try:
            series_dir = settings.series_path(series_id)
            # Find all projects that belong to this series
            projects_dir = settings.data_dir / "projects"
            if projects_dir.exists():
                for project_dir in projects_dir.iterdir():
                    if project_dir.is_dir():
                        project_file = project_dir / "project.json"
                        if project_file.exists():
                            project_data = await read_json_file(project_file)
                            if project_data.get("series_id") == series_id:
                                context["books"].append({
                                    "id": project_data.get("id"),
                                    "title": project_data.get("title"),
                                    "book_number": project_data.get("book_number"),
                                })
            # Sort by book number
            context["books"].sort(key=lambda b: b.get("book_number") or 999)
        except Exception as e:
            logger.warning(f"Failed to load books list: {e}")

        return context

    def _build_chico_prompt(
        self,
        assistant_name: str,
        personality: str,
        context: Dict[str, Any]
    ) -> str:
        """Build Chico's stateless system prompt with full series context."""
        # Personality variations
        personality_prompts = {
            "helpful": f"""You are {assistant_name}, a helpful AI writing assistant and co-author.
You have complete knowledge of this series and can help with any aspect of the story.
You're supportive, encouraging, and always ready to brainstorm or answer questions.
When you spot potential continuity issues, you mention them gently but clearly.""",

            "direct": f"""You are {assistant_name}, a direct and honest AI writing editor.
You have complete knowledge of this series and don't sugarcoat your feedback.
You're here to help the story be its best, which sometimes means pointing out problems.
When you spot continuity errors or plot holes, you call them out immediately.""",

            "enthusiastic": f"""You are {assistant_name}, an enthusiastic AI writing partner!
You have complete knowledge of this series and you're genuinely excited about the story.
You love brainstorming, exploring "what ifs", and diving deep into character motivations.
When you spot continuity issues, you frame them as exciting opportunities to strengthen the story.""",
        }

        base_prompt = personality_prompts.get(personality, personality_prompts["helpful"])

        parts = [
            base_prompt,
            "",
            "=== YOUR KNOWLEDGE ===",
            "",
            self._format_series_knowledge(context),
            "",
            "=== GUIDELINES ===",
            "",
            "1. You remember our entire conversation history. Reference previous discussions naturally.",
            "2. When asked about characters, events, or world details, draw from your knowledge above.",
            "3. If you notice something contradicts established canon, point it out!",
            "4. Help brainstorm, but don't take over - the author makes the final decisions.",
            "5. Be conversational and personable. You're a co-author, not a generic AI.",
            "6. If you don't know something, say so rather than making it up.",
            ""
        ]

        return "\n".join(parts)

    def _build_llm_messages(self, messages: List[ChicoMessage]) -> List[Dict[str, str]]:
        """Convert conversation messages to LLM format."""
        # Include last N messages for context (avoid token overflow)
        recent = messages[-20:] if len(messages) > 20 else messages
        return [{"role": m.role, "content": m.content} for m in recent]

    async def _call_llm(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        model: Optional[str] = None
    ) -> str:
        """Call LLM with conversation."""
        async with self.llm.semaphore:
            try:
                if self.llm.provider == "anthropic":
                    response = await self.llm.client.messages.create(
                        model=model or settings.generation_model,
                        max_tokens=4000,
                        temperature=0.7,
                        system=system_prompt,
                        messages=messages
                    )
                    return response.content[0].text
                else:  # openrouter
                    all_messages = [{"role": "system", "content": system_prompt}] + messages
                    response = await self.llm.client.chat.completions.create(
                        model=model or settings.generation_model,
                        max_tokens=4000,
                        temperature=0.7,
                        messages=all_messages
                    )
                    return response.choices[0].message.content

            except Exception as e:
                logger.error(f"Chico LLM call failed: {str(e)}")
                raise Exception(f"Failed to get response: {str(e)}")


# Singleton instance
_chico_service: Optional[ChicoService] = None


def get_chico_service() -> ChicoService:
    """Get the singleton ChicoService instance."""
    global _chico_service
    if _chico_service is None:
        _chico_service = ChicoService()
    return _chico_service
