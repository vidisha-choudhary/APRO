"""Policy constraints and candidate action eligibility for APRO Phase 9."""

from pydantic import BaseModel, ConfigDict, Field

from apro.dataset.models import ModelInputRecord
from apro.decision.enums import (
    POLICY_CONFIG_SCHEMA_VERSION,
    RECOVERY_ACTION_ORDER,
    RecoveryAction,
)
from apro.decision.models import ActionEligibility
from apro.diagnosis.enums import DiagnosisCategory
from apro.diagnosis.models import DiagnosisResult


class PolicyConfiguration(BaseModel):
    """Declarative safety and governance policy parameters."""

    model_config = ConfigDict(frozen=True)

    policy_version: str = Field(default=POLICY_CONFIG_SCHEMA_VERSION)
    max_retries: int = Field(default=3, ge=1)
    max_total_interventions: int = Field(default=5, ge=1)
    high_value_threshold: int = Field(default=10000000, ge=0)  # Rs 1,00,000 in paise
    min_outreach_amount: int = Field(default=50000, ge=0)  # Rs 500.00 in paise
    disallow_retry_on_terminal_failures: bool = True
    disallow_outreach_on_low_value: bool = True


class PolicyEligibilityEngine:
    """Evaluates candidate actions against policy constraints prior to economics."""

    def __init__(
        self,
        config: PolicyConfiguration | None = None,
    ) -> None:
        self._config = config or PolicyConfiguration()

    @property
    def config(self) -> PolicyConfiguration:
        return self._config

    def evaluate_action_eligibility(
        self,
        model_input: ModelInputRecord,
        action: RecoveryAction,
        diagnosis_result: DiagnosisResult | None = None,
    ) -> ActionEligibility:
        """Determine whether a candidate action is permissible under policy."""
        feats = model_input.features
        p_amount = feats.payment_amount
        attempt_cnt = feats.attempt_count
        tot_interventions = feats.previous_recovery_count

        # STOP and ESCALATE are baseline safety fallback actions
        if action == RecoveryAction.STOP:
            return ActionEligibility(
                action=action,
                is_eligible=True,
                reason="Stop is always a permissible safe fallback.",
                policy_rule="RULE_ALWAYS_ELIGIBLE_STOP",
            )

        if action == RecoveryAction.ESCALATE:
            return ActionEligibility(
                action=action,
                is_eligible=True,
                reason="Escalate is always permissible for risk mitigation.",
                policy_rule="RULE_ALWAYS_ELIGIBLE_ESCALATE",
            )

        # 1. High-Value Transaction Guardrail
        if p_amount >= self._config.high_value_threshold and action in (
            RecoveryAction.RETRY,
            RecoveryAction.OUTREACH,
        ):
            amt_rs = p_amount / 100
            lim_rs = self._config.high_value_threshold / 100
            return ActionEligibility(
                action=action,
                is_eligible=False,
                reason=(
                    f"Transaction amount Rs {amt_rs:.2f} exceeds high-value "
                    f"threshold (Rs {lim_rs:.2f}). "
                    "Automated retry/outreach blocked."
                ),
                policy_rule="RULE_H11_HIGH_VALUE_THRESHOLD",
            )

        # 2. Maximum Total Interventions Guardrail
        if tot_interventions >= self._config.max_total_interventions and action in (
            RecoveryAction.RETRY,
            RecoveryAction.PAYMENT_LINK,
            RecoveryAction.OUTREACH,
        ):
            return ActionEligibility(
                action=action,
                is_eligible=False,
                reason=(
                    f"Total interventions ({tot_interventions}) reached limit "
                    f"({self._config.max_total_interventions})."
                ),
                policy_rule="RULE_H9_MAX_TOTAL_INTERVENTIONS",
            )

        # 3. Action-Specific Rules: RETRY
        if action == RecoveryAction.RETRY:
            if attempt_cnt >= self._config.max_retries:
                return ActionEligibility(
                    action=action,
                    is_eligible=False,
                    reason=(
                        f"Attempt count ({attempt_cnt}) reached maximum retry limit "
                        f"({self._config.max_retries})."
                    ),
                    policy_rule="RULE_H7_MAX_RETRY_LIMIT",
                )

            # Diagnosis Category Restrictions on RETRY
            if (
                self._config.disallow_retry_on_terminal_failures
                and diagnosis_result is not None
            ):
                diag_cat = diagnosis_result.predicted_category
                if diag_cat in (
                    DiagnosisCategory.CUSTOMER_SIDE_FAILURE,
                    DiagnosisCategory.AUTHENTICATION_FAILURE,
                    DiagnosisCategory.PAYMENT_METHOD_FAILURE,
                ):
                    return ActionEligibility(
                        action=action,
                        is_eligible=False,
                        reason=(
                            f"Retry prohibited for category '{diag_cat.value}'. "
                            "Requires customer re-auth or alternative method."
                        ),
                        policy_rule="RULE_DIAGNOSIS_RETRY_RESTRICTION",
                    )

        # 4. Action-Specific Rules: OUTREACH
        if (
            action == RecoveryAction.OUTREACH
            and self._config.disallow_outreach_on_low_value
            and p_amount < self._config.min_outreach_amount
        ):
            amt_rs = p_amount / 100
            min_rs = self._config.min_outreach_amount / 100
            return ActionEligibility(
                action=action,
                is_eligible=False,
                reason=(
                    f"Outreach prohibited for low-value transaction "
                    f"Rs {amt_rs:.2f} (minimum required: Rs {min_rs:.2f})."
                ),
                policy_rule="RULE_LOW_VALUE_OUTREACH_RESTRICTION",
            )

        return ActionEligibility(
            action=action,
            is_eligible=True,
            reason=f"Action '{action.value}' passed all policy constraints.",
            policy_rule="RULE_POLICY_PERMITTED",
        )

    def evaluate_all_actions(
        self,
        model_input: ModelInputRecord,
        diagnosis_result: DiagnosisResult | None = None,
    ) -> dict[RecoveryAction, ActionEligibility]:
        """Evaluate eligibility across all 5 actions in deterministic order."""
        return {
            act: self.evaluate_action_eligibility(
                model_input, act, diagnosis_result=diagnosis_result
            )
            for act in RECOVERY_ACTION_ORDER
        }
