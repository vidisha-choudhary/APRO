"""Canonical Event Pipeline coordinator for APRO Phase 3."""

import json
import logging
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apro.domain.enums import PaymentStatus
from apro.domain.exceptions import (
    CapturedPaymentRecoveryError,
    InvalidStateTransitionError,
)
from apro.domain.state_machines import transition_payment
from apro.events.exceptions import (
    InvalidSignatureError,
    MalformedPayloadError,
)
from apro.events.razorpay_adapter import RazorpayAdapter
from apro.persistence.unit_of_work import UnitOfWork
from apro.recovery.orchestrator import RecoveryCaseOrchestrator
from apro.webhooks.verification import verify_razorpay_signature

logger = logging.getLogger("apro.events.pipeline")


def is_provider_event_uniqueness_error(exc: IntegrityError) -> bool:
    """Check if IntegrityError was caused by provider event deduplication constraint.

    Strictly inspects constraint identity to avoid misclassifying errors.
    """
    orig_text = str(getattr(exc, "orig", exc)).lower()
    msg_text = str(exc).lower()
    combined = f"{orig_text} {msg_text}"

    # PostgreSQL exact unique constraint identity
    if "uq_raw_events_provider_event_id" in combined:
        return True

    # SQLite exact unique constraint failure identity
    return (
        "unique constraint failed" in combined
        and "raw_events.provider" in combined
        and "raw_events.provider_event_id" in combined
    )


class PipelineResult(BaseModel):
    """Result of processing a webhook through the canonical event pipeline."""

    status: str  # "accepted", "duplicate", "ignored"
    event_id: str
    classification: str
    # "NEW", "DUPLICATE", "UNSUPPORTED", "STALE", "UNRESOLVED_PAYMENT"
    event_type: str | None = None
    payment_id: str | None = None
    reason: str | None = None


