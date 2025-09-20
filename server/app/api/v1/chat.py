from fastapi import APIRouter, HTTPException
import logging
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest
from app.providers.router import router as provider_router
from fastapi import Request
from app.core.ratelimit import enforce_rate_limit

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/chat/stream")
async def stream_chat(request: ChatRequest, http_request: Request):
    """Stream chat completion via the resolved provider."""
    try:
        enforce_rate_limit(http_request, limit=30, window_seconds=60)
        logger.info("/chat/stream start model=%s messages=%d", request.model, len(request.messages))
        provider = provider_router.get_provider(request.model)
        logger.info("Resolved provider=%s for model=%s", provider.__class__.__name__, request.model)
        return StreamingResponse(
            provider.stream(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    except Exception as e:
        logger.exception("/chat/stream error model=%s: %s", request.model, e)
        raise HTTPException(status_code=500, detail=str(e))
