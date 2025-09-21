from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.models import Conversation as ConversationModel, Message as MessageModel
from app.db.session import get_session

router = APIRouter()


@router.get("/conversations")
async def get_conversations() -> List[Dict]:
    """Get all conversations (most recent first)."""
    async with get_session() as session:  # type: AsyncSession
        stmt = select(ConversationModel).order_by(ConversationModel.updated_at.desc())
        result = await session.exec(stmt)
        rows = result.all()
        return [row.model_dump() for row in rows]


@router.post("/conversations")
async def create_conversation(title: str = Query("New Conversation", min_length=1, max_length=200)) -> Dict:
    """Create a new conversation."""
    async with get_session() as session:  # type: AsyncSession
        obj = ConversationModel(title=title)
        session.add(obj)
        await session.flush()
        await session.refresh(obj)
        return obj.model_dump()


@router.patch("/conversations/{conversation_id}")
async def rename_conversation(conversation_id: int, title: str = Query(..., min_length=1, max_length=200)) -> Dict:
    """Rename a conversation."""
    async with get_session() as session:  # type: AsyncSession
        inst = await session.get(ConversationModel, conversation_id)
        if not inst:
            raise HTTPException(status_code=404, detail="Conversation not found")
        inst.title = title
        await session.flush()
        await session.refresh(inst)
        return inst.model_dump()


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int) -> Dict[str, str]:
    """Delete a conversation by ID."""
    async with get_session() as session:  # type: AsyncSession
        inst = await session.get(ConversationModel, conversation_id)
        if not inst:
            raise HTTPException(status_code=404, detail="Conversation not found")
        # Delete messages first (no relationship cascade defined)
        msg_stmt = select(MessageModel).where(MessageModel.conversation_id == conversation_id)
        res = await session.exec(msg_stmt)
        for m in res.all():
            await session.delete(m)
        await session.delete(inst)
        return {"status": "deleted", "id": str(conversation_id)}


@router.get("/conversations/{conversation_id}/messages")
async def list_messages(conversation_id: int) -> List[Dict]:
    """List messages for a conversation (newest first)."""
    async with get_session() as session:  # type: AsyncSession
        # Validate conversation exists
        conv = await session.get(ConversationModel, conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        stmt = (
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            .order_by(desc(MessageModel.created_at))
        )
        result = await session.exec(stmt)
        rows = result.all()
        return [r.model_dump() for r in rows]


@router.post("/conversations/{conversation_id}/messages")
async def create_message(conversation_id: int, role: str = Query(..., regex=r"^(user|assistant|system)$"), content: str = Query(...)) -> Dict:
    """Create a single message (helper endpoint)."""
    async with get_session() as session:  # type: AsyncSession
        conv = await session.get(ConversationModel, conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        msg = MessageModel(conversation_id=conversation_id, role=role, content=content)
        session.add(msg)
        # Touch conversation
        conv.updated_at = msg.created_at
        await session.flush()
        await session.refresh(msg)
        return msg.model_dump()
