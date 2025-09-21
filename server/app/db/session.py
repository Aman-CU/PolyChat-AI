from __future__ import annotations
from contextlib import asynccontextmanager
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./polychat.db")

engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False, autocommit=False
)


async def _migrate_sqlite_owner_id() -> None:
    """Add missing columns to existing SQLite tables (non-destructive)."""
    # Only for SQLite
    if not str(engine.url).startswith("sqlite+"):
        return
    async with engine.begin() as conn:
        # Ensure conversation.owner_id exists
        try:
            result = await conn.exec_driver_sql("PRAGMA table_info(conversation)")
            cols = [row[1] for row in result.fetchall()]
            if "owner_id" not in cols:
                await conn.exec_driver_sql("ALTER TABLE conversation ADD COLUMN owner_id VARCHAR")
        except Exception:
            # Best effort; ignore if table doesn't exist yet
            pass


async def init_db() -> None:
    # Run lightweight migrations first, then ensure tables exist
    await _migrate_sqlite_owner_id()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


@asynccontextmanager
async def get_session():
    session: AsyncSession = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
