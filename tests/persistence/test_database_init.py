"""Integration tests for database initialization and Alembic migrations."""

import os
from unittest.mock import patch

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

from apro.config import settings
from apro.persistence.database import get_async_engine


def test_missing_database_url_raises_error() -> None:
    """Rework #3: Missing/unconfigured DATABASE_URL raises clear ValueError."""
    with (
        patch.object(settings, "DATABASE_URL", None),
        pytest.raises(ValueError, match="DATABASE_URL is not configured"),
    ):
        get_async_engine(db_url=None)


def test_alembic_migration_upgrade_head(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Rework #5: Test fresh database initialization via Alembic upgrade('head')."""
    db_file = tmp_path / "test_migration.db"
    test_db_url = os.getenv("POSTGRES_TEST_URL", f"sqlite:///{db_file}")

    # Run Alembic migration command
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)

    # Execute upgrade head
    command.upgrade(alembic_cfg, "head")

    sync_db_url = test_db_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    engine = create_engine(sync_db_url, echo=False)
    with engine.connect() as conn:
        from sqlalchemy import inspect

        inspector = inspect(conn)
        tables = set(inspector.get_table_names())
        expected_tables = {
            "customers",
            "payments",
            "raw_events",
            "payment_events",
            "recovery_cases",
            "recovery_actions",
            "diagnoses",
            "action_evaluations",
            "decisions",
            "policy_decisions",
            "executions",
            "outcomes",
            "audit_events",
            "alembic_version",
        }
        assert expected_tables.issubset(tables)

    engine.dispose()
