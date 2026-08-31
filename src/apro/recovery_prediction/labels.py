"""Action-conditioned recovery outcome label construction from simulator truth."""

from apro.dataset.models import EvaluationTruthRecord, GovernedDataset
from apro.recovery_prediction.enums import (
    OUTCOME_TAXONOMY_VERSION,
    RECOVERY_ACTION_ORDER,
    RECOVERY_ACTION_SCHEMA_VERSION,
    PredictedOutcomeState,
    RecoveryAction,
)
from apro.recovery_prediction.models import RecoveryOutcomeLabel
from apro.simulation.enums import SimulatedActionType, SimulatedOutcomeStatus

SIMULATED_STATUS_TO_PREDICTED_STATE: dict[
    SimulatedOutcomeStatus, PredictedOutcomeState
] = {
    SimulatedOutcomeStatus.SUCCESS: PredictedOutcomeState.SUCCESS,
    SimulatedOutcomeStatus.FAILURE: PredictedOutcomeState.FAILURE,
    SimulatedOutcomeStatus.PENDING: PredictedOutcomeState.PENDING,
}


def construct_outcome_label(
    truth_record: EvaluationTruthRecord,
    action: RecoveryAction,
    payment_amount: int,
    dataset_version: str,
) -> RecoveryOutcomeLabel:
    """Construct supervised RecoveryOutcomeLabel for a scenario and action."""
    sim_action = SimulatedActionType(action.value)
    if sim_action not in truth_record.potential_outcomes:
        msg = (
            f"Action '{action.value}' not found in potential outcomes for "
            f"scenario '{truth_record.scenario_id}'."
        )
        raise ValueError(msg)

    raw_status = truth_record.potential_outcomes[sim_action]
    outcome_state = SIMULATED_STATUS_TO_PREDICTED_STATE.get(
        raw_status, PredictedOutcomeState.FAILURE
    )

    recovered_amount = (
        payment_amount if outcome_state == PredictedOutcomeState.SUCCESS else 0
    )

    return RecoveryOutcomeLabel(
        record_id=truth_record.record_id,
        scenario_id=truth_record.scenario_id,
        action=action,
        outcome_state=outcome_state,
        recovered_amount=recovered_amount,
        label_source="governed_simulator_ground_truth",
        dataset_version=dataset_version,
        action_schema_version=RECOVERY_ACTION_SCHEMA_VERSION,
        outcome_schema_version=OUTCOME_TAXONOMY_VERSION,
    )


def construct_outcome_labels_from_dataset(
    dataset: GovernedDataset,
    actions: list[RecoveryAction] | None = None,
) -> list[RecoveryOutcomeLabel]:
    """Construct action-conditioned labels across records in a GovernedDataset."""
    target_actions = actions or list(RECOVERY_ACTION_ORDER)
    labels: list[RecoveryOutcomeLabel] = []

    for rec in dataset.records:
        payment_amount = rec.model_input.features.payment_amount
        ds_version = dataset.manifest.dataset_version
        for act in target_actions:
            labels.append(
                construct_outcome_label(
                    truth_record=rec.evaluation_truth,
                    action=act,
                    payment_amount=payment_amount,
                    dataset_version=ds_version,
                )
            )
    return labels
