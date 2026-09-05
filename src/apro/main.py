"""APRO application entry point."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apro.config import settings
from apro.dashboard import dashboard_router
from apro.persistence.database import get_async_engine, get_session_factory
from apro.webhooks.razorpay import router as razorpay_router

# Initialize logging using the configured LOG_LEVEL
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger("apro.main")
logger.info("Starting APRO backend service...")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown database connections."""
    engine = None
    if settings.DATABASE_URL:
        # DATABASE_URL is configured: database initialization must succeed.
        # Do not suppress exceptions; let startup fail cleanly if DB init fails.
        engine = get_async_engine()
        session_factory = get_session_factory(engine)
        app.state.engine = engine
        app.state.session_factory = session_factory
        logger.info("Attached database session factory to app.state.")

    yield

    if engine is not None:
        logger.info("Disposing database engine on application shutdown.")
        await engine.dispose()


# Initialize FastAPI application
app = FastAPI(
    title="APRO — Adaptive Payment Recovery Orchestrator",
    description="APRO backend service engineering foundation",
    version="0.1.0",
    lifespan=lifespan,
)

# Scoped CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

# Include application routers
app.include_router(razorpay_router)
app.include_router(dashboard_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Basic health check endpoint indicating service liveness."""
    logger.debug("Health check requested")
    return {
        "status": "ok",
        "service": "apro",
    }
