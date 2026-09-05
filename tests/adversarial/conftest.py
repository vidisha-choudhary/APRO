"""Shared test fixtures for Phase 17 Adversarial Security test suite."""

import os
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import text

from apro.adversarial.executor import AdversarialAttackExecutor
from apro.evaluation.persistence import PostgreSQLEvaluationArtifactStore
from apro.persistence.database import get_async_engine, get_session_factory


@pytest_asyncio.fixture
async def attack_db_session_factory() -> AsyncGenerator[Any, None]:
    """Provide isolated session factory bound to apro_attack_db."""
    db_url = os.environ.get("POSTGRES_TEST_URL")
    if not db_url:
        pytest.fail("Missing required environment variable POSTGRES_TEST_URL")
    engine = get_async_engine(db_url)
    session_factory = get_session_factory(engine)

    try:
        async with session_factory() as session, session.begin():
            await session.execute(
                text("TRUNCATE TABLE evaluation_benchmark_reports CASCADE;")
            )
    except Exception as exc:
        await engine.dispose()
        pytest.fail(f"Attack database setup/cleanup failed (fail-fast): {exc}")

    yield session_factory
    await engine.dispose()


@pytest_asyncio.fixture
async def attack_eval_store(
    attack_db_session_factory: Any,
) -> AsyncGenerator[PostgreSQLEvaluationArtifactStore, None]:
    """Provide PostgreSQLEvaluationArtifactStore connected to apro_attack_db."""
    store = PostgreSQLEvaluationArtifactStore(session_factory=attack_db_session_factory)
    yield store


@pytest.fixture
def adversarial_executor(
    attack_eval_store: PostgreSQLEvaluationArtifactStore,
    attack_db_session_factory: Any,
) -> AdversarialAttackExecutor:
    """Provide initialized AdversarialAttackExecutor."""
    return AdversarialAttackExecutor(
        eval_store=attack_eval_store,
        session_factory=attack_db_session_factory,
    )
