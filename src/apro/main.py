"""APRO application entry point."""

import logging

from fastapi import FastAPI

from apro.config import settings

# Initialize logging using the configured LOG_LEVEL
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger("apro.main")
logger.info("Starting APRO backend service...")

# Initialize FastAPI application
app = FastAPI(
    title="APRO — Adaptive Payment Recovery Orchestrator",
    description="APRO backend service engineering foundation",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Basic health check endpoint indicating service liveness."""
    logger.debug("Health check requested")
    return {
        "status": "ok",
        "service": "apro",
    }
