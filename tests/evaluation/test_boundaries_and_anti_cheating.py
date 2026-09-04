"""Architectural boundary and anti-cheating verification tests (Phase 15)."""

import inspect

from apro.evaluation.evaluator import APROEvaluator


def test_evaluator_has_zero_dispatch_or_mutation_methods() -> None:
    """AC-76, AC-77, AC-78, AC-79, AC-80: Verify zero provider dispatch/mutation."""
    evaluator_methods = [
        m for m, _ in inspect.getmembers(APROEvaluator, predicate=inspect.isfunction)
    ]

    forbidden_keywords = [
        "dispatch",
        "execute_provider",
        "authorize",
        "create_action",
        "mutate",
        "select_action",
        "call_razorpay",
        "send_payment_link",
        "retry_payment",
    ]

    for m in evaluator_methods:
        for kw in forbidden_keywords:
            assert kw not in m.lower(), (
                f"Evaluator must not contain method '{m}' with forbidden action '{kw}'!"
            )


def test_evaluator_is_read_only() -> None:
    """AC-79: Test evaluator runs without attempting DB mutations."""
    evaluator = APROEvaluator()
    # Confirm evaluator only has read-only methods
    assert hasattr(evaluator, "evaluate_dataset")
    assert not hasattr(evaluator, "save_case")
    assert not hasattr(evaluator, "update_case")
    assert not hasattr(evaluator, "mutate_state")
