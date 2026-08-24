"""Razorpay webhook router implementation."""

import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status

from apro.config import settings
from apro.webhooks.verification import verify_razorpay_signature

logger = logging.getLogger("apro.webhooks.razorpay")

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/razorpay")
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(None),
    x_razorpay_event_id: str | None = Header(None),
) -> dict[str, Any]:
    """Handle incoming Razorpay webhook events.

    Verifies signature over raw request body, extracts webhook event ID, performs
    temporary in-memory duplicate detection, validates event payload, and extracts
    payment failure metadata.
    """
    # 1. Capture raw request body before parsing
    raw_body = await request.body()

    # 2. Extract signature and event ID headers
    signature = x_razorpay_signature or request.headers.get("X-Razorpay-Signature")
    event_id = x_razorpay_event_id or request.headers.get("X-Razorpay-Event-Id")

    # 3. Webhook secret retrieval and verification
    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
    if not verify_razorpay_signature(raw_body, signature, webhook_secret):
        logger.warning("Rejected webhook: invalid or missing signature header.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or missing webhook signature",
        )

    # 4. Capture event identifier header (strictly required for Phase 01)
    if not event_id:
        logger.warning("Rejected webhook: missing X-Razorpay-Event-Id header.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing event identifier header",
        )

    # 5. Temporary Phase 01 Test-Only Duplicate Detection
    if not hasattr(request.app.state, "processed_event_ids"):
        request.app.state.processed_event_ids = set()

    processed_ids: set[str] = request.app.state.processed_event_ids
    if event_id in processed_ids:
        logger.info(
            "Duplicate webhook delivery detected (TEMPORARY) for event ID: %s",
            event_id,
        )
        return {
            "status": "duplicate",
            "event_id": event_id,
            "classification": "DUPLICATE",
        }

    # 6. Parse JSON payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.warning("Rejected webhook: malformed JSON payload. %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON payload",
        ) from e

    # 7. Validate payload envelope
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload structure",
        )

    if payload.get("entity") != "event":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unexpected entity type in payload",
        )

    event_name = payload.get("event")
    if not event_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing event name in payload",
        )

    # 8. Check for target event type (payment.failed)
    if event_name != "payment.failed":
        logger.info("Ignored webhook event: unsupported event type %s", event_name)
        return {
            "status": "ignored",
            "reason": f"Unsupported event type: {event_name}",
        }

    # 9. Extract and validate payment entity details
    event_payload = payload.get("payload")
    if not isinstance(event_payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing payload details",
        )

    payment_data = event_payload.get("payment")
    if not isinstance(payment_data, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing payment details",
        )

    payment_entity = payment_data.get("entity")
    if not isinstance(payment_entity, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing payment entity details",
        )

    # 10. Extract Required Payment Metadata (fail if missing)
    payment_id = payment_entity.get("id")
    amount = payment_entity.get("amount")
    currency = payment_entity.get("currency")
    payment_status = payment_entity.get("status")
    method = payment_entity.get("method")
    created_at = payment_entity.get("created_at")

    if not payment_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing payment identifier (id)",
        )
    if amount is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing payment amount",
        )
    if not currency:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing payment currency",
        )
    if not payment_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing payment status",
        )
    if not method:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing payment method",
        )
    if created_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing payment creation timestamp (created_at)",
        )

    # Check status consistency
    if payment_status != "failed":
        logger.error(
            "State mismatch: event is payment.failed but payment status is %s",
            payment_status,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Inconsistent payment status: {payment_status}",
        )

    # Add to processed event IDs set (TEMPORARY PHASE 01 TEST-ONLY DETECTOR)
    processed_ids.add(event_id)

    # 11. Extract Optional Payment Metadata (do not fail if missing)
    order_id = payment_entity.get("order_id")
    error_code = payment_entity.get("error_code")
    error_description = payment_entity.get("error_description")
    error_reason = payment_entity.get("error_reason")
    error_source = payment_entity.get("error_source")
    error_step = payment_entity.get("error_step")

    metadata = {
        "payment_id": payment_id,
        "amount": amount,
        "currency": currency,
        "status": payment_status,
        "method": method,
        "order_id": order_id,
        "created_at": created_at,
        "error_code": error_code,
        "error_description": error_description,
        "error_reason": error_reason,
        "error_source": error_source,
        "error_step": error_step,
    }

    logger.info(
        "Successfully validated payment.failed event %s for payment %s [NEW]",
        event_id,
        payment_id,
    )

    return {
        "status": "accepted",
        "event_id": event_id,
        "event_type": "payment.failed",
        "payment_id": payment_id,
        "classification": "NEW",
        "extracted_metadata": metadata,
    }
