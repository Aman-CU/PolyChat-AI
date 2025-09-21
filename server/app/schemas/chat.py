from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str = Field(..., pattern=r"^(user|assistant|system)$")
    content: str


class ChatRequest(BaseModel):
    conversationId: Optional[int | str] = None
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.7
    maxTokens: Optional[int] = Field(default=512, ge=1, alias="max_tokens")

    class Config:
        populate_by_name = True


class ModelInfo(BaseModel):
    id: str
    name: str
    context_length: int = 128000
