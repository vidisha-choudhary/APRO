"""Tests for Razorpay provider request and response schemas."""

import pytest
from pydantic import ValidationError

from apro.providers.razorpay.models import (
    RazorpayErrorResponse,
    RazorpayNotifyRequest,
    RazorpayNotifyResponse,
    RazorpayPaymentLinkCustomer,
    RazorpayPaymentLinkNotify,
    RazorpayPaymentLinkRequest,
    RazorpayPaymentLinkResponse,
)


def test_payment_link_request_validation() -> None:
    """Verify Payment Link request enforces positive amount and fields."""
    req = RazorpayPaymentLinkRequest(
        amount=50000,
        currency="INR",
        description="Recovery Link for Case 123",
        customer=RazorpayPaymentLinkCustomer(
            name="Rahul Sharma", email="rahul@example.com", contact="+919876543210"
        ),
        notify=RazorpayPaymentLinkNotify(sms=True, email=True),
        reference_id="apro_case123_ref",
    )
    assert req.amount == 50000
    assert req.currency == "INR"
    assert req.customer is not None
    assert req.customer.name == "Rahul Sharma"
    assert req.reference_id == "apro_case123_ref"


def test_payment_link_request_negative_amount_rejected() -> None:
    """Verify negative or zero amount is rejected."""
    with pytest.raises(ValidationError):
        RazorpayPaymentLinkRequest(
            amount=0,
            description="Invalid 0 amount",
        )
    with pytest.raises(ValidationError):
        RazorpayPaymentLinkRequest(
            amount=-500,
            description="Invalid negative amount",
        )


def test_payment_link_response_parsing() -> None:
    """Verify Payment Link response model parses correctly."""
    data = {
        "id": "plink_test_998877",
        "amount": 50000,
        "currency": "INR",
        "status": "created",
        "short_url": "https://rzp.io/i/test99",
        "description": "Test recovery",
        "created_at": 1725300000,
        "reference_id": "apro_ref_99",
    }
    res = RazorpayPaymentLinkResponse(**data)
    assert res.id == "plink_test_998877"
    assert res.status == "created"
    assert res.short_url == "https://rzp.io/i/test99"


def test_notify_request_and_response() -> None:
    """Verify notification request and response models."""
    req = RazorpayNotifyRequest(payment_link_id="plink_123", medium="sms")
    assert req.payment_link_id == "plink_123"
    assert req.medium == "sms"

    res = RazorpayNotifyResponse(success=True)
    assert res.success is True


def test_error_response_parsing() -> None:
    """Verify error response parsing."""
    raw = {
        "error": {
            "code": "BAD_REQUEST_ERROR",
            "description": "Amount must be in paise",
            "source": "gateway",
            "step": "payment_initiation",
            "reason": "invalid_amount",
        }
    }
    err = RazorpayErrorResponse(**raw)
    assert err.error.code == "BAD_REQUEST_ERROR"
    assert err.error.description == "Amount must be in paise"
