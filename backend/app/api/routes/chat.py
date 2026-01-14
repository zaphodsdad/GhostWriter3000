"""Chat API endpoints."""

from fastapi import APIRouter, HTTPException
from typing import List, Optional

from app.models.chat import (
    ChatScope, ChatRequest, ChatResponse, Conversation, ConversationSummary
)
from app.services.chat_service import get_chat_service
from app.config import settings

router = APIRouter()


def ensure_project_exists(project_id: str):
    """Check that project exists, raise 404 if not."""
    if not settings.project_dir(project_id).exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")


@router.get("/", response_model=List[dict])
async def list_conversations(project_id: str):
    """
    List all conversations in a project.

    Args:
        project_id: Project ID

    Returns:
        List of conversation summaries
    """
    ensure_project_exists(project_id)

    try:
        chat_service = get_chat_service()
        return await chat_service.list_conversations(project_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{scope}", response_model=Conversation)
async def get_project_conversation(project_id: str, scope: str):
    """
    Get or create project-scoped conversation.

    Args:
        project_id: Project ID
        scope: Must be "project"

    Returns:
        Conversation
    """
    ensure_project_exists(project_id)

    if scope != "project":
        raise HTTPException(status_code=400, detail="Use /{scope}/{scope_id} for scene/chapter conversations")

    try:
        chat_service = get_chat_service()
        return await chat_service.get_or_create_conversation(
            project_id, ChatScope.PROJECT, None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{scope}/{scope_id}", response_model=Conversation)
async def get_conversation(project_id: str, scope: str, scope_id: str):
    """
    Get or create a conversation for a specific scope.

    Args:
        project_id: Project ID
        scope: "scene" or "chapter"
        scope_id: ID of the scene or chapter

    Returns:
        Conversation
    """
    ensure_project_exists(project_id)

    try:
        chat_scope = ChatScope(scope)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid scope: {scope}. Use 'scene', 'chapter', or 'project'")

    try:
        chat_service = get_chat_service()
        return await chat_service.get_or_create_conversation(
            project_id, chat_scope, scope_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{scope}/message", response_model=ChatResponse)
async def send_project_message(project_id: str, scope: str, request: ChatRequest):
    """
    Send a message in project-scoped conversation.

    Args:
        project_id: Project ID
        scope: Must be "project"
        request: Chat request with message

    Returns:
        AI response with any edits made
    """
    ensure_project_exists(project_id)

    if scope != "project":
        raise HTTPException(status_code=400, detail="Use /{scope}/{scope_id}/message for scene/chapter conversations")

    try:
        chat_service = get_chat_service()
        return await chat_service.send_message(
            project_id, ChatScope.PROJECT, None, request
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{scope}/{scope_id}/message", response_model=ChatResponse)
async def send_message(project_id: str, scope: str, scope_id: str, request: ChatRequest):
    """
    Send a message in a conversation.

    Args:
        project_id: Project ID
        scope: "scene" or "chapter"
        scope_id: ID of the scene or chapter
        request: Chat request with message

    Returns:
        AI response with any edits made
    """
    ensure_project_exists(project_id)

    try:
        chat_scope = ChatScope(scope)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid scope: {scope}. Use 'scene', 'chapter', or 'project'")

    try:
        chat_service = get_chat_service()
        return await chat_service.send_message(
            project_id, chat_scope, scope_id, request
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{scope}")
async def clear_project_conversation(project_id: str, scope: str):
    """
    Clear project-scoped conversation history.

    Args:
        project_id: Project ID
        scope: Must be "project"

    Returns:
        Success message
    """
    ensure_project_exists(project_id)

    if scope != "project":
        raise HTTPException(status_code=400, detail="Use /{scope}/{scope_id} for scene/chapter conversations")

    try:
        chat_service = get_chat_service()
        await chat_service.clear_conversation(project_id, ChatScope.PROJECT, None)
        return {"message": "Conversation cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{scope}/{scope_id}")
async def clear_conversation(project_id: str, scope: str, scope_id: str):
    """
    Clear conversation history.

    Args:
        project_id: Project ID
        scope: "scene" or "chapter"
        scope_id: ID of the scene or chapter

    Returns:
        Success message
    """
    ensure_project_exists(project_id)

    try:
        chat_scope = ChatScope(scope)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid scope: {scope}")

    try:
        chat_service = get_chat_service()
        await chat_service.clear_conversation(project_id, chat_scope, scope_id)
        return {"message": "Conversation cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
