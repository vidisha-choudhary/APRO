"""Decision-time feature snapshot generation for APRO Phase 6."""

from datetime import UTC, datetime

from apro.dataset.models import FeatureSnapshot
from apro.simulation.models import ObservableScenarioState


def create_feature_snapshot(
    observable_state: ObservableScenarioState,
    decision_timestamp: datetime | str | None = None,
    schema_version: str = "feature-schema-v1",
) -> FeatureSnapshot:
    """Extract a decision-time feature snapshot from an observable scenario projection.

    Guarantees:
    - Only observable fields are copied.
    - No hidden ground truth or post-decision outcomes are included.
    - Immutable feature snapshot is versioned.
    """
    if decision_timestamp is None:
        ts_str = datetime.now(UTC).isoformat()
    elif isinstance(decision_timestamp, datetime):
        ts_str = decision_timestamp.isoformat()
    else:
        ts_str = decision_timestamp

    return FeatureSnapshot(
        feature_schema_version=schema_version,
        decision_timestamp=ts_str,
        payment_id=observable_state.payment.payment_id,
        payment_amount=observable_state.payment.amount,
        currency=observable_state.payment.currency,
        payment_method=observable_state.payment.method,
        attempt_count=observable_state.payment.attempt_count,
        failure_reason=observable_state.failure.failure_reason,
        failure_code=observable_state.failure.failure_code,
        decline_code=observable_state.failure.decline_code,
        customer_id=observable_state.customer.customer_id,
        previous_payment_count=observable_state.customer.previous_payment_count,
        previous_success_count=observable_state.customer.previous_success_count,
        previous_failure_count=observable_state.customer.previous_failure_count,
        previous_recovery_count=observable_state.customer.previous_recovery_count,
        previous_retry_success=observable_state.customer.previous_retry_success,
        previous_payment_link_success=observable_state.customer.previous_payment_link_success,
        hour_of_day=observable_state.temporal.hour_of_day,
        day_of_week=observable_state.temporal.day_of_week,
        is_weekend=observable_state.temporal.is_weekend,
        time_since_previous_attempt_seconds=observable_state.temporal.time_since_previous_attempt_seconds,
        time_since_previous_successful_payment_seconds=observable_state.temporal.time_since_previous_successful_payment_seconds,
        candidate_actions=list(observable_state.candidate_actions),
    )
