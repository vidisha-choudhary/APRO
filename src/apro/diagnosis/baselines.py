"""Diagnosis baseline models for APRO Phase 7 evaluation reference."""

import math
from typing import Any

from apro.diagnosis.classifiers.interface import BaseDiagnosisModel
from apro.diagnosis.enums import (
    DIAGNOSIS_TAXONOMY_ORDER,
    DiagnosisCategory,
)
from apro.diagnosis.features import DiagnosisFeatureVector
from apro.diagnosis.models import DiagnosisLabel


class MajorityClassBaseline(BaseDiagnosisModel):
    """Baseline 0 — Predicts empirical majority class from training data."""

    def __init__(self, model_version: str = "v1.0", **kwargs: Any) -> None:
        super().__init__(
            model_name="Majority Class Baseline",
            model_version=model_version,
            **kwargs,
        )
        self._class_distribution: dict[DiagnosisCategory, float] = {}
        self._majority_class: DiagnosisCategory = DIAGNOSIS_TAXONOMY_ORDER[0]

    def _fit_internal(
        self,
        features: list[DiagnosisFeatureVector],
        labels: list[DiagnosisLabel],
    ) -> None:
        _ = features
        n = len(labels)
        counts: dict[DiagnosisCategory, int] = dict.fromkeys(
            DIAGNOSIS_TAXONOMY_ORDER, 0
        )
        for lbl in labels:
            counts[lbl.failure_category] += 1

        self._class_distribution = {
            c: (counts[c] / n) for c in DIAGNOSIS_TAXONOMY_ORDER
        }
        self._majority_class = max(
            DIAGNOSIS_TAXONOMY_ORDER,
            key=lambda c: (
                self._class_distribution[c],
                -DIAGNOSIS_TAXONOMY_ORDER.index(c),
            ),
        )

    def predict_proba_raw(
        self, feature_vector: DiagnosisFeatureVector
    ) -> dict[DiagnosisCategory, float]:
        _ = feature_vector
        return dict(self._class_distribution)

    def export_parameters(self) -> dict[str, Any]:
        return {
            "class_distribution": {
                c.value: p for c, p in self._class_distribution.items()
            },
            "majority_class": self._majority_class.value,
        }

    def load_parameters(self, params: dict[str, Any]) -> None:
        raw_dist = params.get("class_distribution", {})
        self._class_distribution = {
            DiagnosisCategory(k): float(v) for k, v in raw_dist.items()
        }
        self._majority_class = DiagnosisCategory(
            params.get("majority_class", DIAGNOSIS_TAXONOMY_ORDER[0].value)
        )
        self._is_fitted = True


