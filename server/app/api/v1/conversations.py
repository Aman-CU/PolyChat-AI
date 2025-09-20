from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.models import Conversation as ConversationModel
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


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int) -> Dict[str, str]:
    """Delete a conversation by ID."""
    async with get_session() as session:  # type: AsyncSession
        inst = await session.get(ConversationModel, conversation_id)
        if not inst:
            raise HTTPException(status_code=404, detail="Conversation not found")
        await session.delete(inst)
        return {"status": "deleted", "id": str(conversation_id)}
