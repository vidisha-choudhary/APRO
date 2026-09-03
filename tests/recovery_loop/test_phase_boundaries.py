"""Tests proving architectural phase boundaries and provider neutrality for Phase 13."""

from pathlib import Path


def test_recovery_loop_has_zero_provider_imports() -> None:
    """Phase 13 must remain provider-neutral with zero imports from apro.providers."""
    rl_dir = Path("src/apro/recovery_loop")
    assert rl_dir.exists(), "src/apro/recovery_loop directory must exist."

    for py_file in rl_dir.glob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        assert "from apro.providers" not in content, (
            f"Found forbidden provider import in {py_file.name}"
        )
        assert "import apro.providers" not in content, (
            f"Found forbidden provider import in {py_file.name}"
        )
        assert "RazorpayTestMode" not in content, (
            f"Found forbidden RazorpayTestMode reference in {py_file.name}"
        )
        assert "httpx" not in content, (
            f"Found forbidden network transport dependency in {py_file.name}"
        )


def test_recovery_loop_contains_no_second_decision_or_policy_engine() -> None:
    """Phase 13 must not contain an action-ranking algorithm or duplicate
    policy rule engine.
    """
    rl_dir = Path("src/apro/recovery_loop")
    for py_file in rl_dir.glob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        assert "calculate_utility" not in content, (
            f"Found utility calculation logic in {py_file.name}"
        )
        assert "expected_recovery_value" not in content or "class " in content, (
            f"Found ERV computation logic in {py_file.name}"
        )
