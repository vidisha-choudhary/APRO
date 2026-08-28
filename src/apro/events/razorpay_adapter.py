"""Razorpay adapter for normalizing payloads into PaymentEvent objects."""

import uuid
from datetime import UTC, datetime
from typing import Any

from apro.domain.enums import PaymentStatus
from apro.domain.models import PaymentEvent
from apro.events.exceptions import MalformedPayloadError

SUPPORTED_RAZORPAY_EVENTS = {
    "payment.failed": PaymentStatus.FAILED,
    "payment.authorized": PaymentStatus.AUTHORIZED,
    "payment.captured": PaymentStatus.CAPTURED,
}


class RazorpayAdapter:
    """Normalizes Razorpay nested payloads into PaymentEvent objects."""

    @staticmethod
    def is_supported_event(event_name: str) -> bool:
        """Check if Razorpay event type is supported for canonical processing."""
        return event_name in SUPPORTED_RAZORPAY_EVENTS

    @staticmethod
    def validate_payment_entity(
        payload: dict[str, Any], event_name: str
    ) -> dict[str, Any]:
        """Validate structure of payment entity within Razorpay payload."""
        event_payload = payload.get("payload")
        if not isinstance(event_payload, dict):
            raise MalformedPayloadError("Missing payload details")

        payment_data = event_payload.get("payment")
        if not isinstance(payment_data, dict):
            raise MalformedPayloadError("Missing payment details")

        payment_entity = payment_data.get("entity")
        if not isinstance(payment_entity, dict):
            raise MalformedPayloadError("Missing payment entity details")

        # Validate required fields
        provider_payment_id = payment_entity.get("id")
        amount = payment_entity.get("amount")
        currency = payment_entity.get("currency")
        status_str = payment_entity.get("status")
        method = payment_entity.get("method")
        created_at = payment_entity.get("created_at")

        if not provider_payment_id:
            raise MalformedPayloadError("Missing payment identifier (id)")
        if amount is None or not isinstance(amount, int):
            raise MalformedPayloadError("Missing or invalid payment amount")
        if not currency or not isinstance(currency, str):
            raise MalformedPayloadError("Missing or invalid payment currency")
        if not status_str or not isinstance(status_str, str):
            raise MalformedPayloadError("Missing or invalid payment status")
        if not method or not isinstance(method, str):
            raise MalformedPayloadError("Missing or invalid payment method")
        if created_at is None:
            raise MalformedPayloadError(
                "Missing payment creation timestamp (created_at)"
            )

        expected_status = SUPPORTED_RAZORPAY_EVENTS.get(event_name)
        if expected_status is not None:
            actual_status = payment_status_from_string(status_str)
            if actual_status != expected_status:
                msg = (
                    f"Inconsistent payment status: event type {event_name} "
                    f"contradicts payment status {status_str}"
                )
                raise MalformedPayloadError(msg)

        return payment_entity

    @classmethod
    def to_canonical_event(
        cls,
        payload: dict[str, Any],
        internal_payment_id: str,
        raw_event_id: str,
        received_at: datetime,
    ) -> PaymentEvent:
        """Convert a validated Razorpay payload into a PaymentEvent model."""
        event_name = str(payload.get("event"))
        if not cls.is_supported_event(event_name):
            msg = f"Event type {event_name} is not a supported canonical event"
            raise MalformedPayloadError(msg)

        payment_entity = cls.validate_payment_entity(payload, event_name)

        # Provider event created_at timestamp (top-level created_at is source of truth)
        top_created_at = payload.get("created_at")
        if top_created_at is None:
            raise MalformedPayloadError(
                "Missing required provider event timestamp (created_at)"
            )

        if isinstance(top_created_at, (int, float)):
            try:
                event_timestamp = datetime.fromtimestamp(top_created_at, tz=UTC)
            except Exception as e:
                raise MalformedPayloadError(
                    "Invalid provider event timestamp (created_at)"
                ) from e
        elif isinstance(top_created_at, datetime):
            event_timestamp = top_created_at
        else:
            raise MalformedPayloadError(
                "Invalid provider event timestamp format (created_at)"
            )

        payment_status = SUPPORTED_RAZORPAY_EVENTS[event_name]

        return PaymentEvent(
            event_id=str(uuid.uuid4()),
            provider="razorpay",
            event_type=event_name,
            payment_id=internal_payment_id,
            order_id=payment_entity.get("order_id"),
            amount=int(payment_entity["amount"]),
            currency=str(payment_entity["currency"]),
            method=str(payment_entity["method"]),
            status=payment_status,
            failure_code=payment_entity.get("error_code"),
            failure_source=payment_entity.get("error_source"),
            failure_step=payment_entity.get("error_step"),
            failure_reason=payment_entity.get("error_reason"),
            failure_description=payment_entity.get("error_description"),
            event_timestamp=event_timestamp,
            received_at=received_at,
            raw_payload_reference=raw_event_id,
        )


def payment_status_from_string(status_str: str) -> PaymentStatus:
    """Map string status to PaymentStatus enum."""
    mapping = {
        "failed": PaymentStatus.FAILED,
        "authorized": PaymentStatus.AUTHORIZED,
        "captured": PaymentStatus.CAPTURED,
        "created": PaymentStatus.PENDING,
    }
    if status_str in mapping:
        return mapping[status_str]
    msg = f"Unsupported or unknown payment status string: {status_str}"
    raise MalformedPayloadError(msg)
