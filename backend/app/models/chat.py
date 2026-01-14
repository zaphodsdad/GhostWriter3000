"""Chat conversation models."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class ChatScope(str, Enum):
    """Scope of a chat conversation."""
    SCENE = "scene"
    CHAPTER = "chapter"
    PROJECT = "project"


class EditAction(BaseModel):
    """Record of an edit made by the AI."""

    entity_type: str = Field(..., description="Type: character, world, scene")
    entity_id: str = Field(..., description="ID of entity edited")
    field: str = Field(..., description="Field that was modified")
    old_value: Optional[str] = Field(None, description="Previous value")
    new_value: str = Field(..., description="New value")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatMessage(BaseModel):
    """A single message in a conversation."""

    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    edits_made: List[EditAction] = Field(default_factory=list, description="Edits AI made")


class Conversation(BaseModel):
    """A chat conversation with context."""

    id: str = Field(..., description="Unique conversation identifier")
    project_id: str = Field(..., description="Project this conversation belongs to")
    scope: ChatScope = Field(..., description="Scope of the conversation")
    scope_id: Optional[str] = Field(None, description="ID of scene/chapter (null for project scope)")
    model: Optional[str] = Field(None, description="LLM model to use (null for default)")
    messages: List[ChatMessage] = Field(default_factory=list, description="Conversation history")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    """Request to send a message."""

    message: str = Field(..., description="User's message", min_length=1)
    model: Optional[str] = Field(None, description="Model override for this conversation")


class ChatResponse(BaseModel):
    """Response from chat endpoint."""

    message: ChatMessage = Field(..., description="The assistant's response")
    edits_applied: List[EditAction] = Field(default_factory=list, description="Edits that were applied")
    conversation_id: str = Field(..., description="Conversation ID")


class ConversationSummary(BaseModel):
    """Summary of a conversation for listing."""

    id: str
    scope: ChatScope
    scope_id: Optional[str]
    scope_title: Optional[str] = None
    message_count: int
    last_message_preview: Optional[str] = None
    updated_at: datetime
