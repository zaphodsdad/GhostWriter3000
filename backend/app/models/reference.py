"""Reference document models for context library."""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator
import re


# Document type options
DocType = Literal["style_reference", "published_book", "world_notes", "character_notes", "research", "other"]

# Scope options
ScopeType = Literal["series", "project"]


class ReferenceDocument(BaseModel):
    """Reference document for context injection in generation and chat."""

    id: str = Field(..., description="Unique document identifier (slug)")
    filename: str = Field(..., description="Original filename")
    title: str = Field(..., description="Document title", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="Brief description of content")

    # Categorization
    doc_type: DocType = Field("other", description="Type of reference document")

    # Usage flags - controls when this doc is included in context
    use_in_generation: bool = Field(True, description="Include in prose generation context")
    use_in_chat: bool = Field(True, description="Include in chat context")

    # Scope - where this document lives
    scope: ScopeType = Field("project", description="Whether this belongs to a series or project")
    scope_id: str = Field(..., description="Series ID or Project ID this belongs to")

    # Content metadata (full content stored in filesystem)
    content_preview: Optional[str] = Field(None, description="First 500 chars preview")
    word_count: int = Field(0, description="Document word count")
    char_count: int = Field(0, description="Character count")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', v):
            raise ValueError("ID must be a valid slug (lowercase alphanumeric with hyphens)")
        return v


class ReferenceCreate(BaseModel):
    """Model for uploading a reference document."""

    title: str = Field(..., min_length=1, max_length=200, description="Document title")
    description: Optional[str] = Field(None, description="Brief description")
    doc_type: DocType = Field("other", description="Type of reference document")
    use_in_generation: bool = Field(True, description="Include in prose generation")
    use_in_chat: bool = Field(True, description="Include in chat context")
    content: str = Field(..., min_length=1, description="Full document content")
    filename: Optional[str] = Field(None, description="Original filename (auto-generated if not provided)")


class ReferenceUpdate(BaseModel):
    """Model for updating reference document metadata."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    doc_type: Optional[DocType] = None
    use_in_generation: Optional[bool] = None
    use_in_chat: Optional[bool] = None
    content: Optional[str] = Field(None, description="Update content (optional)")


class ReferenceSummary(BaseModel):
    """Summary of a reference document for listing."""

    id: str
    title: str
    description: Optional[str] = None
    doc_type: DocType
    use_in_generation: bool
    use_in_chat: bool
    scope: ScopeType
    word_count: int
    content_preview: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ReferenceContent(BaseModel):
    """Full reference document with content."""

    id: str
    title: str
    description: Optional[str] = None
    doc_type: DocType
    use_in_generation: bool
    use_in_chat: bool
    scope: ScopeType
    scope_id: str
    content: str = Field(..., description="Full document content")
    word_count: int
    char_count: int
    created_at: datetime
    updated_at: datetime
