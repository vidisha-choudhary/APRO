from abc import ABC, abstractmethod

from apro.dataset.enums import DatasetType
from apro.dataset.models import GovernedDataset, ModelInputRecord
from apro.evaluation.config import EvaluationConfig
from apro.evaluation.enums import (
    BaselineType,
    MetricComparisonLabel,
)
from apro.evaluation.models import (
    BaselineComparisonResult,
    BenchmarkCaseRecord,
    PrimaryKPISet,
)
from apro.simulation.enums import (
    SimulatedActionType,
    SimulatedOutcomeStatus,
)


class EvaluationBaseline(ABC):
    """Abstract interface for Phase 15 evaluation-only baselines."""

    @property
    @abstractmethod
    def baseline_type(self) -> BaselineType:
        """Type enum of the baseline."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable baseline name."""

    @property
    def version(self) -> str:
        """Baseline implementation version."""
        return "1.0.0"

    @abstractmethod
    def evaluate_case(
        self,
        record: BenchmarkCaseRecord,
        config: EvaluationConfig,
    ) -> tuple[bool, int, int]:
        """Evaluate a case under this baseline policy."""


class NoInterventionBaseline(EvaluationBaseline):
    """Baseline 0 — Always select STOP (no recovery action attempted)."""

    @property
    def baseline_type(self) -> BaselineType:
        return BaselineType.NO_INTERVENTION

    @property
    def name(self) -> str:
        return "No Intervention"

    def evaluate_case(
        self,
        record: BenchmarkCaseRecord,
        config: EvaluationConfig,
    ) -> tuple[bool, int, int]:
        _ = record
        cost = config.cost_model.stop_cost
        return False, 0, cost


class FixedRetryBaseline(EvaluationBaseline):
    """Baseline 1 — Always attempt a single retry where eligible."""

    def __init__(self, max_retries: int = 1) -> None:
        self.max_retries = max_retries

    @property
    def baseline_type(self) -> BaselineType:
        return BaselineType.FIXED_RETRY

    @property
    def name(self) -> str:
        return "Fixed Retry"

    def evaluate_case(
        self,
        record: BenchmarkCaseRecord,
        config: EvaluationConfig,
    ) -> tuple[bool, int, int]:
        cost = config.cost_model.retry_cost

        if record.offline_truth and record.offline_truth.counterfactual_outcomes:
            cf = record.offline_truth.counterfactual_outcomes.get("RETRY", {})
            status = cf.get("status", "FAILURE")
            if status in ("SUCCESS", "RECOVERED"):
                amt = cf.get("recovered_amount", record.payment_amount)
                return True, min(amt, record.payment_amount), cost

        if (
            record.executions
            and record.executions[0].execution_type == "RETRY"
            and record.outcomes
        ):
            out_type = (
                record.outcomes[0].type.value
                if hasattr(record.outcomes[0].type, "value")
                else str(record.outcomes[0].type)
            )
            if out_type == "RECOVERED":
                amt = record.outcomes[0].amount_recovered
                return True, min(amt, record.payment_amount), cost

        return False, 0, cost


class PaymentLinkBaseline(EvaluationBaseline):
    """Baseline 2 — Always dispatch a payment link where eligible."""

    @property
    def baseline_type(self) -> BaselineType:
        return BaselineType.PAYMENT_LINK

    @property
    def name(self) -> str:
        return "Payment Link"

    def evaluate_case(
        self,
        record: BenchmarkCaseRecord,
        config: EvaluationConfig,
    ) -> tuple[bool, int, int]:
        cost = config.cost_model.payment_link_cost

        if record.offline_truth and record.offline_truth.counterfactual_outcomes:
            cf = record.offline_truth.counterfactual_outcomes.get("PAYMENT_LINK", {})
            status = cf.get("status", "FAILURE")
            if status in ("SUCCESS", "RECOVERED"):
                amt = cf.get("recovered_amount", record.payment_amount)
                return True, min(amt, record.payment_amount), cost

        if (
            record.executions
            and record.executions[0].execution_type == "PAYMENT_LINK"
            and record.outcomes
        ):
            out_type = (
                record.outcomes[0].type.value
                if hasattr(record.outcomes[0].type, "value")
                else str(record.outcomes[0].type)
            )
            if out_type == "RECOVERED":
                amt = record.outcomes[0].amount_recovered
                return True, min(amt, record.payment_amount), cost

        return False, 0, cost


