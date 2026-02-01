"""Chico - Series-level AI writing assistant models."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ChicoMessage(BaseModel):
    """A single message in a Chico conversation."""

    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChicoConversation(BaseModel):
    """Chico conversation at series level."""

    id: str = Field(..., description="Conversation ID")
    series_id: str = Field(..., description="Series this conversation belongs to")
    messages: List[ChicoMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Conversation metadata
    current_book_id: Optional[str] = Field(
        None,
        description="Currently focused book (for context prioritization)"
    )
    current_scene_id: Optional[str] = Field(
        None,
        description="Currently focused scene (if any)"
    )


class ChicoSettings(BaseModel):
    """Settings for Chico assistant."""

    assistant_name: str = Field(
        default="Chico",
        description="Name of the AI assistant"
    )
    personality: str = Field(
        default="helpful",
        description="Personality style: helpful, direct, enthusiastic"
    )
    model: Optional[str] = Field(
        None,
        description="LLM model to use (null for default)"
    )
    enabled: bool = Field(
        default=True,
        description="Whether Chico is enabled"
    )


class ChicoChatRequest(BaseModel):
    """Request to send a message to Chico."""

    message: str = Field(..., description="User's message", min_length=1)
    current_book_id: Optional[str] = Field(
        None,
        description="Currently focused book for context"
    )
    current_scene_id: Optional[str] = Field(
        None,
        description="Currently focused scene for context"
    )


class ChicoChatResponse(BaseModel):
    """Response from Chico."""

    message: ChicoMessage = Field(..., description="Chico's response")
    assistant_name: str = Field(..., description="Name of the assistant")
    conversation_id: str = Field(..., description="Conversation ID")
