from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.models import Conversation as ConversationModel, Message as MessageModel
from app.db.session import get_session
from app.core.auth import verify_nextauth_jwt, get_effective_owner
from fastapi import Request
from app.config import get_settings
from app.core.memory_store import memory_store

router = APIRouter()


@router.get("/conversations")
async def get_conversations(http_request: Request) -> List[Dict]:
    """Get all conversations (most recent first)."""
    async with get_session() as session:  # type: AsyncSession
        owner = get_effective_owner(http_request)
        if not owner:
            # No owner derivable; return empty list to avoid cross-user leakage
            return []
        settings = get_settings()
        if settings.memory_mode:
            return memory_store.list_conversations(owner)
        else:
            stmt = (
                select(ConversationModel)
                .where(ConversationModel.owner_id == owner)
                .order_by(ConversationModel.updated_at.desc())
            )
            result = await session.exec(stmt)
            rows = result.all()
            return [row.model_dump() for row in rows]


@router.post("/conversations")
async def create_conversation(http_request: Request, title: str = Query("New Conversation", min_length=1, max_length=200)) -> Dict:
    """Create a new conversation."""
    async with get_session() as session:  # type: AsyncSession
        owner_id = get_effective_owner(http_request)
        if not owner_id:
            # If no owner can be resolved, reject to avoid shared/global guest pool
            raise HTTPException(status_code=400, detail="Missing owner context")
        settings = get_settings()
        if settings.memory_mode:
            return memory_store.create_conversation(owner_id, title)
        else:
            obj = ConversationModel(title=title, owner_id=owner_id)
            session.add(obj)
            await session.flush()
            await session.refresh(obj)
            return obj.model_dump()


@router.patch("/conversations/{conversation_id}")
async def rename_conversation(conversation_id: int, http_request: Request, title: str = Query(..., min_length=1, max_length=200)) -> Dict:
    """Rename a conversation."""
    async with get_session() as session:  # type: AsyncSession
        inst = await session.get(ConversationModel, conversation_id)
        if not inst:
            raise HTTPException(status_code=404, detail="Conversation not found")
        uid = get_effective_owner(http_request)
        if not uid or inst.owner_id != uid:
            raise HTTPException(status_code=403, detail="Forbidden")
        settings = get_settings()
        if settings.memory_mode:
            # Mirror behavior via memory store
            obj = memory_store.rename_conversation(uid, conversation_id, title)
            if not obj:
                raise HTTPException(status_code=404, detail="Conversation not found")
            return obj
        else:
            inst.title = title
            await session.flush()
            await session.refresh(inst)
            return inst.model_dump()


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int, http_request: Request) -> Dict[str, str]:
    """Delete a conversation by ID."""
    async with get_session() as session:  # type: AsyncSession
        inst = await session.get(ConversationModel, conversation_id)
        if not inst:
            raise HTTPException(status_code=404, detail="Conversation not found")
        uid = get_effective_owner(http_request)
        if not uid or inst.owner_id != uid:
            raise HTTPException(status_code=403, detail="Forbidden")
        settings = get_settings()
        if settings.memory_mode:
            ok = memory_store.delete_conversation(uid, conversation_id)
            if not ok:
                raise HTTPException(status_code=404, detail="Conversation not found")
            return {"status": "deleted", "id": str(conversation_id)}
        else:
            # Delete messages first (no relationship cascade defined)
            msg_stmt = select(MessageModel).where(MessageModel.conversation_id == conversation_id)
            res = await session.exec(msg_stmt)
            for m in res.all():
                await session.delete(m)
            await session.delete(inst)
            return {"status": "deleted", "id": str(conversation_id)}


@router.get("/conversations/{conversation_id}/messages")
async def list_messages(conversation_id: int, http_request: Request) -> List[Dict]:
    """List messages for a conversation (newest first)."""
    async with get_session() as session:  # type: AsyncSession
        # Validate conversation exists
        uid = get_effective_owner(http_request)
        if not uid:
            raise HTTPException(status_code=403, detail="Forbidden")
        settings = get_settings()
        if settings.memory_mode:
            msgs = memory_store.list_messages(uid, conversation_id)
            if msgs is None:
                raise HTTPException(status_code=404, detail="Conversation not found")
            return msgs
        else:
            conv = await session.get(ConversationModel, conversation_id)
            if not conv:
                raise HTTPException(status_code=404, detail="Conversation not found")
            if conv.owner_id != uid:
                raise HTTPException(status_code=403, detail="Forbidden")
            stmt = (
                select(MessageModel)
                .where(MessageModel.conversation_id == conversation_id)
                .order_by(desc(MessageModel.created_at))
            )
            result = await session.exec(stmt)
            rows = result.all()
            return [r.model_dump() for r in rows]


@router.post("/conversations/{conversation_id}/messages")
async def create_message(conversation_id: int, http_request: Request, role: str = Query(..., regex=r"^(user|assistant|system)$"), content: str = Query(...)) -> Dict:
    """Create a single message (helper endpoint)."""
    async with get_session() as session:  # type: AsyncSession
        uid = get_effective_owner(http_request)
        if not uid:
            raise HTTPException(status_code=403, detail="Forbidden")
        settings = get_settings()
        if settings.memory_mode:
            msg = memory_store.add_message(uid, conversation_id, role, content)
            if msg is None:
                raise HTTPException(status_code=404, detail="Conversation not found")
            return msg
        else:
            conv = await session.get(ConversationModel, conversation_id)
            if not conv:
                raise HTTPException(status_code=404, detail="Conversation not found")
            if conv.owner_id != uid:
                raise HTTPException(status_code=403, detail="Forbidden")
            msg = MessageModel(conversation_id=conversation_id, role=role, content=content)
            session.add(msg)
            # Touch conversation
            conv.updated_at = msg.created_at
            await session.flush()
            await session.refresh(msg)
            return msg.model_dump()
