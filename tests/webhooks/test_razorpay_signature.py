import hashlib
import hmac

from apro.webhooks.verification import verify_razorpay_signature


def test_signature_verification_success() -> None:
    """Test verification passes with a valid body and signature."""
    secret = "test_webhook_secret"
    body = b'{"event": "payment.failed"}'
    signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

    assert verify_razorpay_signature(body, signature, secret) is True


def test_signature_verification_invalid() -> None:
    """Test verification fails with an incorrect signature."""
    secret = "test_webhook_secret"
    body = b'{"event": "payment.failed"}'
    assert verify_razorpay_signature(body, "invalid_signature_hash", secret) is False


def test_signature_verification_missing_signature() -> None:
    """Test verification fails when signature is missing or empty."""
    secret = "test_webhook_secret"
    body = b'{"event": "payment.failed"}'
    assert verify_razorpay_signature(body, None, secret) is False
    assert verify_razorpay_signature(body, "", secret) is False


def test_signature_verification_missing_secret() -> None:
    """Test verification fails when webhook secret is not configured."""
    body = b'{"event": "payment.failed"}'
    assert verify_razorpay_signature(body, "some_sig", None) is False


def test_signature_verification_mutated_body() -> None:
    """Test fails when body is modified but original signature is used."""
    secret = "test_webhook_secret"
    body = b'{"event": "payment.failed"}'
    signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

    # Mutate the body by changing a single character
    mutated_body = b'{"event": "payment.failex"}'
    assert verify_razorpay_signature(mutated_body, signature, secret) is False


def test_signature_verification_empty_body() -> None:
    """Test that signature verification detects mismatch for empty body."""
    secret = "test_webhook_secret"

    body = b""
    assert verify_razorpay_signature(body, "incorrect_sig", secret) is False
