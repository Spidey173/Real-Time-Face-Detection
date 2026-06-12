"""
FastAPI dependency injection.

WHY this file exists: Keeps route files clean. Routes call Depends(get_db)
and get a session — they don't need to know how sessions are created.

This is FastAPI's recommended pattern:
https://fastapi.tiangolo.com/tutorial/dependencies/
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yields a database session for a single request, then closes it.

    WHY generator + try/finally:
    - The session is created when the request starts.
    - It's automatically closed when the request ends (even on errors).
    - No leaked connections, ever.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
