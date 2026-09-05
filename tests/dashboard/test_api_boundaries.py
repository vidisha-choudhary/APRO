"""Boundary tests proving Phase 16 dashboard is strictly read-only with zero mutation capabilities."""

import ast
from pathlib import Path

from fastapi import APIRouter

from apro.dashboard.router import router


def test_dashboard_has_zero_post_put_patch_delete_routes() -> None:
    """AC-06, AC-12, AC-69: Test dashboard router contains strictly GET routes."""
    assert isinstance(router, APIRouter)

    for route in router.routes:
        methods = getattr(route, "methods", set())
        assert methods.issubset({"GET", "HEAD", "OPTIONS"}), (
            f"Route {getattr(route, 'path', '')} has non-GET methods: {methods}"
        )


def test_dashboard_ast_boundary_inspection() -> None:
    """AC-62, AC-63, AC-64, AC-65, AC-66, AC-67, AC-68: Static AST inspection of dashboard source."""
    dashboard_dir = Path("src/apro/dashboard")
    forbidden_imports = {
        "EconomicDecisionEngine",
        "PolicyEngine",
        "RazorpayProviderTransport",
        "RecoveryLoopController",
        "ActionExecutor",
    }

    for py_file in dashboard_dir.glob("*.py"):
        with open(py_file, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(py_file))

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom | ast.Import):
                for alias in node.names:
                    assert alias.name not in forbidden_imports, (
                        f"Forbidden engine import '{alias.name}' found in {py_file}"
                    )
