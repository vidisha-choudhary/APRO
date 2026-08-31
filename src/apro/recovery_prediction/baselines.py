"""Recovery outcome baseline models for APRO Phase 8 evaluation reference."""

import math
from typing import Any

from apro.recovery_prediction.classifiers.interface import (
    BaseRecoveryOutcomeModel,
)
from apro.recovery_prediction.enums import (
    RECOVERY_ACTION_ORDER,
    PredictedOutcomeState,
    RecoveryAction,
)
from apro.recovery_prediction.features import RecoveryFeatureVector
from apro.recovery_prediction.models import RecoveryOutcomeLabel


class GlobalActionRateBaseline(BaseRecoveryOutcomeModel):
    """Baseline 0 — Estimates empirical historical success rate per action."""

    def __init__(self, model_version: str = "v1.0", **kwargs: Any) -> None:
        super().__init__(
            model_name="Global Action Rate Baseline",
            model_version=model_version,
            **kwargs,
        )
        self._action_success_rates: dict[RecoveryAction, float] = {}

    def _fit_internal(
        self,
        features: list[RecoveryFeatureVector],
        labels: list[RecoveryOutcomeLabel],
    ) -> None:
        _ = features
        action_totals: dict[RecoveryAction, int] = dict.fromkeys(
            RECOVERY_ACTION_ORDER, 0
        )
        action_successes: dict[RecoveryAction, int] = dict.fromkeys(
            RECOVERY_ACTION_ORDER, 0
        )

        for lbl in labels:
            act = lbl.action
            action_totals[act] += 1
            if lbl.outcome_state == PredictedOutcomeState.SUCCESS:
                action_successes[act] += 1

        self._action_success_rates = {
            act: (
                action_successes[act] / action_totals[act]
                if action_totals[act] > 0
                else 0.0
            )
            for act in RECOVERY_ACTION_ORDER
        }
        # Hard constraint on STOP
        self._action_success_rates[RecoveryAction.STOP] = 0.0

    def predict_proba_raw(self, feature_vector: RecoveryFeatureVector) -> float:
        return self._action_success_rates.get(feature_vector.action, 0.0)

    def export_parameters(self) -> dict[str, Any]:
        return {
            "action_success_rates": {
                k.value: v for k, v in self._action_success_rates.items()
            }
        }

    def load_parameters(self, params: dict[str, Any]) -> None:
        raw_rates = params.get("action_success_rates", {})
        self._action_success_rates = {
            RecoveryAction(k): float(v) for k, v in raw_rates.items()
        }
        self._is_fitted = True


class ActionStratifiedHistoricalBaseline(BaseRecoveryOutcomeModel):
    """Baseline 1 — Conditions empirical success rates on (action, method_bucket)."""

    def __init__(self, model_version: str = "v1.0", **kwargs: Any) -> None:
        super().__init__(
            model_name="Action Stratified Historical Baseline",
            model_version=model_version,
            **kwargs,
        )
        self._stratified_rates: dict[str, float] = {}
        self._global_rates: dict[RecoveryAction, float] = {}

    def _fit_internal(
        self,
        features: list[RecoveryFeatureVector],
        labels: list[RecoveryOutcomeLabel],
    ) -> None:
        bucket_totals: dict[str, int] = {}
        bucket_successes: dict[str, int] = {}
        act_totals: dict[RecoveryAction, int] = dict.fromkeys(RECOVERY_ACTION_ORDER, 0)
        act_successes: dict[RecoveryAction, int] = dict.fromkeys(
            RECOVERY_ACTION_ORDER, 0
        )

        for feat, lbl in zip(features, labels, strict=True):
            act = lbl.action
            # Bucket key: action + failure kw signature
            kw_sig = 0
            vals = feat.values
            for k_idx in range(7, min(14, len(vals))):
                if vals[k_idx] > 0.0:  # standardized positive
                    kw_sig |= 1 << (k_idx - 7)

            key = f"{act.value}:{kw_sig}"
            bucket_totals[key] = bucket_totals.get(key, 0) + 1
            act_totals[act] += 1

            if lbl.outcome_state == PredictedOutcomeState.SUCCESS:
                bucket_successes[key] = bucket_successes.get(key, 0) + 1
                act_successes[act] += 1

        self._global_rates = {
            act: (act_successes[act] / act_totals[act] if act_totals[act] > 0 else 0.0)
            for act in RECOVERY_ACTION_ORDER
        }
        self._global_rates[RecoveryAction.STOP] = 0.0

        self._stratified_rates = {}
        for key, tot in bucket_totals.items():
            act = RecoveryAction(key.split(":")[0])
            s = bucket_successes.get(key, 0)
            prior = self._global_rates.get(act, 0.0)
            self._stratified_rates[key] = (s + 2.0 * prior) / (tot + 2.0)

    def predict_proba_raw(self, feature_vector: RecoveryFeatureVector) -> float:
        act = feature_vector.action
        if act == RecoveryAction.STOP:
            return 0.0

        vals = feature_vector.values
        kw_sig = 0
        for k_idx in range(7, min(14, len(vals))):
            if vals[k_idx] > 0.0:
                kw_sig |= 1 << (k_idx - 7)

        key = f"{act.value}:{kw_sig}"
        return self._stratified_rates.get(key, self._global_rates.get(act, 0.0))

    def export_parameters(self) -> dict[str, Any]:
        return {
            "stratified_rates": self._stratified_rates,
            "global_rates": {k.value: v for k, v in self._global_rates.items()},
        }

    def load_parameters(self, params: dict[str, Any]) -> None:
        self._stratified_rates = dict(params.get("stratified_rates", {}))
        raw_globals = params.get("global_rates", {})
        self._global_rates = {
            RecoveryAction(k): float(v) for k, v in raw_globals.items()
        }
        self._is_fitted = True


