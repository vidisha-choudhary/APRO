"""Tests for Scenario 2: Stale Decision and Policy Authority Replay."""

import pytest

from apro.adversarial.assertions import assert_stale_authority_rejected
from apro.adversarial.enums import AttackDisposition
from apro.adversarial.executor import AdversarialAttackExecutor
from apro.adversarial.generators import generate_stale_authority_cases


@pytest.mark.asyncio
async def test_scenario_2_stale_authority_rejected(
    adversarial_executor: AdversarialAttackExecutor,
) -> None:
    """Scenario 2: Stale decision and policy authorities are rejected when case/payment state advances."""
    cases = generate_stale_authority_cases(seed=1701, count=5)

    for case in cases:
        result = await adversarial_executor.execute_case(case)
        assert_stale_authority_rejected(result)
        assert result.passed is True
        assert result.disposition == AttackDisposition.REJECTED
