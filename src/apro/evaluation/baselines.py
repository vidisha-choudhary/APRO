"""Deterministic baseline strategy adapters for APRO Phase 6 evaluation."""

from abc import ABC, abstractmethod

from apro.dataset.enums import DatasetType
from apro.dataset.models import GovernedDataset, ModelInputRecord
from apro.simulation.enums import (
    SimulatedActionType,
    SimulatedOutcomeStatus,
)


class BaseStrategy(ABC):
    """Abstract base strategy interface for APRO benchmark evaluation."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable strategy name."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Strategy implementation version."""

    @abstractmethod
    def select_action(self, model_input: ModelInputRecord) -> SimulatedActionType:
        """Select a candidate action given observable model input."""


class NoInterventionStrategy(BaseStrategy):
    """Baseline 0 — Always select STOP (no recovery action attempted)."""

    @property
    def name(self) -> str:
        return "No Intervention"

    @property
    def version(self) -> str:
        return "v1.0"

    def select_action(self, model_input: ModelInputRecord) -> SimulatedActionType:
        _ = model_input
        return SimulatedActionType.STOP


class AlwaysRetryStrategy(BaseStrategy):
    """Baseline 1 — Always select RETRY if candidate, otherwise fallback to STOP."""

    @property
    def name(self) -> str:
        return "Always Retry"

    @property
    def version(self) -> str:
        return "v1.0"

    def select_action(self, model_input: ModelInputRecord) -> SimulatedActionType:
        if SimulatedActionType.RETRY in model_input.features.candidate_actions:
            return SimulatedActionType.RETRY
        return SimulatedActionType.STOP


class StaticRulesStrategy(BaseStrategy):
    """Baseline 2 — Documented static failure classification rules."""

    def __init__(
        self, custom_rules: dict[str, SimulatedActionType] | None = None
    ) -> None:
        # Default documented rule mapping based on observable failure characteristics
        self._rules: dict[str, SimulatedActionType] = custom_rules or {
            "GATEWAY_TIMEOUT": SimulatedActionType.RETRY,
            "PROCESSING_TIMEOUT": SimulatedActionType.RETRY,
            "TRANSIENT_NETWORK_ERROR": SimulatedActionType.RETRY,
            "ISSUER_UNAVAILABLE": SimulatedActionType.PAYMENT_LINK,
            "SWITCH_MALFUNCTION": SimulatedActionType.PAYMENT_LINK,
            "BANK_TIMEOUT": SimulatedActionType.PAYMENT_LINK,
            "INSUFFICIENT_FUNDS": SimulatedActionType.OUTREACH,
            "LIMIT_EXCEEDED": SimulatedActionType.OUTREACH,
            "PAYMENT_CANCELLED": SimulatedActionType.OUTREACH,
            "OTP_EXPIRED": SimulatedActionType.OUTREACH,
            "3DS_AUTH_FAILED": SimulatedActionType.OUTREACH,
            "2FA_DECLINED": SimulatedActionType.OUTREACH,
            "EXPIRED_CARD": SimulatedActionType.PAYMENT_LINK,
            "VPA_NOT_FOUND": SimulatedActionType.PAYMENT_LINK,
            "ACCOUNT_RESTRICTED": SimulatedActionType.PAYMENT_LINK,
            "ACQUIRER_REJECTED": SimulatedActionType.RETRY,
            "GATEWAY_ERROR": SimulatedActionType.RETRY,
            "TRANSACTION_TIMED_OUT": SimulatedActionType.RETRY,
            "CONFIRMATION_TIMEOUT": SimulatedActionType.RETRY,
        }

    @property
    def name(self) -> str:
        return "Static Failure Rules"

    @property
    def version(self) -> str:
        return "v1.0"

    def select_action(self, model_input: ModelInputRecord) -> SimulatedActionType:
        code = model_input.features.failure_code
        preferred_action = self._rules.get(code, SimulatedActionType.STOP)

        if preferred_action in model_input.features.candidate_actions:
            return preferred_action
        return SimulatedActionType.STOP


class GlobalActionRateStrategy(BaseStrategy):
    """Baseline 3 — Selects action with highest observed recovery rate."""

    def __init__(
        self, action_rates: dict[SimulatedActionType, float] | None = None
    ) -> None:
        self._action_rates: dict[SimulatedActionType, float] | None = action_rates
        self._is_fitted: bool = action_rates is not None

    @property
    def name(self) -> str:
        return "Global Action Rate"

    @property
    def version(self) -> str:
        return "v1.0"

    @property
    def is_fitted(self) -> bool:
        """Indicate whether the strategy has been fitted with training observations."""
        return self._is_fitted

    def fit(self, training_dataset: GovernedDataset) -> None:
        """Compute empirical recovery rates strictly from legitimate training data."""
        # Held-out protection: reject VALIDATION, HELD_OUT_TEST, BENCHMARK
        if training_dataset.manifest.dataset_type != DatasetType.TRAINING:
            msg = (
                "GlobalActionRateStrategy.fit() is strictly permitted on "
                f"TRAINING datasets; received dataset of type "
                f"'{training_dataset.manifest.dataset_type.value}'."
            )
            raise ValueError(msg)

        success_counts: dict[SimulatedActionType, int] = dict.fromkeys(
            SimulatedActionType, 0
        )
        total_counts: dict[SimulatedActionType, int] = dict.fromkeys(
            SimulatedActionType, 0
        )

        for record in training_dataset.records:
            # Strictly use training_label from model input; never use truth
            obs = record.model_input.training_label
            if obs is None:
                continue

            total_counts[obs.observed_action] += 1
            if obs.observed_outcome_status == SimulatedOutcomeStatus.SUCCESS:
                success_counts[obs.observed_action] += 1

        new_rates: dict[SimulatedActionType, float] = {}
        for action in SimulatedActionType:
            tot = total_counts[action]
            new_rates[action] = (success_counts[action] / tot) if tot > 0 else 0.0

        self._action_rates = new_rates
        self._is_fitted = True

    def select_action(self, model_input: ModelInputRecord) -> SimulatedActionType:
        if not self._is_fitted or self._action_rates is None:
            msg = (
                "GlobalActionRateStrategy is unfitted. You must call fit() with a "
                "valid TRAINING dataset before selecting actions."
            )
            raise ValueError(msg)

        candidates = model_input.features.candidate_actions
        if not candidates:
            return SimulatedActionType.STOP

        # Pick candidate action with highest historical rate
        return max(
            candidates,
            key=lambda act: self._action_rates.get(act, 0.0),  # type: ignore[union-attr]
        )
