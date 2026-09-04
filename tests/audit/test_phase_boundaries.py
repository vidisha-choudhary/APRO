"""Tests verifying strict Phase 14 observational boundaries."""

import inspect

import apro.audit
import apro.audit.reconstruction
import apro.audit.service


def test_audit_module_has_no_action_selection_engine() -> None:
    """Audit module does not contain any action selection or ranking logic."""
    src = inspect.getsource(apro.audit.service)
    assert "class EconomicDecisionEngine" not in src
    assert "def calculate_erv" not in src
    assert "def rank_actions" not in src


def test_audit_module_has_no_policy_engine() -> None:
    """Audit module does not contain policy rules or rule evaluation logic."""
    src = inspect.getsource(apro.audit.service)
    assert "class PolicyEngine" not in src
    assert "def evaluate_policy" not in src
    assert "def evaluate_rule" not in src


def test_audit_module_has_no_provider_transport() -> None:
    """Audit module does not contain direct Razorpay/HTTP transport logic."""
    src = inspect.getsource(apro.audit.service)
    assert "class RazorpayProviderAdapter" not in src
    assert "def dispatch_payment_link" not in src
    assert "import httpx" not in src
