from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: list[ChatMessage]
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: Optional[int] = None
    stream: bool = False
    top_p: float = Field(default=1.0, ge=0, le=1)


class ChatChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class UsageInfo(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatChoice]
    usage: UsageInfo
    # Extension fields
    x_routing_strategy: Optional[str] = None
    x_provider: Optional[str] = None
    x_cost_usd: Optional[float] = None
    x_latency_ms: Optional[int] = None
