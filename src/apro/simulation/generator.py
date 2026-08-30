"""Synthetic scenario generator for APRO Phase 5."""

import random
import uuid
from typing import TypeVar

from apro.simulation.config import SimulationConfig
from apro.simulation.engine import evaluate_action_outcome_from_probability
from apro.simulation.enums import (
    CustomerBehaviorClass,
    RecoverabilityClass,
    ScenarioFamily,
    SimulatedActionType,
    SimulatedOutcomeStatus,
)
from apro.simulation.models import (
    CustomerContext,
    FailureContext,
    HiddenScenarioState,
    ObservableScenarioState,
    PaymentContext,
    SimulationScenario,
    TemporalContext,
)

T = TypeVar("T")


def _sample_categorical(rng: random.Random, dist: dict[T, float]) -> T:
    """Sample an item from a categorical distribution using the provided RNG."""
    choices = list(dist.keys())
    weights = list(dist.values())
    return rng.choices(choices, weights=weights, k=1)[0]


FAMILY_OBSERVABLE_ERRORS: dict[ScenarioFamily, list[tuple[str, str, str | None]]] = {
    ScenarioFamily.TRANSIENT_FAILURE: [
        ("Network error communicating with gateway", "GATEWAY_TIMEOUT", "GATEWAY_504"),
        ("Internal processing timeout", "PROCESSING_TIMEOUT", "SYS_TIMEOUT"),
        ("Temporary connection glitch", "TRANSIENT_NETWORK_ERROR", None),
    ],
    ScenarioFamily.BANK_SIDE_FAILURE: [
        ("Issuing bank technical error", "ISSUER_UNAVAILABLE", "BANK_DOWN"),
        ("Bank network switch failure", "SWITCH_MALFUNCTION", "SWITCH_503"),
        ("Bank response timed out", "BANK_TIMEOUT", "BANK_NO_RESPONSE"),
    ],
    ScenarioFamily.CUSTOMER_SIDE_FAILURE: [
        ("Insufficient account balance", "INSUFFICIENT_FUNDS", "BAL_LOW"),
        ("Exceeded transaction frequency limit", "LIMIT_EXCEEDED", "MAX_TXN_REACHED"),
        ("Payment cancelled by customer", "PAYMENT_CANCELLED", "USER_ABORT"),
    ],
    ScenarioFamily.AUTHENTICATION_FAILURE: [
        ("One-time password expired", "OTP_EXPIRED", "AUTH_OTP_EXP"),
        ("3DS verification failed", "3DS_AUTH_FAILED", "SECURE_AUTH_FAIL"),
        ("Two-factor authentication declined", "2FA_DECLINED", "MFA_REJECT"),
    ],
    ScenarioFamily.PAYMENT_METHOD_FAILURE: [
        ("Card expired or invalid validity date", "EXPIRED_CARD", "CARD_EXPIRED"),
        ("UPI Virtual Payment Address not found", "VPA_NOT_FOUND", "INVALID_VPA"),
        ("Account temporarily restricted", "ACCOUNT_RESTRICTED", "RESTRICTED_MTHD"),
    ],
    ScenarioFamily.GATEWAY_FAILURE: [
        ("Payment gateway rejected request", "ACQUIRER_REJECTED", "ACQ_REJECT_91"),
        ("Payment gateway integration error", "GATEWAY_ERROR", "GW_INTERNAL_500"),
    ],
    ScenarioFamily.TIMEOUT: [
        (
            "Transaction pending authorization expired",
            "TRANSACTION_TIMED_OUT",
            "TXN_EXP_01",
        ),
        ("Payment confirmation expired", "CONFIRMATION_TIMEOUT", "EXP_CONFIRM"),
    ],
    ScenarioFamily.UNKNOWN_FAILURE: [
        ("Payment processing failed", "PAYMENT_FAILED", None),
        ("Generic payment decline", "UNDEFINED_FAILURE", "GENERIC_99"),
    ],
}