class FixedEscalationBaseline(EvaluationBaseline):
    """Baseline 3 — Always escalate to human operator."""

    @property
    def baseline_type(self) -> BaselineType:
        return BaselineType.FIXED_ESCALATION

    @property
    def name(self) -> str:
        return "Fixed Escalation"

    def evaluate_case(
        self,
        record: BenchmarkCaseRecord,
        config: EvaluationConfig,
    ) -> tuple[bool, int, int]:
        cost = config.cost_model.escalation_cost

        if record.offline_truth and record.offline_truth.counterfactual_outcomes:
            cf = record.offline_truth.counterfactual_outcomes.get("ESCALATE", {})
            status = cf.get("status", "FAILURE")
            if status in ("SUCCESS", "RECOVERED"):
                amt = cf.get("recovered_amount", record.payment_amount)
                return True, min(amt, record.payment_amount), cost

        return False, 0, cost


class OracleUpperBoundBaseline(EvaluationBaseline):
    """Baseline Optional — Oracle counterfactual upper bound (evaluation-only)."""

    @property
    def baseline_type(self) -> BaselineType:
        return BaselineType.ORACLE_UPPER_BOUND

    @property
    def name(self) -> str:
        return "Oracle Upper Bound"

    def evaluate_case(
        self,
        record: BenchmarkCaseRecord,
        config: EvaluationConfig,
    ) -> tuple[bool, int, int]:
        if record.offline_truth and record.offline_truth.ground_truth_recovered:
            best_act = record.offline_truth.ground_truth_best_action or "RETRY"
            cost = config.cost_model.get_action_cost(best_act)
            return True, record.offline_truth.ground_truth_recovered_amount, cost

        return False, 0, 0


def get_baseline_instance(b_type: BaselineType) -> EvaluationBaseline:
    """Factory for evaluation baseline instances."""
    if b_type == BaselineType.NO_INTERVENTION:
        return NoInterventionBaseline()
    if b_type == BaselineType.FIXED_RETRY:
        return FixedRetryBaseline()
    if b_type == BaselineType.PAYMENT_LINK:
        return PaymentLinkBaseline()
    if b_type == BaselineType.FIXED_ESCALATION:
        return FixedEscalationBaseline()
    if b_type == BaselineType.ORACLE_UPPER_BOUND:
        return OracleUpperBoundBaseline()
    return NoInterventionBaseline()


