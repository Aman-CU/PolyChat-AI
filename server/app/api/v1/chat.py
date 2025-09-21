from fastapi import APIRouter, HTTPException
import logging
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest
from app.providers.router import router as provider_router
from fastapi import Request
from app.core.ratelimit import enforce_rate_limit
from app.core.auth import verify_nextauth_jwt, get_effective_owner
from app.db.session import get_session
from sqlmodel.ext.asyncio.session import AsyncSession
from app.db.models import Conversation as ConversationModel, Message as MessageModel
from sqlmodel import select
import json

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

        # Create conversation if needed and persist the incoming user message
        async with get_session() as session:  # type: AsyncSession
            conversation_id = request.conversationId
            if conversation_id is None:
                # Title from last user message snippet
                last_user = next((m for m in reversed(request.messages) if m.role == "user"), None)
                title = (last_user.content[:40] + "...") if last_user and last_user.content else "New Conversation"
                # Associate new conversation with effective owner (logged-in user or per-browser guest)
                owner_id = get_effective_owner(http_request)
                conv = ConversationModel(title=title, owner_id=owner_id)
                session.add(conv)
                await session.flush()
                await session.refresh(conv)
                conversation_id = conv.id

            # Persist the latest user message in the payload (if present)
            if request.messages:
                last = request.messages[-1]
                if last.role == "user":
                    umsg = MessageModel(conversation_id=conversation_id, role="user", content=last.content)
                    session.add(umsg)
                    # Touch conversation timestamp
                    conv_ref = await session.get(ConversationModel, conversation_id)
                    if conv_ref:
                        conv_ref.updated_at = umsg.created_at

        async def generator():
            assistant_buffer = []
            # Emit meta event with conversationId so the client can reuse it
            try:
                yield "data: " + json.dumps({"meta": {"conversationId": conversation_id}}) + "\n\n"
            except Exception:
                pass
            # Stream from provider and mirror to client while buffering assistant content
            async for chunk in provider.stream(request):
                # chunk is an SSE line like 'data: {json}\n\n' or similar
                try:
                    line = chunk.strip()
                    if line.startswith("data: "):
                        payload = line[len("data: "):]
                        if payload == "{\"done\": true}":
                            # On done, persist assistant message if any
                            text = "".join(assistant_buffer).strip()
                            if text:
                                async with get_session() as session:  # type: AsyncSession
                                    amsg = MessageModel(conversation_id=conversation_id, role="assistant", content=text)
                                    session.add(amsg)
                                    conv_ref = await session.get(ConversationModel, conversation_id)
                                    if conv_ref:
                                        conv_ref.updated_at = amsg.created_at
                            # forward done
                            yield chunk
                            continue
                        # attempt to parse and capture content
                        obj = json.loads(payload)
                        content = obj.get("content")
                        # Filter out model banner lines so they are not forwarded nor persisted
                        if isinstance(content, str) and content.startswith("[model:"):
                            # Skip both buffering and forwarding this particular chunk
                            continue
                        if isinstance(content, str):
                            assistant_buffer.append(content)
                except Exception:
                    # ignore parsing issues, just forward
                    pass
                # forward to client unchanged
                yield chunk

        return StreamingResponse(
            generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    except Exception as e:
        logger.exception("/chat/stream error model=%s: %s", request.model, e)
        raise HTTPException(status_code=500, detail=str(e))
