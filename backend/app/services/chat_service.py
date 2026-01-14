"""Chat service for AI conversations with full context."""

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from app.models.chat import (
    Conversation, ChatMessage, ChatScope, EditAction,
    ChatRequest, ChatResponse
)
from app.models.scene import Scene
from app.services.llm_service import get_llm_service
from app.services.markdown_parser import MarkdownParser
from app.utils.file_utils import read_json_file, write_json_file, list_files
from app.utils.logging import get_logger
from app.config import settings

logger = get_logger(__name__)


class ChatService:
    """Service for AI-powered chat with full project context."""

    def __init__(self):
        self.llm = get_llm_service()
        self.parser = MarkdownParser()

    def _get_chat_dir(self, project_id: str) -> Path:
        """Get chat storage directory for a project."""
        chat_dir = settings.project_dir(project_id) / "chat"
        chat_dir.mkdir(parents=True, exist_ok=True)
        return chat_dir

    def _get_conversation_path(self, project_id: str, scope: ChatScope, scope_id: Optional[str]) -> Path:
        """Get path for a conversation file."""
        chat_dir = self._get_chat_dir(project_id)
        if scope == ChatScope.PROJECT:
            return chat_dir / "project.json"
        else:
            return chat_dir / f"{scope.value}-{scope_id}.json"

    async def get_or_create_conversation(
        self,
        project_id: str,
        scope: ChatScope,
        scope_id: Optional[str] = None,
        model: Optional[str] = None
    ) -> Conversation:
        """Get existing conversation or create new one."""
        filepath = self._get_conversation_path(project_id, scope, scope_id)

        if filepath.exists():
            data = await read_json_file(filepath)
            return Conversation.model_validate(data)

        # Create new conversation
        conv = Conversation(
            id=str(uuid.uuid4()),
            project_id=project_id,
            scope=scope,
            scope_id=scope_id,
            model=model,
            messages=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        await write_json_file(filepath, conv.model_dump(mode='json'))
        return conv

    async def save_conversation(self, project_id: str, conversation: Conversation) -> None:
        """Save conversation to disk."""
        filepath = self._get_conversation_path(project_id, conversation.scope, conversation.scope_id)
        await write_json_file(filepath, conversation.model_dump(mode='json'))

    async def clear_conversation(self, project_id: str, scope: ChatScope, scope_id: Optional[str]) -> None:
        """Clear conversation history."""
        filepath = self._get_conversation_path(project_id, scope, scope_id)
        if filepath.exists():
            filepath.unlink()

    async def list_conversations(self, project_id: str) -> List[Dict[str, Any]]:
        """List all conversations in a project."""
        chat_dir = self._get_chat_dir(project_id)
        conversations = []

        for filepath in chat_dir.glob("*.json"):
            try:
                data = await read_json_file(filepath)
                conv = Conversation.model_validate(data)

                # Get scope title
                scope_title = await self._get_scope_title(project_id, conv.scope, conv.scope_id)

                # Get last message preview
                last_preview = None
                if conv.messages:
                    last_msg = conv.messages[-1]
                    last_preview = last_msg.content[:100] + "..." if len(last_msg.content) > 100 else last_msg.content

                conversations.append({
                    "id": conv.id,
                    "scope": conv.scope.value,
                    "scope_id": conv.scope_id,
                    "scope_title": scope_title,
                    "message_count": len(conv.messages),
                    "last_message_preview": last_preview,
                    "updated_at": conv.updated_at.isoformat()
                })
            except Exception:
                continue

        return sorted(conversations, key=lambda c: c["updated_at"], reverse=True)

    async def _get_scope_title(self, project_id: str, scope: ChatScope, scope_id: Optional[str]) -> str:
        """Get human-readable title for a scope."""
        if scope == ChatScope.PROJECT:
            # Load project title
            project_file = settings.project_dir(project_id) / "project.json"
            if project_file.exists():
                data = await read_json_file(project_file)
                return data.get("title", "Project")
            return "Project"

        elif scope == ChatScope.SCENE:
            scene_file = settings.scenes_dir(project_id) / f"{scope_id}.json"
            if scene_file.exists():
                data = await read_json_file(scene_file)
                return data.get("title", scope_id)
            return scope_id or "Scene"

        elif scope == ChatScope.CHAPTER:
            chapter_file = settings.project_dir(project_id) / "chapters" / f"{scope_id}.json"
            if chapter_file.exists():
                data = await read_json_file(chapter_file)
                return f"Chapter {data.get('chapter_number', '?')}: {data.get('title', scope_id)}"
            return scope_id or "Chapter"

        return "Unknown"

    async def send_message(
        self,
        project_id: str,
        scope: ChatScope,
        scope_id: Optional[str],
        request: ChatRequest
    ) -> ChatResponse:
        """Send a message and get AI response."""
        # Get or create conversation
        conversation = await self.get_or_create_conversation(
            project_id, scope, scope_id, request.model
        )

        # Add user message
        user_message = ChatMessage(
            role="user",
            content=request.message,
            timestamp=datetime.utcnow()
        )
        conversation.messages.append(user_message)

        # Build context
        context = await self._build_context(project_id, scope, scope_id)

        # Build system prompt with edit instructions
        system_prompt = self._build_system_prompt(context, scope)

        # Build messages for LLM
        llm_messages = self._build_llm_messages(conversation.messages)

        # Get AI response
        model = request.model or conversation.model
        response_text = await self._call_llm(system_prompt, llm_messages, model)

        # Parse response for edits
        clean_response, edits = await self._parse_and_apply_edits(
            project_id, response_text
        )

        # Create assistant message
        assistant_message = ChatMessage(
            role="assistant",
            content=clean_response,
            timestamp=datetime.utcnow(),
            edits_made=edits
        )
        conversation.messages.append(assistant_message)

        # Update and save conversation
        conversation.updated_at = datetime.utcnow()
        await self.save_conversation(project_id, conversation)

        return ChatResponse(
            message=assistant_message,
            edits_applied=edits,
            conversation_id=conversation.id
        )

    async def _build_context(
        self,
        project_id: str,
        scope: ChatScope,
        scope_id: Optional[str]
    ) -> Dict[str, Any]:
        """Build context based on scope."""
        context = {
            "characters": [],
            "worlds": [],
            "scenes": [],
            "current_scene": None,
            "current_chapter": None,
            "style_guide": None
        }

        # Load style guide
        style_path = settings.project_dir(project_id) / "style.json"
        if style_path.exists():
            try:
                context["style_guide"] = await read_json_file(style_path)
            except Exception:
                pass

        # Load all characters
        chars_dir = settings.characters_dir(project_id)
        if chars_dir.exists():
            for filepath in chars_dir.glob("*.md"):
                try:
                    parsed = self.parser.parse_file(filepath)
                    context["characters"].append(parsed)
                except Exception:
                    continue

        # Load all world contexts
        world_dir = settings.world_dir(project_id)
        if world_dir.exists():
            for filepath in world_dir.glob("*.md"):
                try:
                    parsed = self.parser.parse_file(filepath)
                    context["worlds"].append(parsed)
                except Exception:
                    continue

        # Load scenes based on scope
        if scope == ChatScope.PROJECT:
            # Load all canon scene summaries
            scenes_dir = settings.scenes_dir(project_id)
            if scenes_dir.exists():
                for filepath in scenes_dir.glob("*.json"):
                    try:
                        data = await read_json_file(filepath)
                        if data.get("is_canon") and data.get("summary"):
                            context["scenes"].append({
                                "id": data.get("id"),
                                "title": data.get("title"),
                                "summary": data.get("summary"),
                                "chapter_id": data.get("chapter_id")
                            })
                    except Exception:
                        continue

        elif scope == ChatScope.CHAPTER:
            # Load all scenes in this chapter
            scenes_dir = settings.scenes_dir(project_id)
            chapter_file = settings.project_dir(project_id) / "chapters" / f"{scope_id}.json"

            if chapter_file.exists():
                context["current_chapter"] = await read_json_file(chapter_file)

            if scenes_dir.exists():
                for filepath in scenes_dir.glob("*.json"):
                    try:
                        data = await read_json_file(filepath)
                        if data.get("chapter_id") == scope_id:
                            context["scenes"].append({
                                "id": data.get("id"),
                                "title": data.get("title"),
                                "outline": data.get("outline"),
                                "summary": data.get("summary"),
                                "is_canon": data.get("is_canon", False),
                                "prose": data.get("prose") if data.get("is_canon") else None
                            })
                    except Exception:
                        continue

        elif scope == ChatScope.SCENE:
            # Load the specific scene and previous summaries
            scene_file = settings.scenes_dir(project_id) / f"{scope_id}.json"
            if scene_file.exists():
                data = await read_json_file(scene_file)
                context["current_scene"] = data

                # Load previous scene summaries
                for prev_id in data.get("previous_scene_ids", []):
                    prev_file = settings.scenes_dir(project_id) / f"{prev_id}.json"
                    if prev_file.exists():
                        try:
                            prev_data = await read_json_file(prev_file)
                            if prev_data.get("is_canon") and prev_data.get("summary"):
                                context["scenes"].append({
                                    "id": prev_data.get("id"),
                                    "title": prev_data.get("title"),
                                    "summary": prev_data.get("summary")
                                })
                        except Exception:
                            continue

        return context

    def _build_system_prompt(self, context: Dict[str, Any], scope: ChatScope) -> str:
        """Build system prompt with context and edit instructions."""
        parts = [
            "You are an AI writing assistant with full knowledge of this creative project.",
            "You can discuss the story, characters, world, and provide writing advice.",
            "",
            "IMPORTANT: You can edit project elements. To make an edit, include it in your response using this exact format:",
            "```edit",
            "{",
            '  "entity_type": "character|world|scene",',
            '  "entity_id": "the-id",',
            '  "field": "field_name",',
            '  "new_value": "the new value"',
            "}",
            "```",
            "",
            "For characters, editable fields: name, role, age, occupation, background, personality_traits",
            "For scenes, editable fields: title, outline, tone, pov, additional_notes",
            "For world contexts, editable fields: name, era, technology_level, magic_system, content",
            "",
            "Only make edits when the user asks you to update something. Always explain what you're changing.",
            "",
            "=== PROJECT CONTEXT ===",
            ""
        ]

        # Add style guide first (most important for shaping advice)
        style = context.get("style_guide")
        if style:
            parts.append("STYLE GUIDE:")
            parts.append("When discussing writing or prose, keep this style guide in mind:")
            if style.get("pov"):
                parts.append(f"- POV: {style['pov']}")
            if style.get("tense"):
                parts.append(f"- Tense: {style['tense']}")
            if style.get("tone"):
                parts.append(f"- Tone: {style['tone']}")
            if style.get("heat_level"):
                parts.append(f"- Heat Level: {style['heat_level']}")
            if style.get("guide"):
                # Include summary of guide (truncated for chat context)
                guide_preview = style['guide'][:2000]
                if len(style['guide']) > 2000:
                    guide_preview += "...[truncated]"
                parts.append(f"\nFull Style Guide:\n{guide_preview}")
            parts.append("")

        # Add characters
        if context["characters"]:
            parts.append("CHARACTERS:")
            for char in context["characters"]:
                meta = char.get("metadata", {})
                parts.append(f"- {meta.get('name', char.get('id', 'Unknown'))} ({meta.get('role', 'Unknown role')})")
                if meta.get("background"):
                    parts.append(f"  Background: {meta['background'][:200]}...")
            parts.append("")

        # Add world contexts
        if context["worlds"]:
            parts.append("WORLD CONTEXT:")
            for world in context["worlds"]:
                meta = world.get("metadata", {})
                parts.append(f"- {meta.get('name', world.get('id', 'Unknown'))}")
                if world.get("content"):
                    parts.append(f"  {world['content'][:300]}...")
            parts.append("")

        # Add scene summaries
        if context["scenes"]:
            parts.append("SCENE SUMMARIES (for continuity):")
            for scene in context["scenes"]:
                parts.append(f"- {scene.get('title', 'Untitled')}: {scene.get('summary', scene.get('outline', 'No summary'))[:200]}...")
            parts.append("")

        # Add current focus
        if context.get("current_scene"):
            scene = context["current_scene"]
            parts.append("CURRENT SCENE (in focus):")
            parts.append(f"Title: {scene.get('title')}")
            parts.append(f"Outline: {scene.get('outline')}")
            if scene.get("prose"):
                parts.append(f"Prose: {scene.get('prose')[:500]}...")
            parts.append("")

        if context.get("current_chapter"):
            chapter = context["current_chapter"]
            parts.append("CURRENT CHAPTER (in focus):")
            parts.append(f"Title: Chapter {chapter.get('chapter_number')}: {chapter.get('title')}")
            if chapter.get("description"):
                parts.append(f"Description: {chapter.get('description')}")
            parts.append("")

        return "\n".join(parts)

    def _build_llm_messages(self, messages: List[ChatMessage]) -> List[Dict[str, str]]:
        """Convert conversation messages to LLM format."""
        return [{"role": m.role, "content": m.content} for m in messages]

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
                logger.error(f"Chat LLM call failed: {str(e)}")
                raise Exception(f"Failed to get AI response: {str(e)}")

    async def _parse_and_apply_edits(
        self,
        project_id: str,
        response_text: str
    ) -> Tuple[str, List[EditAction]]:
        """Parse edit blocks from response and apply them."""
        edits = []
        clean_response = response_text

        # Find all edit blocks
        edit_pattern = r'```edit\s*\n(.*?)\n```'
        matches = re.findall(edit_pattern, response_text, re.DOTALL)

        for match in matches:
            try:
                edit_data = json.loads(match)
                edit_action = await self._apply_edit(project_id, edit_data)
                if edit_action:
                    edits.append(edit_action)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse edit JSON: {match}")
            except Exception as e:
                logger.warning(f"Failed to apply edit: {str(e)}")

        # Remove edit blocks from response for clean display
        clean_response = re.sub(edit_pattern, '', response_text, flags=re.DOTALL)
        clean_response = clean_response.strip()

        return clean_response, edits

    async def _apply_edit(self, project_id: str, edit_data: Dict[str, Any]) -> Optional[EditAction]:
        """Apply a single edit to the project."""
        entity_type = edit_data.get("entity_type")
        entity_id = edit_data.get("entity_id")
        field = edit_data.get("field")
        new_value = edit_data.get("new_value")

        if not all([entity_type, entity_id, field, new_value]):
            return None

        old_value = None

        try:
            if entity_type == "character":
                filepath = settings.characters_dir(project_id) / f"{entity_id}.md"
                if filepath.exists():
                    parsed = self.parser.parse_file(filepath)
                    old_value = str(parsed.get("metadata", {}).get(field, ""))

                    # Update metadata
                    parsed["metadata"][field] = new_value

                    # Write back as markdown
                    self._write_markdown_file(filepath, parsed)

            elif entity_type == "world":
                filepath = settings.world_dir(project_id) / f"{entity_id}.md"
                if filepath.exists():
                    parsed = self.parser.parse_file(filepath)

                    if field == "content":
                        old_value = parsed.get("content", "")[:100]
                        parsed["content"] = new_value
                    else:
                        old_value = str(parsed.get("metadata", {}).get(field, ""))
                        parsed["metadata"][field] = new_value

                    self._write_markdown_file(filepath, parsed)

            elif entity_type == "scene":
                filepath = settings.scenes_dir(project_id) / f"{entity_id}.json"
                if filepath.exists():
                    data = await read_json_file(filepath)
                    old_value = str(data.get(field, ""))[:100]
                    data[field] = new_value
                    data["updated_at"] = datetime.utcnow().isoformat()
                    await write_json_file(filepath, data)

            return EditAction(
                entity_type=entity_type,
                entity_id=entity_id,
                field=field,
                old_value=old_value,
                new_value=new_value[:100] + "..." if len(str(new_value)) > 100 else new_value,
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Failed to apply edit: {str(e)}")
            return None

    def _write_markdown_file(self, filepath: Path, data: Dict[str, Any]) -> None:
        """Write parsed data back as markdown with YAML frontmatter."""
        import yaml

        metadata = data.get("metadata", {})
        content = data.get("content", "")

        yaml_str = yaml.dump(metadata, default_flow_style=False, allow_unicode=True)

        with open(filepath, 'w') as f:
            f.write("---\n")
            f.write(yaml_str)
            f.write("---\n\n")
            f.write(content)


# Global service instance
_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """Get or create the global chat service instance."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