class ProviderRuleBaseline(BaseDiagnosisModel):
    """Baseline 1 — Rule-based deterministic mapping from provider failure metadata."""

    def __init__(self, model_version: str = "v1.0", **kwargs: Any) -> None:
        super().__init__(
            model_name="Provider Rule Baseline",
            model_version=model_version,
            **kwargs,
        )
        self._rule_mapping: dict[str, DiagnosisCategory] = {
            "GATEWAY_TIMEOUT": DiagnosisCategory.TIMEOUT,
            "PROCESSING_TIMEOUT": DiagnosisCategory.TIMEOUT,
            "BANK_TIMEOUT": DiagnosisCategory.TIMEOUT,
            "TRANSACTION_TIMED_OUT": DiagnosisCategory.TIMEOUT,
            "CONFIRMATION_TIMEOUT": DiagnosisCategory.TIMEOUT,
            "TRANSIENT_NETWORK_ERROR": DiagnosisCategory.TRANSIENT_FAILURE,
            "GATEWAY_ERROR": DiagnosisCategory.GATEWAY_FAILURE,
            "ACQUIRER_REJECTED": DiagnosisCategory.GATEWAY_FAILURE,
            "ISSUER_UNAVAILABLE": DiagnosisCategory.BANK_SIDE_FAILURE,
            "SWITCH_MALFUNCTION": DiagnosisCategory.BANK_SIDE_FAILURE,
            "INSUFFICIENT_FUNDS": DiagnosisCategory.CUSTOMER_SIDE_FAILURE,
            "LIMIT_EXCEEDED": DiagnosisCategory.CUSTOMER_SIDE_FAILURE,
            "PAYMENT_CANCELLED": DiagnosisCategory.CUSTOMER_SIDE_FAILURE,
            "OTP_EXPIRED": DiagnosisCategory.AUTHENTICATION_FAILURE,
            "3DS_AUTH_FAILED": DiagnosisCategory.AUTHENTICATION_FAILURE,
            "2FA_DECLINED": DiagnosisCategory.AUTHENTICATION_FAILURE,
            "EXPIRED_CARD": DiagnosisCategory.PAYMENT_METHOD_FAILURE,
            "VPA_NOT_FOUND": DiagnosisCategory.PAYMENT_METHOD_FAILURE,
            "ACCOUNT_RESTRICTED": DiagnosisCategory.PAYMENT_METHOD_FAILURE,
        }
        self._is_fitted = True

    def _fit_internal(
        self,
        features: list[DiagnosisFeatureVector],
        labels: list[DiagnosisLabel],
    ) -> None:
        # Rule baseline is structurally defined and requires no data fitting
        _ = features, labels

    def predict_proba_raw(
        self, feature_vector: DiagnosisFeatureVector
    ) -> dict[DiagnosisCategory, float]:
        values = feature_vector.values
        # Feature indices from features.py: kw_timeout=10, kw_auth=11, kw_bank=12,
        # kw_insufficient=13, kw_method_error=14, kw_gateway=15, kw_unknown=16
        matched_cat: DiagnosisCategory = DiagnosisCategory.UNKNOWN_FAILURE

        if len(values) > 16:
            if values[10] > 0.5:  # kw_timeout
                matched_cat = DiagnosisCategory.TIMEOUT
            elif values[11] > 0.5:  # kw_auth
                matched_cat = DiagnosisCategory.AUTHENTICATION_FAILURE
            elif values[12] > 0.5:  # kw_bank
                matched_cat = DiagnosisCategory.BANK_SIDE_FAILURE
            elif values[13] > 0.5:  # kw_insufficient
                matched_cat = DiagnosisCategory.CUSTOMER_SIDE_FAILURE
            elif values[14] > 0.5:  # kw_method_error
                matched_cat = DiagnosisCategory.PAYMENT_METHOD_FAILURE
            elif values[15] > 0.5:  # kw_gateway
                matched_cat = DiagnosisCategory.GATEWAY_FAILURE
            elif values[16] > 0.5:  # kw_unknown
                matched_cat = DiagnosisCategory.UNKNOWN_FAILURE

        # Assign high probability to matched class, distribute remainder
        high_prob = 0.86
        low_prob = (1.0 - high_prob) / (len(DIAGNOSIS_TAXONOMY_ORDER) - 1)

        return {
            c: (high_prob if c == matched_cat else low_prob)
            for c in DIAGNOSIS_TAXONOMY_ORDER
        }

    def export_parameters(self) -> dict[str, Any]:
        return {"rules": {k: v.value for k, v in self._rule_mapping.items()}}

    def load_parameters(self, params: dict[str, Any]) -> None:
        raw_rules = params.get("rules", {})
        self._rule_mapping = {k: DiagnosisCategory(v) for k, v in raw_rules.items()}
        self._is_fitted = True


class HistoricalConditionalBaseline(BaseDiagnosisModel):
    """Baseline 2 — Empirical conditional distribution computed from training data."""

    def __init__(self, model_version: str = "v1.0", **kwargs: Any) -> None:
        super().__init__(
            model_name="Historical Conditional Baseline",
            model_version=model_version,
            **kwargs,
        )
        self._conditional_probs: dict[int, dict[DiagnosisCategory, float]] = {}
        self._global_priors: dict[DiagnosisCategory, float] = {}

    def _fit_internal(
        self,
        features: list[DiagnosisFeatureVector],
        labels: list[DiagnosisLabel],
    ) -> None:
        n = len(features)
        global_counts: dict[DiagnosisCategory, int] = dict.fromkeys(
            DIAGNOSIS_TAXONOMY_ORDER, 0
        )
        bucket_counts: dict[int, dict[DiagnosisCategory, int]] = {}

        for feat, lbl in zip(features, labels, strict=True):
            cat = lbl.failure_category
            global_counts[cat] += 1

            # Determine keyword bucket signature
            kw_sig = 0
            for k_idx in range(10, min(17, len(feat.values))):
                if feat.values[k_idx] > 0.5:
                    kw_sig |= 1 << (k_idx - 10)

            bucket_counts.setdefault(
                kw_sig, dict.fromkeys(DIAGNOSIS_TAXONOMY_ORDER, 0)
            )[cat] += 1

        self._global_priors = {
            c: (global_counts[c] / n) for c in DIAGNOSIS_TAXONOMY_ORDER
        }

        self._conditional_probs = {}
        num_classes = len(DIAGNOSIS_TAXONOMY_ORDER)
        for sig, counts in bucket_counts.items():
            tot = sum(counts.values())
            # Laplace smoothing with global priors
            smoothed = {
                c: (counts[c] + 1.0 * self._global_priors[c])
                / (tot + 1.0 * num_classes)
                for c in DIAGNOSIS_TAXONOMY_ORDER
            }
            s_tot = sum(smoothed.values())
            self._conditional_probs[sig] = {
                c: (smoothed[c] / s_tot) for c in DIAGNOSIS_TAXONOMY_ORDER
            }

    def predict_proba_raw(
        self, feature_vector: DiagnosisFeatureVector
    ) -> dict[DiagnosisCategory, float]:
        feat = feature_vector.values
        kw_sig = 0
        for k_idx in range(10, min(17, len(feat))):
            if feat[k_idx] > 0.5:
                kw_sig |= 1 << (k_idx - 10)

        if kw_sig in self._conditional_probs:
            return dict(self._conditional_probs[kw_sig])
        return dict(self._global_priors)

    def export_parameters(self) -> dict[str, Any]:
        return {
            "global_priors": {c.value: p for c, p in self._global_priors.items()},
            "conditional_probs": {
                str(k): {c.value: p for c, p in v.items()}
                for k, v in self._conditional_probs.items()
            },
        }

    def load_parameters(self, params: dict[str, Any]) -> None:
        raw_priors = params.get("global_priors", {})
        self._global_priors = {
            DiagnosisCategory(k): float(v) for k, v in raw_priors.items()
        }
        raw_cond = params.get("conditional_probs", {})
        self._conditional_probs = {
            int(k): {DiagnosisCategory(c): float(p) for c, p in v.items()}
            for k, v in raw_cond.items()
        }
        self._is_fitted = True


