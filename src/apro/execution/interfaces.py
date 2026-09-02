"""Abstract executor interface for the APRO Execution Framework."""

from abc import ABC, abstractmethod

from apro.domain.enums import ExecutionMode, RecoveryActionType
from apro.execution.models import ApprovedExecutionRequest, ExecutionResult


class BaseExecutor(ABC):
    """Abstract interface for all recovery action executors."""

    @property
    @abstractmethod
    def action_type(self) -> RecoveryActionType:
        """The recovery action type handled by this executor."""
        ...

    @property
    @abstractmethod
    def supported_modes(self) -> set[ExecutionMode]:
        """The execution modes supported by this executor."""
        ...

    @abstractmethod
    def validate(self, request: ApprovedExecutionRequest) -> None:
        """Validate that the request parameters and mode are acceptable.

        Raises:
            ExecutionValidationError: If parameters are invalid.
            ExecutionAuthorizationError: If mode is unsupported.
        """
        ...

    @abstractmethod
    async def execute(self, request: ApprovedExecutionRequest) -> ExecutionResult:
        """Execute the recovery action and return an immutable ExecutionResult."""
        ...


__all__ = ["BaseExecutor"]
