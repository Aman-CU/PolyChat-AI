from __future__ import annotations
from typing import Protocol, AsyncIterator, List
from app.schemas.chat import ChatRequest, ModelInfo


class ChatProvider(Protocol):
    id: str

    async def list_models(self) -> List[ModelInfo]:
        ...

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        """Yield SSE 'data: {...}\n\n' strings."""
        ...
