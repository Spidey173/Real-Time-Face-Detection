"""
Async database engine and session factory.

WHY async: We don't want DB writes to block the frame-processing loop.
asyncpg is the fastest PostgreSQL driver for Python.

WHY SessionLocal pattern: Each request gets its own session via FastAPI's
Depends(). No shared mutable state, no threading bugs.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import get_settings

settings = get_settings()

# Create the async engine
# pool_size=5: Default connection pool. Enough for moderate load.
# echo=False: Set to True during debugging to see generated SQL.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
)

# Session factory — creates new sessions, does NOT open a connection yet
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # WHY: Prevents lazy-load errors after commit in async
)