class NaiveBayesDiagnosisModel(BaseDiagnosisModel):
    """Baseline 3 — Gaussian / Bernoulli Naive Bayes classifier."""

    def __init__(self, model_version: str = "v1.0", **kwargs: Any) -> None:
        super().__init__(
            model_name="Naive Bayes Baseline",
            model_version=model_version,
            **kwargs,
        )
        self._class_priors: dict[DiagnosisCategory, float] = {}
        self._means: dict[DiagnosisCategory, list[float]] = {}
        self._variances: dict[DiagnosisCategory, list[float]] = {}

    def _fit_internal(
        self,
        features: list[DiagnosisFeatureVector],
        labels: list[DiagnosisLabel],
    ) -> None:
        n = len(features)
        num_features = len(features[0].values)

        by_class: dict[DiagnosisCategory, list[list[float]]] = {
            c: [] for c in DIAGNOSIS_TAXONOMY_ORDER
        }
        for f, lbl in zip(features, labels, strict=True):
            by_class[lbl.failure_category].append(f.values)

        self._class_priors = {}
        self._means = {}
        self._variances = {}

        for c in DIAGNOSIS_TAXONOMY_ORDER:
            c_data = by_class[c]
            c_count = len(c_data)
            self._class_priors[c] = (c_count + 1.0) / (
                n + len(DIAGNOSIS_TAXONOMY_ORDER)
            )

            if c_count == 0:
                self._means[c] = [0.0] * num_features
                self._variances[c] = [1.0] * num_features
                continue

            means = [0.0] * num_features
            for row in c_data:
                for j in range(num_features):
                    means[j] += row[j]
            means = [m / c_count for m in means]

            vars_ = [0.0] * num_features
            for row in c_data:
                for j in range(num_features):
                    diff = row[j] - means[j]
                    vars_[j] += diff * diff
            vars_ = [max(1e-4, v / c_count) for v in vars_]

            self._means[c] = means
            self._variances[c] = vars_

    def predict_proba_raw(
        self, feature_vector: DiagnosisFeatureVector
    ) -> dict[DiagnosisCategory, float]:
        x = feature_vector.values
        num_features = len(x)

        log_posteriors: list[float] = []
        for c in DIAGNOSIS_TAXONOMY_ORDER:
            prior = self._class_priors.get(c, 1e-6)
            log_p = math.log(max(1e-12, prior))

            means = self._means.get(c, [0.0] * num_features)
            vars_ = self._variances.get(c, [1.0] * num_features)

            for j in range(num_features):
                mean = means[j]
                var = vars_[j]
                diff = x[j] - mean
                log_prob_x = -0.5 * math.log(2.0 * math.pi * var) - (
                    (diff * diff) / (2.0 * var)
                )
                log_p += log_prob_x

            log_posteriors.append(log_p)

        max_lp = max(log_posteriors)
        exp_lp = [math.exp(lp - max_lp) for lp in log_posteriors]
        sum_exp = sum(exp_lp)

        return {
            c: (exp_lp[i] / sum_exp) for i, c in enumerate(DIAGNOSIS_TAXONOMY_ORDER)
        }

    def export_parameters(self) -> dict[str, Any]:
        return {
            "priors": {c.value: p for c, p in self._class_priors.items()},
            "means": {c.value: m for c, m in self._means.items()},
            "variances": {c.value: v for c, v in self._variances.items()},
        }

    def load_parameters(self, params: dict[str, Any]) -> None:
        raw_priors = params.get("priors", {})
        self._class_priors = {
            DiagnosisCategory(k): float(v) for k, v in raw_priors.items()
        }
        raw_means = params.get("means", {})
        self._means = {DiagnosisCategory(k): v for k, v in raw_means.items()}
        raw_vars = params.get("variances", {})
        self._variances = {DiagnosisCategory(k): v for k, v in raw_vars.items()}
        self._is_fitted = True
