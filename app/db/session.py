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

import urllib.parse

db_url = settings.DATABASE_URL
connect_args = {}

# asyncpg does not support the sslmode query parameter and will raise a TypeError.
# We strip it from the URL and pass it via connect_args.
if "asyncpg" in db_url:
    parsed = urllib.parse.urlparse(db_url)
    query = urllib.parse.parse_qs(parsed.query)
    if "sslmode" in query:
        sslmode = query["sslmode"][0]
        query.pop("sslmode", None)
        new_query = urllib.parse.urlencode(query, doseq=True)
        db_url = urllib.parse.urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment)
        )
        if sslmode in ("require", "verify-ca", "verify-full", "prefer"):
            connect_args["ssl"] = "require"
        elif sslmode == "disable":
            connect_args["ssl"] = False

# Create the async engine
engine = create_async_engine(
    db_url,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
    connect_args=connect_args,
)

# Session factory — creates new sessions, does NOT open a connection yet
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # WHY: Prevents lazy-load errors after commit in async
)
