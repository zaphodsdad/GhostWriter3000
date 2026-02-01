"""Chico API endpoints - Series-level AI writing assistant."""

from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any

from app.models.chico import (
    ChicoConversation,
    ChicoSettings,
    ChicoChatRequest,
    ChicoChatResponse,
    ChicoMessage,
)
from app.services.chico_service import get_chico_service
from app.config import settings

router = APIRouter()


def ensure_series_exists(series_id: str) -> None:
    """Verify series exists, raise 404 if not."""
    series_path = settings.series_path(series_id)
    if not series_path.exists():
        raise HTTPException(status_code=404, detail=f"Series not found: {series_id}")


# =============================================================================
# Chat Endpoints
# =============================================================================

@router.post("/{series_id}/chat", response_model=ChicoChatResponse)
async def send_message(series_id: str, request: ChicoChatRequest):
    """
    Send a message to Chico and get a response.

    Chico is your series-level AI co-author who knows:
    - All characters across all books
    - World building and lore
    - Plot events and timeline
    - Your writing style preferences

    Args:
        series_id: Series ID
        request: Message and optional context focus

    Returns:
        Chico's response with assistant name and conversation ID
    """
    ensure_series_exists(series_id)

    service = get_chico_service()
    try:
        return await service.send_message(series_id, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{series_id}/history", response_model=ChicoConversation)
async def get_conversation_history(series_id: str):
    """
    Get Chico conversation history for a series.

    Returns the full conversation including all messages.
    """
    ensure_series_exists(series_id)

    service = get_chico_service()
    try:
        return await service.get_conversation(series_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{series_id}/history")
async def clear_conversation_history(series_id: str):
    """
    Clear Chico conversation history for a series.

    This resets the conversation - Chico will still know your series,
    but won't remember previous chat messages.
    """
    ensure_series_exists(series_id)

    service = get_chico_service()
    try:
        await service.clear_conversation(series_id)
        return {"message": "Conversation history cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Settings Endpoints
# =============================================================================

@router.get("/{series_id}/settings", response_model=ChicoSettings)
async def get_chico_settings(series_id: str):
    """
    Get Chico settings for a series.

    Returns assistant name, personality, and model preferences.
    """
    ensure_series_exists(series_id)

    service = get_chico_service()
    try:
        return await service.get_settings(series_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{series_id}/settings", response_model=ChicoSettings)
async def update_chico_settings(series_id: str, chico_settings: ChicoSettings):
    """
    Update Chico settings for a series.

    Configurable options:
    - assistant_name: What to call the assistant (default: "Chico")
    - personality: "helpful", "direct", or "enthusiastic"
    - model: LLM model override (null for default)
    - enabled: Whether Chico is enabled
    """
    ensure_series_exists(series_id)

    service = get_chico_service()
    try:
        await service.save_settings(series_id, chico_settings)
        return chico_settings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
