"""Tests for mapping Phase 11 requests to Razorpay TEST payloads."""

from datetime import UTC, datetime

import pytest

from apro.domain.enums import ExecutionMode, RecoveryActionType
from apro.execution.models import ApprovedExecutionRequest
from apro.providers.exceptions import ProviderRequestValidationError
from apro.providers.razorpay.mapper import (
    map_approved_request_to_notify_request,
    map_approved_request_to_payment_link_request,
)


def _make_request(params: dict) -> ApprovedExecutionRequest:
    now = datetime.now(UTC)
    return ApprovedExecutionRequest(
        execution_id="exec_test_001",
        case_id="case_test_001",
        action_id="act_test_001",
        action_type=RecoveryActionType.ALTERNATE_RECOVERY,
        policy_decision_id="pol_test_001",
        idempotency_key="idem_test_001",
        execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
        parameters=params,
        requested_at=now,
        policy_version="pol-v1",
        rule_set_version="rules-v1",
        action_schema_version="act-v1",
    )


def test_payment_link_request_mapping_success() -> None:
    """Verify mapping an authorized request to a Razorpay payment link request."""
    req = _make_request(
        {
            "amount": 75000,
            "currency": "INR",
            "description": "Invoice recovery",
            "customer_name": "Priya Patel",
            "customer_email": "priya@example.com",
            "customer_contact": "+919876543210",
            "notify": {"sms": True, "email": False},
            "notes": {"merchant_order_id": "order_abc"},
        }
    )
    plink_req = map_approved_request_to_payment_link_request(req)
    assert plink_req.amount == 75000
    assert plink_req.currency == "INR"
    assert plink_req.description == "Invoice recovery"
    assert plink_req.customer is not None
    assert plink_req.customer.name == "Priya Patel"
    assert plink_req.customer.email == "priya@example.com"
    assert plink_req.notify is not None
    assert plink_req.notify.sms is True
    assert plink_req.notify.email is False
    assert plink_req.notes["apro_case_id"] == "case_test_001"
    assert plink_req.notes["merchant_order_id"] == "order_abc"


def test_payment_link_request_missing_amount_raises_error() -> None:
    """Verify missing or invalid amount raises ProviderRequestValidationError."""
    req = _make_request({"description": "No amount provided"})
    with pytest.raises(ProviderRequestValidationError):
        map_approved_request_to_payment_link_request(req)


def test_secret_parameters_rejected() -> None:
    """Verify parameters containing secret/credential keys are rejected."""
    req = _make_request({"amount": 50000, "api_key": "leaked_key_value"})
    with pytest.raises(ProviderRequestValidationError):
        map_approved_request_to_payment_link_request(req)

    req_auth = _make_request({"amount": 50000, "authorization": "Bearer xxx"})
    with pytest.raises(ProviderRequestValidationError):
        map_approved_request_to_payment_link_request(req_auth)


def test_notify_request_mapping() -> None:
    """Verify mapping an outreach notification request."""
    req = _make_request(
        {
            "payment_link_id": "plink_test_12345",
            "medium": "sms",
        }
    )
    notify_req = map_approved_request_to_notify_request(req)
    assert notify_req.payment_link_id == "plink_test_12345"
    assert notify_req.medium == "sms"
