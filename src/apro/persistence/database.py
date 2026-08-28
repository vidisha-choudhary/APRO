"""SQLAlchemy async database engine and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from apro.config import settings


def get_async_engine(db_url: str | None = None) -> AsyncEngine:
    """Create and return an AsyncEngine instance.

    Raises:
        ValueError: If db_url or settings.DATABASE_URL is missing/unconfigured.
    """
    url = db_url or settings.DATABASE_URL
    if not url:
        raise ValueError("DATABASE_URL is not configured. Please set DATABASE_URL.")

    # Handle standard postgresql:// vs postgresql+asyncpg://
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("sqlite://"):
        url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)

    connect_args = {}
    if "sqlite" in url:
        connect_args["check_same_thread"] = False

    return create_async_engine(
        url,
        echo=False,
        future=True,
        connect_args=connect_args,
    )


def get_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create and return an async_sessionmaker factory."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_async_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async with session_factory() as session:
        yield session
