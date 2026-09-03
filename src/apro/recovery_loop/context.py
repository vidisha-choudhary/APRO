"""Re-evaluation context builder for APRO Phase 13 Recovery Loop."""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from apro.dataset.models import FeatureSnapshot, ModelInputRecord
from apro.domain.models import Diagnosis, Outcome, Payment, RecoveryCase
from apro.recovery_loop.enums import RE_EVALUATION_CONTEXT_SCHEMA_VERSION
from apro.recovery_loop.models import ActionHistoryRecord, ReEvaluationContext
from apro.simulation.enums import SimulatedPaymentMethod


def compute_re_evaluation_id(
    case_id: str,
    cycle_number: int,
    latest_outcome_id: str | None = None,
    created_at: datetime | str | None = None,
) -> str:
    """Generate a deterministic SHA-256 identifier for a re-evaluation context.

    Uses logical state keys (case_id, cycle_number, latest_outcome_id, schema_version)
    to ensure strict determinism across calls and processes.
    """
    _ = created_at
    payload: dict[str, Any] = {
        "case_id": case_id,
        "cycle_number": cycle_number,
        "latest_outcome_id": latest_outcome_id or "",
        "schema_version": RE_EVALUATION_CONTEXT_SCHEMA_VERSION,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:32]


class ReEvaluationContextBuilder:
    """Builds observable context for Phase 9 decision re-evaluation while
    enforcing anti-leakage.
    """

    @staticmethod
    def build_context(
        case: RecoveryCase,
        payment: Payment,
        cycle_number: int,
        history: tuple[ActionHistoryRecord, ...],
        latest_diagnosis: Diagnosis | None,
        latest_outcome: Outcome | None,
        base_model_input: ModelInputRecord,
        now: datetime | None = None,
    ) -> ReEvaluationContext:
        """Construct a fresh, immutable ReEvaluationContext."""
        current_time = now or datetime.now(UTC)

        re_eval_id = compute_re_evaluation_id(
            case_id=case.case_id,
            cycle_number=cycle_number,
            latest_outcome_id=latest_outcome.outcome_id if latest_outcome else None,
            created_at=current_time,
        )

        # Update features for re-evaluation without leaking simulator hidden truth
        old_features = base_model_input.features

        # Map payment method safely
        try:
            p_method = SimulatedPaymentMethod(payment.method.lower())
        except (ValueError, AttributeError):
            p_method = old_features.payment_method

        updated_features = FeatureSnapshot(
            feature_schema_version=old_features.feature_schema_version,
            decision_timestamp=current_time.isoformat(),
            payment_id=payment.payment_id,
            payment_amount=payment.amount,
            currency=payment.currency,
            payment_method=p_method,
            attempt_count=cycle_number,
            failure_reason=old_features.failure_reason,
            failure_code=old_features.failure_code,
            decline_code=old_features.decline_code,
            customer_id=payment.customer_id,
            previous_payment_count=old_features.previous_payment_count,
            previous_success_count=old_features.previous_success_count,
            previous_failure_count=old_features.previous_failure_count
            + (cycle_number - 1),
            previous_recovery_count=old_features.previous_recovery_count,
            previous_retry_success=old_features.previous_retry_success,
            previous_payment_link_success=old_features.previous_payment_link_success,
            hour_of_day=current_time.hour,
            day_of_week=current_time.weekday(),
            is_weekend=current_time.weekday() >= 5,
            time_since_previous_attempt_seconds=int(
                (
                    current_time
                    - (history[-1].observed_at if history else case.opened_at)
                ).total_seconds()
            ),
            time_since_previous_successful_payment_seconds=old_features.time_since_previous_successful_payment_seconds,
            candidate_actions=old_features.candidate_actions,
        )

        updated_model_input = ModelInputRecord(
            record_id=base_model_input.record_id,
            dataset_type=base_model_input.dataset_type,
            dataset_version=base_model_input.dataset_version,
            scenario_id=base_model_input.scenario_id,
            generation_seed=base_model_input.generation_seed,
            scenario_version=base_model_input.scenario_version,
            configuration_version=base_model_input.configuration_version,
            feature_schema_version=base_model_input.feature_schema_version,
            benchmark_version=base_model_input.benchmark_version,
            features=updated_features,
            training_label=None,
        )

        return ReEvaluationContext(
            re_evaluation_id=re_eval_id,
            case_id=case.case_id,
            payment=payment,
            cycle_number=cycle_number,
            history=history,
            latest_diagnosis=latest_diagnosis,
            latest_outcome=latest_outcome,
            model_input=updated_model_input,
            created_at=current_time,
        )
