"""Tests verifying phase boundary isolation and zero upstream coupling."""

from pathlib import Path


def test_upstream_modules_do_not_import_providers() -> None:
    """Verify upstream domain, policy, decision do not import providers."""
    src_root = Path("src/apro")
    upstream_dirs = [
        "domain",
        "policy",
        "decision",
        "diagnosis",
        "recovery_prediction",
        "dataset",
    ]

    for d in upstream_dirs:
        pkg_dir = src_root / d
        if not pkg_dir.exists():
            continue
        for py_file in pkg_dir.glob("**/*.py"):
            content = py_file.read_text(encoding="utf-8")
            assert "apro.providers" not in content, (
                f"Forbidden provider import found in upstream file: {py_file}"
            )
            assert "RazorpayTestModeClient" not in content, (
                f"Forbidden provider client reference in upstream file: {py_file}"
            )


def test_no_adaptive_loop_in_providers() -> None:
    """Verify provider code does not implement autonomous replanning or retry loops."""
    provider_dir = Path("src/apro/providers")
    for py_file in provider_dir.glob("**/*.py"):
        content = py_file.read_text(encoding="utf-8")
        assert "select_action" not in content
        assert "replan" not in content
        assert "PolicyEngine" not in content
