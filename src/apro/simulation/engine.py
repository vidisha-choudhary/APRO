"""Independent outcome engine for APRO Phase 5 synthetic scenarios."""

import hashlib
import random
from typing import Any

from apro.simulation.config import SimulationConfig
from apro.simulation.enums import (
    SimulatedActionType,
    SimulatedOutcomeStatus,
)
from apro.simulation.models import (
    SimulatedActionOutcome,
    SimulationScenario,
)


def compute_outcome_seed_key(
    generation_seed: int,
    scenario_id: str,
    action: SimulatedActionType,
    outcome_seed: int | None = None,
) -> str:
    """Generate a deterministic seed key for action outcome evaluation."""
    seed_suffix = "default" if outcome_seed is None else outcome_seed
    return f"{generation_seed}_{scenario_id}_{action.value}_{seed_suffix}"


def evaluate_action_outcome_from_probability(
    true_prob: float,
    action: SimulatedActionType,
    amount: int,
    generation_seed: int,
    scenario_id: str,
    outcome_seed: int | None = None,
) -> SimulatedActionOutcome:
    """Core deterministic outcome computation used across simulation components."""
    seed_key = compute_outcome_seed_key(
        generation_seed, scenario_id, action, outcome_seed
    )
    seed_int = int(hashlib.sha256(seed_key.encode("utf-8")).hexdigest()[:8], 16)
    rng = random.Random(seed_int)

    roll = rng.random()

    if action == SimulatedActionType.STOP:
        status = SimulatedOutcomeStatus.FAILURE
        recovered = 0
        duration = 0
        fail_reason: str | None = "Recovery stopped by decision"
        meta: dict[str, Any] = {"terminal_action": True}

    elif action == SimulatedActionType.ESCALATE:
        if roll < true_prob:
            status = SimulatedOutcomeStatus.PENDING
            recovered = 0
            duration = rng.randint(300, 3600)
            fail_reason = None
            meta = {"escalation_routed": True}
        else:
            status = SimulatedOutcomeStatus.FAILURE
            recovered = 0
            duration = rng.randint(60, 600)
            fail_reason = "Escalation failed or declined"
            meta = {"escalation_routed": False}

    else:
        # RETRY, PAYMENT_LINK, OUTREACH
        if roll < true_prob:
            status = SimulatedOutcomeStatus.SUCCESS
            recovered = amount
            if action == SimulatedActionType.RETRY:
                duration = rng.randint(2, 30)
            elif action == SimulatedActionType.PAYMENT_LINK:
                duration = rng.randint(300, 3600)
            else:  # OUTREACH
                duration = rng.randint(600, 7200)
            fail_reason = None
            meta = {"action_type": action.value}
        else:
            status = SimulatedOutcomeStatus.FAILURE
            recovered = 0
            if action == SimulatedActionType.RETRY:
                duration = rng.randint(2, 15)
            elif action == SimulatedActionType.PAYMENT_LINK:
                duration = rng.randint(3600, 86400)
            else:  # OUTREACH
                duration = rng.randint(3600, 43200)
            fail_reason = f"Simulated {action.value} failure"
            meta = {"action_type": action.value}

    return SimulatedActionOutcome(
        scenario_id=scenario_id,
        action=action,
        status=status,
        recovered_amount=recovered,
        attempt_duration_seconds=duration,
        failure_reason=fail_reason,
        metadata=meta,
    )


class OutcomeEngine:
    """Evaluates chosen action outcomes against hidden ground truth.

    INVARIANT:
    Outcome = f(underlying scenario, chosen action, controlled randomness)
    The outcome engine strictly does NOT accept APRO predictions, decision scores,
    expected recovery values, or recommendation state.
    """

    def __init__(self, config: SimulationConfig | None = None) -> None:
        self._config = config or SimulationConfig()

    def generate_outcome(
        self,
        scenario: SimulationScenario,
        chosen_action: SimulatedActionType,
        outcome_seed: int | None = None,
    ) -> SimulatedActionOutcome:
        """Deterministically determine the outcome of a chosen action on a scenario."""
        if chosen_action not in scenario.observable_state.candidate_actions:
            msg = (
                f"Chosen action '{chosen_action}' is not in candidate actions: "
                f"{scenario.observable_state.candidate_actions}"
            )
            raise ValueError(msg)

        true_prob = scenario.hidden_state.true_action_probabilities.get(
            chosen_action, 0.0
        )
        return evaluate_action_outcome_from_probability(
            true_prob=true_prob,
            action=chosen_action,
            amount=scenario.observable_state.payment.amount,
            generation_seed=scenario.generation_seed,
            scenario_id=scenario.scenario_id,
            outcome_seed=outcome_seed,
        )