class StaticOutcomeRuleBaseline(BaseRecoveryOutcomeModel):
    """Baseline 2 — Deterministic versioned rule mapping context & action to outcome."""

    def __init__(self, model_version: str = "v1.0", **kwargs: Any) -> None:
        super().__init__(
            model_name="Static Outcome Rule Baseline",
            model_version=model_version,
            **kwargs,
        )
        self._is_fitted = True

    def _fit_internal(
        self,
        features: list[RecoveryFeatureVector],
        labels: list[RecoveryOutcomeLabel],
    ) -> None:
        _ = features, labels
        self._is_fitted = True

    def predict_proba_raw(self, feature_vector: RecoveryFeatureVector) -> float:
        act = feature_vector.action
        if act == RecoveryAction.STOP:
            return 0.0
        if act == RecoveryAction.ESCALATE:
            return 0.10

        vals = feature_vector.values
        is_timeout = len(vals) > 7 and vals[7] > 0.0
        is_auth = len(vals) > 8 and vals[8] > 0.0
        is_insufficient = len(vals) > 10 and vals[10] > 0.0
        is_method = len(vals) > 11 and vals[11] > 0.0
        is_gateway = len(vals) > 12 and vals[12] > 0.0

        if act == RecoveryAction.RETRY:
            if is_timeout or is_gateway:
                return 0.85
            return 0.20
        if act == RecoveryAction.PAYMENT_LINK:
            if is_insufficient or is_auth or is_method:
                return 0.80
            return 0.30
        if act == RecoveryAction.OUTREACH:
            if is_insufficient:
                return 0.70
            return 0.25

        return 0.30

    def export_parameters(self) -> dict[str, Any]:
        return {"rule_version": "v1.0"}

    def load_parameters(self, params: dict[str, Any]) -> None:
        _ = params
        self._is_fitted = True


class SimpleStatisticalOutcomeBaseline(BaseRecoveryOutcomeModel):
    """Baseline 3 — Naive Bayes action-conditioned probability predictor."""

    def __init__(self, model_version: str = "v1.0", **kwargs: Any) -> None:
        super().__init__(
            model_name="Simple Statistical Outcome Baseline",
            model_version=model_version,
            **kwargs,
        )
        self._priors: dict[RecoveryAction, float] = {}
        self._pos_means: dict[RecoveryAction, list[float]] = {}
        self._neg_means: dict[RecoveryAction, list[float]] = {}

    def _fit_internal(
        self,
        features: list[RecoveryFeatureVector],
        labels: list[RecoveryOutcomeLabel],
    ) -> None:
        num_features = len(features[0].values)
        pos_by_act: dict[RecoveryAction, list[list[float]]] = {
            act: [] for act in RECOVERY_ACTION_ORDER
        }
        neg_by_act: dict[RecoveryAction, list[list[float]]] = {
            act: [] for act in RECOVERY_ACTION_ORDER
        }

        for feat, lbl in zip(features, labels, strict=True):
            act = lbl.action
            if lbl.outcome_state == PredictedOutcomeState.SUCCESS:
                pos_by_act[act].append(feat.values)
            else:
                neg_by_act[act].append(feat.values)

        for act in RECOVERY_ACTION_ORDER:
            p_cnt = len(pos_by_act[act])
            n_cnt = len(neg_by_act[act])
            tot = p_cnt + n_cnt
            self._priors[act] = (p_cnt + 1.0) / (tot + 2.0)

            if p_cnt > 0:
                self._pos_means[act] = [
                    sum(pos_by_act[act][i][j] for i in range(p_cnt)) / p_cnt
                    for j in range(num_features)
                ]
            else:
                self._pos_means[act] = [0.0] * num_features

            if n_cnt > 0:
                self._neg_means[act] = [
                    sum(neg_by_act[act][i][j] for i in range(n_cnt)) / n_cnt
                    for j in range(num_features)
                ]
            else:
                self._neg_means[act] = [0.0] * num_features

    def predict_proba_raw(self, feature_vector: RecoveryFeatureVector) -> float:
        act = feature_vector.action
        if act == RecoveryAction.STOP:
            return 0.0

        prior = self._priors.get(act, 0.5)
        pos_m = self._pos_means.get(act, [])
        neg_m = self._neg_means.get(act, [])
        x = feature_vector.values

        if not pos_m or not neg_m:
            return prior

        dist_pos = sum((x[j] - pos_m[j]) ** 2 for j in range(len(x)))
        dist_neg = sum((x[j] - neg_m[j]) ** 2 for j in range(len(x)))

        diff = dist_neg - dist_pos
        p = 1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, diff * 0.1))))
        return max(0.0, min(1.0, p))

    def export_parameters(self) -> dict[str, Any]:
        return {
            "priors": {k.value: v for k, v in self._priors.items()},
            "pos_means": {k.value: v for k, v in self._pos_means.items()},
            "neg_means": {k.value: v for k, v in self._neg_means.items()},
        }

    def load_parameters(self, params: dict[str, Any]) -> None:
        self._priors = {
            RecoveryAction(k): float(v) for k, v in params.get("priors", {}).items()
        }
        self._pos_means = {
            RecoveryAction(k): [float(x) for x in v]
            for k, v in params.get("pos_means", {}).items()
        }
        self._neg_means = {
            RecoveryAction(k): [float(x) for x in v]
            for k, v in params.get("neg_means", {}).items()
        }
        self._is_fitted = True
