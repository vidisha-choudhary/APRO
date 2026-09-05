"""Tests for Scenario 6: Truth-Plane and Latent Oracle Contamination Attacks."""

from datetime import UTC, datetime

import pytest

from apro.adversarial.assertions import assert_zero_truth_leakage
from apro.adversarial.enums import AttackDisposition
from apro.adversarial.executor import AdversarialAttackExecutor
from apro.adversarial.generators import generate_truth_plane_cases
from apro.dataset.enums import DatasetType
from apro.dataset.models import FeatureSnapshot, ModelInputRecord
from apro.decision.engine import EconomicDecisionEngine
from apro.decision.enums import RecoveryAction as DecisionAction
from apro.recovery_prediction.enums import (
    PredictedOutcomeState,
    PredictionUncertaintyState,
)
from apro.recovery_prediction.models import OutcomePrediction
from apro.simulation.enums import (
    SimulatedActionType,
    SimulatedPaymentMethod,
)


@pytest.mark.asyncio
async def test_scenario_6_truth_plane_cases(
    adversarial_executor: AdversarialAttackExecutor,
) -> None:
    """Scenario 6: Truth plane injection fails to alter runtime decision or leak into output."""
    cases = generate_truth_plane_cases(seed=1701, count=5)

    for case in cases:
        result = await adversarial_executor.execute_case(case)
        assert result.passed is True
        assert result.disposition == AttackDisposition.CONTAINED
        assert (
            "Runtime decision determined strictly by legitimate economic inputs"
            in result.observed_property
        )


def test_scenario_6_oracle_injection_decision_engine_invariance() -> None:
    """Amendment 4: Attempting to influence EconomicDecisionEngine runtime decision path with injected oracle truth."""
    now = datetime.now(UTC)

    feats = FeatureSnapshot(
        decision_timestamp=now.isoformat(),
        payment_id="pay_inv_001",
        payment_amount=50000,
        currency="INR",
        payment_method=SimulatedPaymentMethod.CARD,
        attempt_count=1,
        failure_reason="GATEWAY_TIMEOUT",
        failure_code="GATEWAY_TIMEOUT",
        customer_id="cust_inv_001",
        previous_payment_count=2,
        previous_success_count=1,
        previous_failure_count=1,
        previous_recovery_count=0,
        previous_retry_success=0,
        previous_payment_link_success=0,
        hour_of_day=10,
        day_of_week=2,
        is_weekend=False,
        candidate_actions=list(SimulatedActionType),
    )

    legit_record = ModelInputRecord(
        record_id="rec_inv_001",
        dataset_type=DatasetType.BENCHMARK,
        dataset_version="bench-v1",
        scenario_id="sc_inv_001",
        generation_seed=1701,
        scenario_version="scenario-v1",
        configuration_version="config-v1",
        feature_schema_version="feature-schema-v1",
        features=feats,
    )

    probs = {
        DecisionAction.RETRY: 0.85,
        DecisionAction.PAYMENT_LINK: 0.50,
        DecisionAction.OUTREACH: 0.40,
        DecisionAction.ESCALATE: 0.10,
        DecisionAction.STOP: 0.0,
    }
    predictions: dict[DecisionAction, OutcomePrediction] = {}
    for act, p in probs.items():
        predictions[act] = OutcomePrediction(
            prediction_id=f"pred_{act.value.lower()}",
            record_id="rec_inv_001",
            scenario_id="sc_inv_001",
            action=act,
            model_name="OutcomeModel",
            model_version="v1.0",
            dataset_version="bench-v1",
            feature_schema_version="feature-schema-v1",
            predicted_success_probability=p,
            predicted_outcome_state=(
                PredictedOutcomeState.SUCCESS
                if p >= 0.5
                else PredictedOutcomeState.FAILURE
            ),
            predicted_recovered_amount=int(50000 * p),
            confidence=max(p, 1.0 - p),
            uncertainty_state=PredictionUncertaintyState.HIGH_CONFIDENCE,
        )

    engine = EconomicDecisionEngine()

    # Legitimate decision
    clean_decision = engine.decide(legit_record, None, predictions)
    assert clean_decision.selected_action == DecisionAction.RETRY

    # Attempt oracle injection (oracle suggests ESCALATE as ground truth)
    injected_dict = legit_record.model_dump()
    injected_dict["oracle_action"] = "ESCALATE"
    injected_dict["oracle_recovery_amount"] = 50000
    injected_dict["counterfactual_outcomes"] = {"RETRY": False, "ESCALATE": True}
    injected_record = ModelInputRecord.model_validate(injected_dict)

    attack_decision = engine.decide(injected_record, None, predictions)

    # Invariance check: Decision engine must ignore injected fields completely
    assert (
        attack_decision.selected_action
        == clean_decision.selected_action
        == DecisionAction.RETRY
    )
    assert (
        attack_decision.expected_recovery_value
        == clean_decision.expected_recovery_value
    )

    # Zero leakage check
    out_json = attack_decision.model_dump_json()
    assert "oracle_action" not in out_json
    assert "counterfactual_outcomes" not in out_json

    assert_zero_truth_leakage(attack_decision.model_dump())