class EventPipeline:
    """Coordinates trusted webhook verification, deduplication, and persistence."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._orchestrator = RecoveryCaseOrchestrator()

    async def process_webhook(
        self,
        raw_body: bytes,
        signature: str | None,
        event_id: str | None,
        webhook_secret: str | None,
        received_at: datetime | None = None,
    ) -> PipelineResult:
        """Process an incoming webhook request through the canonical pipeline."""
        now = received_at or datetime.now(UTC)

        # 1. Signature Verification
        if not verify_razorpay_signature(raw_body, signature, webhook_secret):
            logger.warning("Rejected webhook: invalid signature")
            raise InvalidSignatureError("Invalid or missing webhook signature")

        # 2. Event Identifier Verification
        if not event_id:
            logger.warning("Rejected webhook: missing X-Razorpay-Event-Id header")
            raise MalformedPayloadError("Missing event identifier header")

        # 3. JSON Parsing
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception as e:
            logger.warning("Rejected webhook: malformed JSON payload")
            raise MalformedPayloadError("Malformed JSON payload") from e

        # 4. Envelope Validation
        if not isinstance(payload, dict):
            raise MalformedPayloadError("Invalid payload structure")

        if payload.get("entity") != "event":
            raise MalformedPayloadError("Unexpected entity type in payload")

        event_name = payload.get("event")
        if not event_name or not isinstance(event_name, str):
            raise MalformedPayloadError("Missing event name in payload")

        # 5. Unit of Work Transaction Boundary
        async with UnitOfWork(self._session_factory) as uow:
            # Deduplication Check: Check existing raw event
            existing_raw = await uow.raw_events.find_by_provider_event_id(
                "razorpay", event_id
            )
            if existing_raw is not None:
                await uow.rollback()
                logger.info(
                    "Duplicate provider event detected for event_id: %s", event_id
                )
                return PipelineResult(
                    status="duplicate",
                    event_id=event_id,
                    classification="DUPLICATE",
                )

            raw_event_id = str(uuid.uuid4())
            try:
                await uow.raw_events.save(
                    raw_event_id=raw_event_id,
                    provider="razorpay",
                    provider_event_id=event_id,
                    event_type=event_name,
                    received_at=now,
                    raw_payload=payload,
                )
                await uow.flush()
            except IntegrityError as exc:
                await uow.rollback()
                if is_provider_event_uniqueness_error(exc):
                    logger.info(
                        "Concurrent duplicate event detected for event_id: %s",
                        event_id,
                    )
                    return PipelineResult(
                        status="duplicate",
                        event_id=event_id,
                        classification="DUPLICATE",
                    )
                logger.error(
                    "Unexpected database integrity failure during raw event insert: %s",
                    exc,
                )
                raise

            # Check supported event type
            if not RazorpayAdapter.is_supported_event(event_name):
                await uow.commit()
                logger.info("Ignored unsupported event type: %s", event_name)
                return PipelineResult(
                    status="ignored",
                    event_id=event_id,
                    classification="UNSUPPORTED",
                    reason=f"Unsupported event type: {event_name}",
                )

            # Validate payment entity structure
            try:
                payment_entity = RazorpayAdapter.validate_payment_entity(
                    payload, event_name
                )
            except MalformedPayloadError:
                await uow.rollback()
                raise

            # Provider payment identity resolution (SELECT ... FOR UPDATE row lock)
            provider_payment_id = str(payment_entity["id"])
            existing_payment = await uow.payments.find_by_provider_payment_id(
                "razorpay", provider_payment_id, for_update=True
            )

            if existing_payment is None:
                await uow.commit()
                logger.info(
                    "Unresolved provider payment ID: %s for event %s",
                    provider_payment_id,
                    event_id,
                )
                return PipelineResult(
                    status="accepted",
                    event_id=event_id,
                    classification="UNRESOLVED_PAYMENT",
                    event_type=event_name,
                    reason=f"Unresolved provider payment ID: {provider_payment_id}",
                )

            internal_payment_id = existing_payment.payment_id

            # Construct Canonical Event
            canonical_event = RazorpayAdapter.to_canonical_event(
                payload=payload,
                internal_payment_id=internal_payment_id,
                raw_event_id=raw_event_id,
                received_at=now,
            )

            # Query historical event knowledge for out-of-order timestamp check
            latest_event = await uow.payment_events.find_latest_by_payment_id(
                internal_payment_id
            )

            # Unconditionally persist canonical PaymentEvent record in history
            await uow.payment_events.append(canonical_event)

            # Payment State Application
            target_status = canonical_event.status
            current_status = existing_payment.status
            classification = "NEW"

            if (
                current_status == PaymentStatus.CAPTURED
                and target_status != PaymentStatus.CAPTURED
            ):
                # Stale event attempting to regress CAPTURED payment
                classification = "STALE"
                logger.info(
                    "Stale event %s ignored for CAPTURED payment %s",
                    event_name,
                    internal_payment_id,
                )
            elif (
                latest_event is not None
                and canonical_event.event_timestamp < latest_event.event_timestamp
            ):
                # Out-of-order timestamp: event occurred earlier than latest event
                classification = "STALE"
                logger.info(
                    "Stale event by timestamp (%s < %s) ignored for payment %s",
                    canonical_event.event_timestamp,
                    latest_event.event_timestamp,
                    internal_payment_id,
                )
            # Effective Payment resolution post-transition attempt
            effective_payment = existing_payment
            if classification != "STALE":
                try:
                    updated_payment = transition_payment(
                        existing_payment,
                        target_status,
                        now=canonical_event.event_timestamp,
                    )
                    await uow.payments.update_status_conditional(
                        updated_payment, expected_status=current_status
                    )
                    effective_payment = updated_payment
                except (InvalidStateTransitionError, CapturedPaymentRecoveryError):
                    classification = "STALE"
                    logger.info(
                        "Invalid transition %s -> %s for payment %s treated as STALE",
                        current_status,
                        target_status,
                        internal_payment_id,
                    )

            # Phase 4 Recovery Case Orchestration (Atomic UOW boundary)
            await self._orchestrator.handle_payment_event(
                uow, canonical_event, effective_payment
            )

            await uow.commit()

            return PipelineResult(
                status="accepted",
                event_id=event_id,
                classification=classification,
                event_type=event_name,
                payment_id=internal_payment_id,
            )