def evaluate_baselines_comparison(
    records: list[BenchmarkCaseRecord],
    config: EvaluationConfig,
    apro_kpis: PrimaryKPISet,
) -> dict[str, BaselineComparisonResult]:
    """Evaluate all configured baselines over the exact same eligible cohort."""
    from apro.evaluation.statistics import (
        compute_paired_bootstrap_ci,
        compute_paired_randomization_p_value,
    )

    results: dict[str, BaselineComparisonResult] = {}
    n = len(records)
    if n == 0:
        return results

    apro_cases_rec: list[int] = []
    apro_cases_net: list[int] = []

    for r in records:
        is_rec = 1 if (r.is_recovered and r.recovered_amount > 0) else 0
        rec_amt = r.recovered_amount if is_rec else 0
        cost = 0
        if r.executions:
            for ex in r.executions:
                if ex.execution_type != "STOP":
                    cost += config.cost_model.get_action_cost(ex.execution_type)
        else:
            cost = r.intervention_count * config.cost_model.retry_cost
        net_rev = rec_amt - cost
        apro_cases_rec.append(is_rec)
        apro_cases_net.append(net_rev)

    for b_def in config.baseline_definitions:
        if not b_def.enabled:
            continue

        baseline = get_baseline_instance(b_def.baseline_type)
        base_rec_count = 0
        base_gross_recovered = 0
        base_total_cost = 0

        base_cases_rec: list[int] = []
        base_cases_net: list[int] = []

        for r in records:
            is_r, amt_r, cost_r = baseline.evaluate_case(r, config)
            if is_r:
                base_rec_count += 1
                base_gross_recovered += amt_r
            base_total_cost += cost_r

            base_cases_rec.append(1 if is_r else 0)
            base_cases_net.append(amt_r - cost_r)

        base_rec_rate = round(base_rec_count / n, 4)
        base_net_rev = base_gross_recovered - base_total_cost

        abs_delta_rec = round(apro_kpis.recovery_rate - base_rec_rate, 4)
        rel_delta_rec = (
            round(abs_delta_rec / base_rec_rate, 4) if base_rec_rate > 0 else None
        )
        inc_gross = apro_kpis.gross_recovered_amount - base_gross_recovered
        inc_net = apro_kpis.net_recovered_revenue - base_net_rev

        diff_rec = [a - b for a, b in zip(apro_cases_rec, base_cases_rec, strict=False)]
        diff_net = [a - b for a, b in zip(apro_cases_net, base_cases_net, strict=False)]

        ci_rec = compute_paired_bootstrap_ci(
            diff_rec,
            confidence_level=config.confidence_level,
            iterations=config.bootstrap_iterations,
            seed=config.bootstrap_seed,
        )
        ci_net = compute_paired_bootstrap_ci(
            diff_net,
            confidence_level=config.confidence_level,
            iterations=config.bootstrap_iterations,
            seed=config.bootstrap_seed,
        )

        p_val = compute_paired_randomization_p_value(
            diff_rec,
            iterations=config.bootstrap_iterations,
            seed=config.bootstrap_seed,
        )
        alpha = round(1.0 - config.confidence_level, 4)
        is_sig = p_val < alpha

        results[b_def.name] = BaselineComparisonResult(
            baseline_type=b_def.baseline_type,
            baseline_name=b_def.name,
            baseline_version=b_def.version,
            apro_recovery_rate=apro_kpis.recovery_rate,
            baseline_recovery_rate=base_rec_rate,
            absolute_recovery_delta=abs_delta_rec,
            relative_recovery_delta=rel_delta_rec,
            apro_gross_recovered=apro_kpis.gross_recovered_amount,
            baseline_gross_recovered=base_gross_recovered,
            incremental_recovered_amount=inc_gross,
            apro_net_recovered=apro_kpis.net_recovered_revenue,
            baseline_net_recovered=base_net_rev,
            incremental_net_revenue=inc_net,
            apro_intervention_cost=apro_kpis.total_intervention_cost,
            baseline_intervention_cost=base_total_cost,
            delta_recovery_ci_95=ci_rec,
            delta_net_revenue_ci_95=ci_net,
            p_value=p_val,
            comparison_label=MetricComparisonLabel.BENCHMARK_ASSOCIATION,
            is_statistically_significant=is_sig,
        )

    return results


# ---------------------------------------------------------------------------
# Phase 6 Legacy Baseline Strategies (for simulation benchmark compatibility)
# ---------------------------------------------------------------------------


class BaseStrategy(ABC):
    """Abstract base strategy for Phase 6 legacy simulation."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable strategy name."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Strategy implementation version."""

    @abstractmethod
    def select_action(self, model_input: ModelInputRecord) -> SimulatedActionType:
        """Select a candidate action given observable model input."""


class NoInterventionStrategy(BaseStrategy):
    """Baseline 0 — Always select STOP (Phase 6 legacy)."""

    @property
    def name(self) -> str:
        return "No Intervention"

    @property
    def version(self) -> str:
        return "v1.0"

    def select_action(self, model_input: ModelInputRecord) -> SimulatedActionType:
        _ = model_input
        return SimulatedActionType.STOP


class AlwaysRetryStrategy(BaseStrategy):
    """Baseline 1 — Always select RETRY if candidate (Phase 6 legacy)."""

    @property
    def name(self) -> str:
        return "Always Retry"

    @property
    def version(self) -> str:
        return "v1.0"

    def select_action(self, model_input: ModelInputRecord) -> SimulatedActionType:
        if SimulatedActionType.RETRY in model_input.features.candidate_actions:
            return SimulatedActionType.RETRY
        return SimulatedActionType.STOP


