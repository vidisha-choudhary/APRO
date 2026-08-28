"""Async Unit of Work pattern implementation for atomic multi-repository operations."""

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apro.persistence.repositories import (
    ActionEvaluationRepository,
    AuditEventRepository,
    CustomerRepository,
    DecisionRepository,
    DiagnosisRepository,
    ExecutionRepository,
    OutcomeRepository,
    PaymentEventRepository,
    PaymentRepository,
    PolicyDecisionRepository,
    RawEventRepository,
    RecoveryActionRepository,
    RecoveryCaseRepository,
)


class UnitOfWork:
    """Unit of Work manager for database transactions and repository lifecycles."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self.session = self._session_factory()
        self.customers = CustomerRepository(self.session)
        self.payments = PaymentRepository(self.session)
        self.raw_events = RawEventRepository(self.session)
        self.payment_events = PaymentEventRepository(self.session)
        self.recovery_cases = RecoveryCaseRepository(self.session)
        self.recovery_actions = RecoveryActionRepository(self.session)
        self.diagnoses = DiagnosisRepository(self.session)
        self.action_evaluations = ActionEvaluationRepository(self.session)
        self.decisions = DecisionRepository(self.session)
        self.policy_decisions = PolicyDecisionRepository(self.session)
        self.executions = ExecutionRepository(self.session)
        self.outcomes = OutcomeRepository(self.session)
        self.audit_events = AuditEventRepository(self.session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.session is not None:
            if exc_type is not None:
                await self.session.rollback()
            await self.session.close()

    async def commit(self) -> None:
        """Explicitly commit the current database transaction."""
        if self.session is None:
            raise RuntimeError("Cannot commit outside an active UnitOfWork context.")
        await self.session.commit()

    async def rollback(self) -> None:
        """Explicitly rollback the current database transaction."""
        if self.session is None:
            raise RuntimeError("Cannot rollback outside an active UnitOfWork context.")
        await self.session.rollback()
