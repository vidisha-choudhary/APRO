"""Unit tests verifying isolation from hidden simulator truth and evaluation labels."""

import inspect

from apro.decision.engine import EconomicDecisionEngine


def test_decision_engine_signature_has_no_oracle_leakage() -> None:
    """Verify decide() signature accepts only observable context and predictions."""
    sig = inspect.signature(EconomicDecisionEngine.decide)
    param_names = list(sig.parameters.keys())

    # Oracle ground truth, potential outcomes, and truth records MUST NOT be parameters
    forbidden_tokens = [
        "truth",
        "oracle",
        "potential_outcomes",
        "simulation",
        "ground_truth",
        "evaluation_truth",
    ]
    for param in param_names:
        for forbidden in forbidden_tokens:
            assert forbidden not in param.lower(), (
                f"Parameter '{param}' in decide() violates decision isolation."
            )