class StaticRulesStrategy(BaseStrategy):
    """Baseline 2 — Documented static failure rules (Phase 6 legacy)."""

    def __init__(
        self, custom_rules: dict[str, SimulatedActionType] | None = None
    ) -> None:
        self._rules: dict[str, SimulatedActionType] = custom_rules or {
            "GATEWAY_TIMEOUT": SimulatedActionType.RETRY,
            "PROCESSING_TIMEOUT": SimulatedActionType.RETRY,
            "TRANSIENT_NETWORK_ERROR": SimulatedActionType.RETRY,
            "ISSUER_UNAVAILABLE": SimulatedActionType.PAYMENT_LINK,
            "SWITCH_MALFUNCTION": SimulatedActionType.PAYMENT_LINK,
            "BANK_TIMEOUT": SimulatedActionType.PAYMENT_LINK,
            "INSUFFICIENT_FUNDS": SimulatedActionType.OUTREACH,
            "LIMIT_EXCEEDED": SimulatedActionType.OUTREACH,
            "PAYMENT_CANCELLED": SimulatedActionType.OUTREACH,
            "OTP_EXPIRED": SimulatedActionType.OUTREACH,
            "3DS_AUTH_FAILED": SimulatedActionType.OUTREACH,
            "2FA_DECLINED": SimulatedActionType.OUTREACH,
            "EXPIRED_CARD": SimulatedActionType.PAYMENT_LINK,
            "VPA_NOT_FOUND": SimulatedActionType.PAYMENT_LINK,
            "ACCOUNT_RESTRICTED": SimulatedActionType.PAYMENT_LINK,
            "ACQUIRER_REJECTED": SimulatedActionType.RETRY,
            "GATEWAY_ERROR": SimulatedActionType.RETRY,
            "TRANSACTION_TIMED_OUT": SimulatedActionType.RETRY,
            "CONFIRMATION_TIMEOUT": SimulatedActionType.RETRY,
        }

    @property
    def name(self) -> str:
        return "Static Failure Rules"

    @property
    def version(self) -> str:
        return "v1.0"

    def select_action(self, model_input: ModelInputRecord) -> SimulatedActionType:
        code = model_input.features.failure_code
        preferred_action = self._rules.get(code, SimulatedActionType.STOP)

        if preferred_action in model_input.features.candidate_actions:
            return preferred_action
        return SimulatedActionType.STOP


class GlobalActionRateStrategy(BaseStrategy):
    """Baseline 3 — Highest observed recovery rate (Phase 6 legacy)."""

    def __init__(
        self, action_rates: dict[SimulatedActionType, float] | None = None
    ) -> None:
        self._action_rates: dict[SimulatedActionType, float] | None = action_rates
        self._is_fitted: bool = action_rates is not None

    @property
    def name(self) -> str:
        return "Global Action Rate"

    @property
    def version(self) -> str:
        return "v1.0"

    @property
    def is_fitted(self) -> bool:
        return self._is_fitted

    def fit(self, training_dataset: GovernedDataset) -> None:
        if training_dataset.manifest.dataset_type != DatasetType.TRAINING:
            msg = (
                "GlobalActionRateStrategy.fit() is strictly permitted on "
                f"TRAINING datasets; received dataset of type "
                f"'{training_dataset.manifest.dataset_type.value}'."
            )
            raise ValueError(msg)

        success_counts: dict[SimulatedActionType, int] = dict.fromkeys(
            SimulatedActionType, 0
        )
        total_counts: dict[SimulatedActionType, int] = dict.fromkeys(
            SimulatedActionType, 0
        )

        for record in training_dataset.records:
            obs = record.model_input.training_label
            if obs is None:
                continue

            total_counts[obs.observed_action] += 1
            if obs.observed_outcome_status == SimulatedOutcomeStatus.SUCCESS:
                success_counts[obs.observed_action] += 1

        new_rates: dict[SimulatedActionType, float] = {}
        for action in SimulatedActionType:
            tot = total_counts[action]
            new_rates[action] = (success_counts[action] / tot) if tot > 0 else 0.0

        self._action_rates = new_rates
        self._is_fitted = True

    def select_action(self, model_input: ModelInputRecord) -> SimulatedActionType:
        if not self._is_fitted or self._action_rates is None:
            msg = (
                "GlobalActionRateStrategy is unfitted. You must call fit() with a "
                "valid TRAINING dataset before selecting actions."
            )
            raise ValueError(msg)

        candidates = model_input.features.candidate_actions
        if not candidates:
            return SimulatedActionType.STOP

        return max(
            candidates,
            key=lambda act: self._action_rates.get(act, 0.0),  # type: ignore[union-attr]
        )
