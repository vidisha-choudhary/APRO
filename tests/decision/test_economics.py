"""Unit tests for economic configuration, cost structures, and ERV calculations."""

import pytest

from apro.decision.economics import (
    EconomicConfiguration,
    get_default_action_costs,
)
from apro.decision.enums import RECOVERY_ACTION_ORDER, RecoveryAction
from apro.decision.models import ActionCostConfig


def test_default_action_costs_coverage() -> None:
    """Verify default action costs exist for all 5 recovery actions."""
    costs = get_default_action_costs()
    for act in RECOVERY_ACTION_ORDER:
        assert act in costs
        cfg = costs[act]
        assert cfg.action_cost >= 0
        assert cfg.operational_cost >= 0
        assert cfg.customer_friction_cost >= 0
        assert cfg.risk_penalty >= 0
        assert cfg.total_cost == (
            cfg.action_cost
            + cfg.operational_cost
            + cfg.customer_friction_cost
            + cfg.risk_penalty
        )


def test_compute_gross_recovery_and_erv() -> None:
    """Verify expected gross recovery and ERV calculation in minor units (paise)."""
    econ = EconomicConfiguration()

    # Case 1: Standard positive probability and recovery
    gross = econ.compute_gross_recovery(
        predicted_success_probability=0.80,
        predicted_recovered_amount=500000,  # Rs 5,000.00
    )
    assert gross == 400000  # Rs 4,000.00

    # ERV for RETRY: Total cost is 500+200+300+200 = 1200 paise (Rs 12.00)
    g, erv, c_cfg = econ.compute_erv(
        action=RecoveryAction.RETRY,
        predicted_success_probability=0.80,
        predicted_recovered_amount=500000,
    )
    assert g == 400000
    assert c_cfg.total_cost == 1200
    assert erv == 400000 - 1200

    # Case 2: Zero or negative probability
    assert econ.compute_gross_recovery(0.0, 500000) == 0
    assert econ.compute_gross_recovery(-0.5, 500000) == 0
    assert econ.compute_gross_recovery(0.5, 0) == 0


def test_missing_action_cost_validation() -> None:
    """Verify validate_action_coverage raises ValueError on incomplete cost map."""
    incomplete_costs = {
        RecoveryAction.STOP: ActionCostConfig(),
    }
    econ = EconomicConfiguration(costs_by_action=incomplete_costs)
    with pytest.raises(ValueError, match="Missing cost configuration"):
        econ.validate_action_coverage()
