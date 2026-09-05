"""Tests for Phase 17 Architecture Boundaries, Non-Duplication, and Zero Live External Calls."""

import ast
from pathlib import Path

import pytest

FORBIDDEN_EXTERNAL_NETWORKING = {
    "requests",
    "aiohttp",
    "urllib.request",
    "socket",
}


def test_ast_boundary_no_forbidden_networking() -> None:
    """Amendment 3: AST verification proving zero live external network modules in src/apro/adversarial/."""
    adv_dir = Path("src/apro/adversarial")
    py_files = list(adv_dir.glob("*.py"))

    assert len(py_files) > 0

    violations = []
    for fpath in py_files:
        tree = ast.parse(fpath.read_text(encoding="utf-8"), filename=str(fpath))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in FORBIDDEN_EXTERNAL_NETWORKING:
                        violations.append(f"{fpath.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod in FORBIDDEN_EXTERNAL_NETWORKING or any(
                    mod.startswith(f"{fn}.") for fn in FORBIDDEN_EXTERNAL_NETWORKING
                ):
                    violations.append(f"{fpath.name}: from {mod} import ...")

    assert not violations, f"Forbidden networking imports found: {violations}"


def test_ast_boundary_no_unconditional_pass_placeholders() -> None:
    """Acceptance invariant: Prove zero unconditional PASS placeholders in src/apro/adversarial/."""
    adv_dir = Path("src/apro/adversarial")
    py_files = list(adv_dir.glob("*.py"))

    for fpath in py_files:
        tree = ast.parse(fpath.read_text(encoding="utf-8"), filename=str(fpath))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and not node.name.startswith("__")
                and len(node.body) == 1
                and isinstance(node.body[0], ast.Pass)
            ):
                pytest.fail(
                    f"Unconditional 'pass' placeholder in function {fpath.name}:{node.name}"
                )


def test_ast_boundary_zero_duplicate_business_authorities() -> None:
    """Phase 17 must NOT duplicate DecisionEngine, PolicyEngine, Evaluator, or Provider authorities."""
    adv_dir = Path("src/apro/adversarial")
    py_files = list(adv_dir.glob("*.py"))

    for fpath in py_files:
        tree = ast.parse(fpath.read_text(encoding="utf-8"), filename=str(fpath))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                assert not node.name.endswith("DecisionEngine"), (
                    f"Duplicate engine: {node.name}"
                )
                assert not node.name.endswith("PolicyEngine"), (
                    f"Duplicate engine: {node.name}"
                )
                assert not node.name.endswith("Evaluator"), (
                    f"Duplicate evaluator: {node.name}"
                )
                assert not node.name.endswith("ProviderTransport"), (
                    f"Duplicate transport: {node.name}"
                )


def test_ast_boundary_no_hardcoded_db_credentials() -> None:
    """Security Invariant: Prove zero hardcoded database credentials or URLs in executable code."""
    import re

    check_paths = [
        *Path("src/apro/adversarial").glob("*.py"),
        *Path("tests/adversarial").glob("*.py"),
        Path("scripts/run_phase_17_acceptance.py"),
    ]

    uri_cred_pattern = re.compile(r"://" + r"[^/\s:@]+" + r":" + r"[^/\s:@]+@")
    db_scheme_pattern = re.compile(
        r"^(?:postgres(?:ql)?|mysql|mariadb)(?:\+[a-zA-Z0-9_]+)?://" + r"[^/\s]+"
    )

    violations = []
    for fpath in check_paths:
        if not fpath.exists():
            continue
        tree = ast.parse(fpath.read_text(encoding="utf-8"), filename=str(fpath))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                val = node.value.strip()
                if len(val) < 10:
                    continue
                if uri_cred_pattern.search(val):
                    violations.append(
                        f"{fpath.name}:{node.lineno}: (credential pattern in URI)"
                    )
                elif db_scheme_pattern.search(val):
                    violations.append(
                        f"{fpath.name}:{node.lineno}: (hardcoded DB URL scheme)"
                    )

    assert not violations, f"Hardcoded DB credentials/URLs found: {violations}"


def test_ast_boundary_no_imports_from_tests() -> None:
    """Production invariant: Prove zero imports from tests.* inside src/apro/adversarial/."""
    adv_dir = Path("src/apro/adversarial")
    py_files = list(adv_dir.glob("*.py"))

    violations = []
    for fpath in py_files:
        tree = ast.parse(fpath.read_text(encoding="utf-8"), filename=str(fpath))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "tests" or alias.name.startswith("tests."):
                        violations.append(f"{fpath.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod == "tests" or mod.startswith("tests."):
                    violations.append(f"{fpath.name}: from {mod} import ...")

    assert not violations, (
        f"Forbidden tests imports found in src/apro/adversarial: {violations}"
    )
