"""Tests for Scenario 1: Policy Bypass and Approval Boundary Enforcement."""

import pytest

from apro.adversarial.assertions import assert_action_unauthorized
from apro.adversarial.enums import AttackDisposition
from apro.adversarial.executor import AdversarialAttackExecutor
from apro.adversarial.generators import generate_policy_bypass_cases


@pytest.mark.asyncio
async def test_scenario_1_policy_bypass_all_vectors_blocked(
    adversarial_executor: AdversarialAttackExecutor,
) -> None:
    """Scenario 1: All policy bypass attack vectors are rejected before provider dispatch."""
    cases = generate_policy_bypass_cases(seed=1701, count=5)

    for case in cases:
        result = await adversarial_executor.execute_case(case)
        assert_action_unauthorized(result)
        assert result.passed is True
        assert result.disposition in (
            AttackDisposition.BLOCKED,
            AttackDisposition.REJECTED,
        )

    assert adversarial_executor.unauthorized_execution_count == 0
