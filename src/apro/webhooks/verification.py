"""Webhook signature verification logic for Razorpay."""

import hashlib
import hmac
import logging

logger = logging.getLogger("apro.webhooks.verification")


def verify_razorpay_signature(
    body: bytes, signature: str | None, secret: str | None
) -> bool:
    """Verify that the webhook signature is valid using constant-time comparison.

    Args:
        body: The raw request body as bytes.
        signature: The signature string from the X-Razorpay-Signature header.
        secret: The configured webhook secret.

    Returns:
        True if the signature is valid, False otherwise.
    """
    if not signature:
        logger.warning("Signature header is missing.")
        return False

    if not secret:
        logger.error("Razorpay webhook secret is not configured.")
        return False

    try:
        # Calculate the HMAC-SHA256 hex digest over the exact raw body
        expected_signature = hmac.new(
            secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()

        # Perform constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(expected_signature, signature)
        if not is_valid:
            logger.warning(
                "Signature verification failed: expected %s, got %s",
                expected_signature,
                signature,
            )
        return is_valid
    except Exception as e:
        logger.error("Error occurred during signature verification: %s", e)
        return False
