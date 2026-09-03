"""
Pydantic schemas for AI-related request and response models.
"""

from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class AIModelChoice(str, Enum):
    auto = "auto"
    gemini_flash = "gemini_flash"
    gemini_flash_lite = "gemini_flash_lite"
    groq = "groq"


class AIRequest(BaseModel):
    model: AIModelChoice = AIModelChoice.auto
    force_refresh: bool = False


class AISummaryResponse(BaseModel):
    summary: Any = None
    is_cached: bool = False
    is_stale: bool = False


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    history: List[ChatMessage]
    page_context: Optional[dict] = None


class Citation(BaseModel):
    type: str
    path: str


class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation] = Field(default_factory=list)
