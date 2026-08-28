"""Razorpay webhook router implementation."""

import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status

from apro.config import settings
from apro.events.exceptions import InvalidSignatureError, MalformedPayloadError
from apro.events.pipeline import EventPipeline
from apro.events.razorpay_adapter import RazorpayAdapter
from apro.webhooks.verification import verify_razorpay_signature

logger = logging.getLogger("apro.webhooks.razorpay")

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/razorpay")
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(None),
    x_razorpay_event_id: str | None = Header(None),
) -> dict[str, Any]:
    """Handle incoming Razorpay webhook events via Phase 3 Canonical Event Pipeline."""
    raw_body = await request.body()
    signature = x_razorpay_signature or request.headers.get("X-Razorpay-Signature")
    event_id = x_razorpay_event_id or request.headers.get("X-Razorpay-Event-Id")
    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET

    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is not None:
        pipeline = EventPipeline(session_factory)
        try:
            result = await pipeline.process_webhook(
                raw_body=raw_body,
                signature=signature,
                event_id=event_id,
                webhook_secret=webhook_secret,
            )
            return result.model_dump(exclude_none=True)
        except InvalidSignatureError as e:
            logger.warning("Rejected webhook: invalid signature header. %s", e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or missing webhook signature",
            ) from e
        except MalformedPayloadError as e:
            logger.warning("Rejected webhook: malformed payload. %s", e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e

    # Fallback path if session_factory is unavailable (lightweight unit test client)
    if settings.DATABASE_URL:
        logger.error("DATABASE_URL configured but session_factory missing on app.state")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database service unavailable: silent fallback forbidden",
        )

    if not verify_razorpay_signature(raw_body, signature, webhook_secret):
        logger.warning("Rejected webhook: invalid or missing signature header.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or missing webhook signature",
        )
    if not event_id:
        logger.warning("Rejected webhook: missing X-Razorpay-Event-Id header.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing event identifier header",
        )

    if not hasattr(request.app.state, "processed_event_ids"):
        request.app.state.processed_event_ids = set()

    processed_ids: set[str] = request.app.state.processed_event_ids
    if event_id in processed_ids:
        return {
            "status": "duplicate",
            "event_id": event_id,
            "classification": "DUPLICATE",
        }

    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON payload",
        ) from e

    if not isinstance(payload, dict) or payload.get("entity") != "event":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload structure",
        )

    event_name = payload.get("event")
    if not event_name or not isinstance(event_name, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing event name in payload",
        )

    if not RazorpayAdapter.is_supported_event(event_name):
        return {
            "status": "ignored",
            "reason": f"Unsupported event type: {event_name}",
        }

    try:
        payment_entity = RazorpayAdapter.validate_payment_entity(payload, event_name)
    except MalformedPayloadError as e:
        logger.warning("Rejected webhook: malformed payment entity. %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    processed_ids.add(event_id)

    metadata = {
        "payment_id": payment_entity.get("id"),
        "amount": payment_entity.get("amount"),
        "currency": payment_entity.get("currency"),
        "status": payment_entity.get("status"),
        "method": payment_entity.get("method"),
        "order_id": payment_entity.get("order_id"),
        "created_at": payment_entity.get("created_at"),
        "error_code": payment_entity.get("error_code"),
        "error_description": payment_entity.get("error_description"),
        "error_reason": payment_entity.get("error_reason"),
        "error_source": payment_entity.get("error_source"),
        "error_step": payment_entity.get("error_step"),
    }

    return {
        "status": "accepted",
        "event_id": event_id,
        "event_type": event_name,
        "payment_id": payment_entity.get("id"),
        "classification": "NEW",
        "extracted_metadata": metadata,
    }
