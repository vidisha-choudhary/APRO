"""Phase 11 BaseExecutor adapters for Razorpay TEST mode."""

from datetime import UTC, datetime

from apro.domain.enums import ExecutionMode, RecoveryActionType
from apro.execution.exceptions import (
    ExecutionAuthorizationError,
    ExecutionValidationError,
)
from apro.execution.interfaces import BaseExecutor
from apro.execution.models import ApprovedExecutionRequest, ExecutionResult
from apro.providers.exceptions import ProviderRequestValidationError
from apro.providers.razorpay.client import RazorpayTestModeClient
from apro.providers.razorpay.mapper import (
    map_approved_request_to_notify_request,
    map_approved_request_to_payment_link_request,
    map_notify_response_to_execution_result,
    map_payment_link_response_to_execution_result,
    map_provider_error_to_execution_result,
)


class RazorpayTestModePaymentLinkExecutor(BaseExecutor):
    """Executor implementing Payment Link creation in Razorpay TEST mode."""

    def __init__(self, client: RazorpayTestModeClient) -> None:
        self.client = client

    @property
    def action_type(self) -> RecoveryActionType:
        return RecoveryActionType.ALTERNATE_RECOVERY

    @property
    def supported_modes(self) -> set[ExecutionMode]:
        return {ExecutionMode.RAZORPAY_TEST_MODE}

    def validate(self, request: ApprovedExecutionRequest) -> None:
        """Validate request preconditions and parameters before dispatch."""
        if request.execution_mode != ExecutionMode.RAZORPAY_TEST_MODE:
            msg = (
                f"RazorpayTestModePaymentLinkExecutor only supports "
                f"RAZORPAY_TEST_MODE, got '{request.execution_mode}'"
            )
            raise ExecutionAuthorizationError(msg)

        try:
            map_approved_request_to_payment_link_request(request)
        except ProviderRequestValidationError as e:
            raise ExecutionValidationError(str(e)) from e

    async def execute(self, request: ApprovedExecutionRequest) -> ExecutionResult:
        """Execute Payment Link creation against Razorpay TEST API."""
        started_at = datetime.now(UTC)
        try:
            plink_req = map_approved_request_to_payment_link_request(request)
            response = await self.client.create_payment_link(plink_req)
            completed_at = datetime.now(UTC)
            return map_payment_link_response_to_execution_result(
                request=request,
                response=response,
                started_at=started_at,
                completed_at=completed_at,
                executor_name=type(self).__name__,
            )
        except Exception as e:
            completed_at = datetime.now(UTC)
            return map_provider_error_to_execution_result(
                request=request,
                error=e,
                started_at=started_at,
                completed_at=completed_at,
                executor_name=type(self).__name__,
                known_secrets=self.client.config.get_secret_set(),
            )


class RazorpayTestModeOutreachExecutor(BaseExecutor):
    """Executor implementing Payment Link outreach in Razorpay TEST mode."""

    def __init__(self, client: RazorpayTestModeClient) -> None:
        self.client = client

    @property
    def action_type(self) -> RecoveryActionType:
        return RecoveryActionType.OUTREACH

    @property
    def supported_modes(self) -> set[ExecutionMode]:
        return {ExecutionMode.RAZORPAY_TEST_MODE}

    def validate(self, request: ApprovedExecutionRequest) -> None:
        """Validate outreach request parameters before dispatch."""
        if request.execution_mode != ExecutionMode.RAZORPAY_TEST_MODE:
            msg = (
                f"RazorpayTestModeOutreachExecutor only supports "
                f"RAZORPAY_TEST_MODE, got '{request.execution_mode}'"
            )
            raise ExecutionAuthorizationError(msg)

        try:
            map_approved_request_to_notify_request(request)
        except ProviderRequestValidationError as e:
            raise ExecutionValidationError(str(e)) from e

    async def execute(self, request: ApprovedExecutionRequest) -> ExecutionResult:
        """Execute Payment Link notification against Razorpay TEST API."""
        started_at = datetime.now(UTC)
        try:
            notify_req = map_approved_request_to_notify_request(request)
            response = await self.client.notify_payment_link(notify_req)
            completed_at = datetime.now(UTC)
            return map_notify_response_to_execution_result(
                request=request,
                response=response,
                started_at=started_at,
                completed_at=completed_at,
                executor_name=type(self).__name__,
            )
        except Exception as e:
            completed_at = datetime.now(UTC)
            return map_provider_error_to_execution_result(
                request=request,
                error=e,
                started_at=started_at,
                completed_at=completed_at,
                executor_name=type(self).__name__,
                known_secrets=self.client.config.get_secret_set(),
            )


__all__ = [
    "RazorpayTestModeOutreachExecutor",
    "RazorpayTestModePaymentLinkExecutor",
]
