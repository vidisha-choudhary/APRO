"""Tests for mapping Razorpay TEST responses to Phase 11 ExecutionResult."""

from datetime import UTC, datetime

from apro.domain.enums import ExecutionMode, ExecutionStatus, RecoveryActionType
from apro.execution.models import ApprovedExecutionRequest
from apro.providers.exceptions import (
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from apro.providers.razorpay.mapper import (
    map_notify_response_to_execution_result,
    map_payment_link_response_to_execution_result,
    map_provider_error_to_execution_result,
)
from apro.providers.razorpay.models import (
    RazorpayNotifyResponse,
    RazorpayPaymentLinkResponse,
)


def _make_request() -> ApprovedExecutionRequest:
    now = datetime.now(UTC)
    return ApprovedExecutionRequest(
        execution_id="exec_test_resp",
        case_id="case_test_resp",
        action_id="act_test_resp",
        action_type=RecoveryActionType.ALTERNATE_RECOVERY,
        policy_decision_id="pol_test_resp",
        idempotency_key="idem_test_resp",
        execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
        parameters={"amount": 50000, "payment_link_id": "plink_test_resp"},
        requested_at=now,
        policy_version="pol-v1",
        rule_set_version="rules-v1",
        action_schema_version="act-v1",
    )


def test_payment_link_created_maps_to_succeeded() -> None:
    """Verify created payment link status maps to ExecutionStatus.SUCCEEDED."""
    req = _make_request()
    start = datetime.now(UTC)
    res_model = RazorpayPaymentLinkResponse(
        id="plink_test_created_123",
        amount=50000,
        currency="INR",
        status="created",
        short_url="https://rzp.io/i/testlink",
    )
    result = map_payment_link_response_to_execution_result(
        req, res_model, start, datetime.now(UTC)
    )
    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.provider_reference == "plink_test_created_123"
    assert result.metadata["short_url"] == "https://rzp.io/i/testlink"
    assert result.metadata["amount"] == 50000


def test_payment_link_cancelled_maps_to_failed() -> None:
    """Verify cancelled payment link status maps to ExecutionStatus.FAILED."""
    req = _make_request()
    start = datetime.now(UTC)
    res_model = RazorpayPaymentLinkResponse(
        id="plink_test_canc_123",
        amount=50000,
        currency="INR",
        status="cancelled",
    )
    result = map_payment_link_response_to_execution_result(
        req, res_model, start, datetime.now(UTC)
    )
    assert result.status == ExecutionStatus.FAILED
    assert result.provider_reference == "plink_test_canc_123"


def test_notify_response_maps_to_succeeded() -> None:
    """Verify notification response maps to ExecutionStatus.SUCCEEDED."""
    req = _make_request()
    start = datetime.now(UTC)
    notify_res = RazorpayNotifyResponse(success=True)
    result = map_notify_response_to_execution_result(
        req, notify_res, start, datetime.now(UTC)
    )
    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.metadata["delivery_status"] == "DELIVERED"


def test_timeout_maps_to_unknown_error_status() -> None:
    """Verify timeout maps to ExecutionStatus.UNKNOWN with PROVIDER_TIMEOUT."""
    req = _make_request()
    start = datetime.now(UTC)
    err = ProviderTimeoutError("Connection timed out")
    result = map_provider_error_to_execution_result(
        req, err, start, datetime.now(UTC), "RazorpayTestModePaymentLinkExecutor"
    )
    assert result.status == ExecutionStatus.UNKNOWN
    assert result.error_code == "PROVIDER_TIMEOUT"
    assert "timed out" in (result.error_message or "")


def test_auth_and_rate_limit_map_to_failed() -> None:
    """Verify 401 and 429 map to ExecutionStatus.FAILED."""
    req = _make_request()
    start = datetime.now(UTC)
    auth_err = ProviderAuthenticationError("Invalid API key")
    res_auth = map_provider_error_to_execution_result(
        req, auth_err, start, datetime.now(UTC), "RazorpayTestModePaymentLinkExecutor"
    )
    assert res_auth.status == ExecutionStatus.FAILED
    assert res_auth.error_code == "PROVIDER_AUTH_ERROR"

    rl_err = ProviderRateLimitError("Too many requests")
    res_rl = map_provider_error_to_execution_result(
        req, rl_err, start, datetime.now(UTC), "RazorpayTestModePaymentLinkExecutor"
    )
    assert res_rl.status == ExecutionStatus.FAILED
    assert res_rl.error_code == "PROVIDER_RATE_LIMIT"
