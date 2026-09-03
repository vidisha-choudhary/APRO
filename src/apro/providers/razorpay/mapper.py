"""Request and response mapping between Phase 11 and Razorpay TEST schemas."""

from datetime import datetime
from typing import Any

from apro.domain.enums import ExecutionStatus
from apro.execution.models import ApprovedExecutionRequest, ExecutionResult
from apro.providers.exceptions import (
    ProviderAmbiguousResultError,
    ProviderAuthenticationError,
    ProviderMalformedResponseError,
    ProviderRateLimitError,
    ProviderRejectedError,
    ProviderRequestValidationError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from apro.providers.razorpay.models import (
    RazorpayNotifyRequest,
    RazorpayNotifyResponse,
    RazorpayPaymentLinkCustomer,
    RazorpayPaymentLinkNotify,
    RazorpayPaymentLinkRequest,
    RazorpayPaymentLinkResponse,
)
from apro.providers.razorpay.security import SENSITIVE_FIELD_NAMES, sanitize_text


def validate_parameters_for_secrets(parameters: dict[str, Any]) -> None:
    """Ensure no forbidden secret keys are passed in execution parameters."""
    for key in parameters:
        k_norm = key.lower().replace("-", "_")
        if k_norm in SENSITIVE_FIELD_NAMES:
            msg = (
                f"Parameter '{key}' contains sensitive secret terminology. "
                "Forbidden in execution request parameters."
            )
            raise ProviderRequestValidationError(msg)


def map_approved_request_to_payment_link_request(
    request: ApprovedExecutionRequest,
    default_currency: str = "INR",
) -> RazorpayPaymentLinkRequest:
    """Map Phase 11 ApprovedExecutionRequest to RazorpayPaymentLinkRequest."""
    params = request.parameters
    validate_parameters_for_secrets(params)

    # 1. Amount
    amount = params.get("amount")
    if amount is None or not isinstance(amount, int) or amount <= 0:
        msg = (
            f"Payment Link creation requires a positive integer amount "
            f"in paise, got '{amount}'"
        )
        raise ProviderRequestValidationError(msg)

    # 2. Currency
    currency = str(params.get("currency", default_currency)).upper()

    # 3. Description
    description = str(
        params.get(
            "description",
            f"APRO Recovery Link for Case {request.case_id}",
        )
    )

    # 4. Customer Details
    cust_data = params.get("customer")
    customer = None
    if isinstance(cust_data, dict):
        customer = RazorpayPaymentLinkCustomer(
            name=cust_data.get("name"),
            email=cust_data.get("email"),
            contact=cust_data.get("contact"),
        )
    elif (
        "customer_contact" in params
        or "customer_email" in params
        or "customer_name" in params
    ):
        customer = RazorpayPaymentLinkCustomer(
            name=params.get("customer_name"),
            email=params.get("customer_email"),
            contact=params.get("customer_contact"),
        )

    # 5. Notification options
    notify_data = params.get("notify")
    notify = None
    if isinstance(notify_data, dict):
        notify = RazorpayPaymentLinkNotify(
            sms=bool(notify_data.get("sms", True)),
            email=bool(notify_data.get("email", True)),
        )

    # 6. Notes (Safe metadata binding)
    notes = {
        "apro_case_id": request.case_id,
        "apro_execution_id": request.execution_id,
        "apro_action_id": request.action_id,
    }
    user_notes = params.get("notes")
    if isinstance(user_notes, dict):
        for k, v in user_notes.items():
            if str(k).lower() not in SENSITIVE_FIELD_NAMES:
                notes[str(k)] = str(v)

    # 7. Deterministic reference ID
    # Max length in Razorpay is 40 alphanumeric/hyphen characters
    ref_id = (
        params.get("reference_id")
        or f"apro_{request.case_id[:16]}_{request.execution_id[:12]}"
    )
    ref_id = ref_id[:40]

    return RazorpayPaymentLinkRequest(
        amount=amount,
        currency=currency,
        accept_partial=bool(params.get("accept_partial", False)),
        description=description,
        customer=customer,
        notify=notify,
        reminder_enable=bool(params.get("reminder_enable", False)),
        notes=notes,
        expire_by=params.get("expire_by"),
        reference_id=ref_id,
    )


def map_payment_link_response_to_execution_result(
    request: ApprovedExecutionRequest,
    response: RazorpayPaymentLinkResponse,
    started_at: datetime,
    completed_at: datetime,
    executor_name: str = "RazorpayTestModePaymentLinkExecutor",
) -> ExecutionResult:
    """Map RazorpayPaymentLinkResponse to normalized Phase 11 ExecutionResult."""
    status_lower = response.status.lower()
    if status_lower in ("created", "paid", "partially_paid", "active"):
        status = ExecutionStatus.SUCCEEDED
    elif status_lower in ("cancelled", "expired"):
        status = ExecutionStatus.FAILED
    else:
        status = ExecutionStatus.UNKNOWN

    metadata: dict[str, Any] = {
        "short_url": response.short_url,
        "amount": response.amount,
        "currency": response.currency,
        "provider_status": response.status,
        "reference_id": response.reference_id,
        "provider": "razorpay_test_mode",
    }
    if response.created_at is not None:
        metadata["provider_created_at"] = response.created_at

    return ExecutionResult(
        execution_id=request.execution_id,
        action_id=request.action_id,
        case_id=request.case_id,
        status=status,
        execution_mode=request.execution_mode,
        provider_reference=response.id,
        error_code=None,
        error_message=None,
        started_at=started_at,
        completed_at=completed_at,
        executor_name=executor_name,
        metadata=metadata,
    )


def map_approved_request_to_notify_request(
    request: ApprovedExecutionRequest,
) -> RazorpayNotifyRequest:
    """Map Phase 11 ApprovedExecutionRequest to RazorpayNotifyRequest."""
    params = request.parameters
    validate_parameters_for_secrets(params)

    plink_id = params.get("payment_link_id") or params.get("provider_reference")
    if not plink_id or not isinstance(plink_id, str):
        msg = "Outreach notification requires 'payment_link_id' parameter."
        raise ProviderRequestValidationError(msg)

    medium = str(params.get("medium") or params.get("channel") or "sms").lower()
    if medium not in ("sms", "email"):
        msg = f"Unsupported notification medium '{medium}'. Must be 'sms' or 'email'."
        raise ProviderRequestValidationError(msg)

    return RazorpayNotifyRequest(
        payment_link_id=plink_id,
        medium=medium,
    )


def map_notify_response_to_execution_result(
    request: ApprovedExecutionRequest,
    response: RazorpayNotifyResponse,
    started_at: datetime,
    completed_at: datetime,
    executor_name: str = "RazorpayTestModeOutreachExecutor",
) -> ExecutionResult:
    """Map RazorpayNotifyResponse to normalized Phase 11 ExecutionResult."""
    status = ExecutionStatus.SUCCEEDED if response.success else ExecutionStatus.FAILED
    plink_id = request.parameters.get("payment_link_id") or request.parameters.get(
        "provider_reference"
    )
    medium = (
        request.parameters.get("medium") or request.parameters.get("channel") or "sms"
    )

    return ExecutionResult(
        execution_id=request.execution_id,
        action_id=request.action_id,
        case_id=request.case_id,
        status=status,
        execution_mode=request.execution_mode,
        provider_reference=str(plink_id),
        error_code=None,
        error_message=None,
        started_at=started_at,
        completed_at=completed_at,
        executor_name=executor_name,
        metadata={
            "delivery_status": "DELIVERED" if response.success else "FAILED",
            "medium": str(medium),
            "provider": "razorpay_test_mode",
        },
    )


def map_provider_error_to_execution_result(
    request: ApprovedExecutionRequest,
    error: Exception,
    started_at: datetime,
    completed_at: datetime,
    executor_name: str,
    known_secrets: set[str] | None = None,
) -> ExecutionResult:
    """Map a caught ProviderError to an immutable Phase 11 ExecutionResult."""
    clean_msg = sanitize_text(str(error), known_secrets)

    if isinstance(error, (ProviderTimeoutError, ProviderAmbiguousResultError)):
        status = ExecutionStatus.UNKNOWN
        error_code = "PROVIDER_TIMEOUT"
    elif isinstance(error, ProviderMalformedResponseError):
        status = ExecutionStatus.UNKNOWN
        error_code = "PROVIDER_MALFORMED_RESPONSE"
    elif isinstance(error, ProviderAuthenticationError):
        status = ExecutionStatus.FAILED
        error_code = "PROVIDER_AUTH_ERROR"
    elif isinstance(error, ProviderRateLimitError):
        status = ExecutionStatus.FAILED
        error_code = "PROVIDER_RATE_LIMIT"
    elif isinstance(error, ProviderUnavailableError):
        status = ExecutionStatus.FAILED
        error_code = "PROVIDER_UNAVAILABLE"
    elif isinstance(error, (ProviderRejectedError, ProviderRequestValidationError)):
        status = ExecutionStatus.FAILED
        error_code = "PROVIDER_REJECTED"
    else:
        status = ExecutionStatus.FAILED
        error_code = "PROVIDER_ERROR"

    return ExecutionResult(
        execution_id=request.execution_id,
        action_id=request.action_id,
        case_id=request.case_id,
        status=status,
        execution_mode=request.execution_mode,
        provider_reference=None,
        error_code=error_code,
        error_message=clean_msg,
        started_at=started_at,
        completed_at=completed_at,
        executor_name=executor_name,
        metadata={"provider": "razorpay_test_mode", "error_type": type(error).__name__},
    )


__all__ = [
    "map_approved_request_to_notify_request",
    "map_approved_request_to_payment_link_request",
    "map_notify_response_to_execution_result",
    "map_payment_link_response_to_execution_result",
    "map_provider_error_to_execution_result",
    "validate_parameters_for_secrets",
]