class ScenarioGenerator:
    """Generates synthetic recovery scenarios with ground truth and observable views."""

    def __init__(self, config: SimulationConfig | None = None) -> None:
        self._config = config or SimulationConfig()

    @property
    def config(self) -> SimulationConfig:
        """Get the active simulator configuration."""
        return self._config

    def generate(self, seed: int, scenario_id: str | None = None) -> SimulationScenario:
        """Generate a single deterministic synthetic scenario using the given seed."""
        rng = random.Random(seed)

        generated_scen_id = f"scen_{uuid.UUID(int=rng.getrandbits(128)).hex[:12]}"
        scen_id = scenario_id or generated_scen_id
        cust_id = f"cust_{uuid.UUID(int=rng.getrandbits(128)).hex[:8]}"
        pay_id = f"pay_sim_{uuid.UUID(int=rng.getrandbits(128)).hex[:8]}"

        # Sample scenario dimensions
        family = _sample_categorical(rng, self._config.family_distribution)
        recoverability = _sample_categorical(
            rng, self._config.recoverability_distribution
        )
        behavior = _sample_categorical(rng, self._config.behavior_distribution)
        value_tier = _sample_categorical(rng, self._config.value_tier_distribution)
        method = _sample_categorical(rng, self._config.method_distribution)
        difficulty = _sample_categorical(rng, self._config.difficulty_distribution)

        # 1. Payment amount
        min_amt, max_amt = self._config.amount_ranges[value_tier]
        raw_amt = rng.randint(min_amt, max_amt)
        amount = max(min_amt, (raw_amt // 100) * 100)

        # 2. Customer history based on behavior class
        if behavior == CustomerBehaviorClass.HIGHLY_RESPONSIVE:
            succ = rng.randint(5, 25)
            fail = rng.randint(0, 2)
            rec = rng.randint(1, 5) if fail > 0 else 0
            retry_succ = rng.randint(0, rec)
            link_succ = rec - retry_succ
        elif behavior == CustomerBehaviorClass.NORMAL:
            succ = rng.randint(2, 10)
            fail = rng.randint(1, 3)
            rec = rng.randint(0, fail)
            retry_succ = rng.randint(0, rec)
            link_succ = rec - retry_succ
        elif behavior == CustomerBehaviorClass.LOW_RESPONSIVENESS:
            succ = rng.randint(0, 3)
            fail = rng.randint(2, 6)
            rec = rng.randint(0, 1)
            retry_succ = rec
            link_succ = 0
        else:  # UNPREDICTABLE
            succ = rng.randint(0, 15)
            fail = rng.randint(0, 8)
            rec = rng.randint(0, fail) if fail > 0 else 0
            retry_succ = rng.randint(0, rec)
            link_succ = rec - retry_succ

        customer_ctx = CustomerContext(
            customer_id=cust_id,
            previous_payment_count=succ + fail,
            previous_success_count=succ,
            previous_failure_count=fail,
            previous_recovery_count=rec,
            previous_retry_success=retry_succ,
            previous_payment_link_success=link_succ,
        )

        # 3. Observable Failure context
        possible_errors = FAMILY_OBSERVABLE_ERRORS.get(
            family, FAMILY_OBSERVABLE_ERRORS[ScenarioFamily.UNKNOWN_FAILURE]
        )
        reason, code, decline = rng.choice(possible_errors)
        failure_ctx = FailureContext(
            failure_reason=reason,
            failure_code=code,
            decline_code=decline,
        )

        # 4. Temporal context
        hour = rng.randint(0, 23)
        dow = rng.randint(0, 6)
        is_weekend = dow in (5, 6)
        time_since_prev_attempt = rng.randint(30, 3600)
        time_since_prev_succ = rng.randint(3600, 86400 * 30) if succ > 0 else None

        temporal_ctx = TemporalContext(
            hour_of_day=hour,
            day_of_week=dow,
            is_weekend=is_weekend,
            time_since_previous_attempt_seconds=time_since_prev_attempt,
            time_since_previous_successful_payment_seconds=time_since_prev_succ,
        )

        payment_ctx = PaymentContext(
            payment_id=pay_id,
            amount=amount,
            currency="INR",
            method=method,
            attempt_count=rng.randint(1, 3),
        )

        # 5. Candidate actions
        candidate_actions = [
            SimulatedActionType.RETRY,
            SimulatedActionType.PAYMENT_LINK,
            SimulatedActionType.OUTREACH,
            SimulatedActionType.STOP,
            SimulatedActionType.ESCALATE,
        ]

        # 6. Hidden true action probabilities & potential outcomes
        true_action_probs: dict[SimulatedActionType, float] = {}
        potential_outcomes: dict[SimulatedActionType, SimulatedOutcomeStatus] = {}

        noise_scale = self._config.difficulty_noise[difficulty]

        for action in candidate_actions:
            if (
                recoverability == RecoverabilityClass.NON_RECOVERABLE
                or action == SimulatedActionType.STOP
            ):
                prob = 0.0
            else:
                base_p = self._config.base_action_effectiveness[recoverability][action]
                fam_mod = self._config.family_action_modifiers[family][action]
                beh_mod = self._config.behavior_action_modifiers[behavior][action]
                noise = rng.uniform(-noise_scale, noise_scale)
                prob = max(0.0, min(1.0, base_p + fam_mod + beh_mod + noise))

            true_action_probs[action] = round(prob, 4)

            # Unified potential outcome calculation (Correction C)
            outcome = evaluate_action_outcome_from_probability(
                true_prob=true_action_probs[action],
                action=action,
                amount=amount,
                generation_seed=seed,
                scenario_id=scen_id,
                outcome_seed=None,
            )
            potential_outcomes[action] = outcome.status

        # 7. Hidden state construction
        latent_intent = round(rng.uniform(0.1, 0.95), 3)
        latent_bank = round(rng.uniform(0.1, 0.95), 3)

        hidden_state = HiddenScenarioState(
            true_failure_mechanism=f"{family.value}_MECHANISM_UNDERLYING",
            recoverability=recoverability,
            customer_behavior=behavior,
            latent_customer_intent=latent_intent,
            latent_bank_condition=latent_bank,
            scenario_difficulty=difficulty,
            true_action_probabilities=true_action_probs,
            potential_outcomes=potential_outcomes,
        )

        observable_state = ObservableScenarioState(
            scenario_id=scen_id,
            customer=customer_ctx,
            payment=payment_ctx,
            failure=failure_ctx,
            temporal=temporal_ctx,
            candidate_actions=candidate_actions,
        )

        return SimulationScenario(
            scenario_id=scen_id,
            generation_seed=seed,
            scenario_version=self._config.scenario_version,
            configuration_version=self._config.configuration_version,
            scenario_family=family,
            observable_state=observable_state,
            hidden_state=hidden_state,
        )
