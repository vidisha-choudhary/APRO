"""Diagnosis feature schema and decision-time feature extraction for APRO Phase 7."""

import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apro.dataset.enums import DatasetType
from apro.dataset.models import GovernedDataset, ModelInputRecord
from apro.simulation.enums import SimulatedPaymentMethod

DIAGNOSIS_FEATURE_SCHEMA_VERSION: str = "diagnosis-feature-v1"

FEATURE_NAMES: list[str] = [
    # Payment context
    "amount_log10",
    "attempt_count",
    "method_upi",
    "method_card",
    "method_netbanking",
    "method_wallet",
    "method_other_supported_method",
    # Failure metadata indicators
    "failure_code_present",
    "failure_reason_present",
    "failure_reason_length",
    # Keyword token indicators
    "kw_timeout",
    "kw_auth",
    "kw_bank",
    "kw_insufficient",
    "kw_method_error",
    "kw_gateway",
    "kw_unknown",
    # Observable customer history
    "prev_payment_count",
    "prev_success_count",
    "prev_failure_count",
    "prev_recovery_count",
    "prev_retry_success",
    "prev_payment_link_success",
    "historical_failure_rate",
    "historical_success_rate",
    "historical_recovery_rate",
    # Temporal context
    "hour_of_day",
    "is_weekend",
    "time_since_prev_attempt_log",
    "time_since_prev_attempt_present",
]


class DiagnosisFeatureDescriptor(BaseModel):
    """Metadata describing an individual diagnosis feature in the schema contract."""

    model_config = ConfigDict(frozen=True)

    name: str
    feature_type: str
    description: str
    decision_time_available: bool = True
    leakage_free: bool = True


class DiagnosisFeatureSchema(BaseModel):
    """Formal schema contract for Model A diagnosis features."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = Field(default=DIAGNOSIS_FEATURE_SCHEMA_VERSION)
    feature_names: list[str] = Field(default_factory=lambda: list(FEATURE_NAMES))
    descriptors: list[DiagnosisFeatureDescriptor] = Field(default_factory=list)


class DiagnosisFeatureVector(BaseModel):
    """Immutable numerical feature vector extracted for Model A prediction."""

    model_config = ConfigDict(frozen=True)

    record_id: str
    feature_schema_version: str = Field(default=DIAGNOSIS_FEATURE_SCHEMA_VERSION)
    values: list[float]
    feature_names: list[str] = Field(default_factory=lambda: list(FEATURE_NAMES))


class DiagnosisFeatureBuilder:
    """Extracts decision-time numerical features strictly from ModelInputRecord."""

    def __init__(
        self,
        schema_version: str = DIAGNOSIS_FEATURE_SCHEMA_VERSION,
        means: list[float] | None = None,
        stds: list[float] | None = None,
    ) -> None:
        self._schema_version = schema_version
        self._means = means
        self._stds = stds
        self._is_fitted = means is not None and stds is not None

    @property
    def schema_version(self) -> str:
        return self._schema_version

    @property
    def feature_names(self) -> list[str]:
        return list(FEATURE_NAMES)

    @property
    def is_fitted(self) -> bool:
        return self._is_fitted

    def get_schema(self) -> DiagnosisFeatureSchema:
        """Return the formal feature schema definition."""
        descriptors = [
            DiagnosisFeatureDescriptor(
                name=name,
                feature_type="float",
                description=f"Observable decision-time feature '{name}'",
                decision_time_available=True,
                leakage_free=True,
            )
            for name in FEATURE_NAMES
        ]
        return DiagnosisFeatureSchema(
            schema_version=self._schema_version,
            feature_names=self.feature_names,
            descriptors=descriptors,
        )

    def extract_raw_features(self, model_input: ModelInputRecord) -> list[float]:
        """Extract unstandardized raw feature vector from ModelInputRecord."""
        snap = model_input.features

        # 1. Payment Context
        amt_log = math.log10(max(1, snap.payment_amount))
        att_cnt = float(snap.attempt_count)

        method_upi = 1.0 if snap.payment_method == SimulatedPaymentMethod.UPI else 0.0
        method_card = 1.0 if snap.payment_method == SimulatedPaymentMethod.CARD else 0.0
        method_netbanking = (
            1.0 if snap.payment_method == SimulatedPaymentMethod.NETBANKING else 0.0
        )
        method_wallet = (
            1.0 if snap.payment_method == SimulatedPaymentMethod.WALLET else 0.0
        )
        method_other = (
            1.0
            if snap.payment_method == SimulatedPaymentMethod.OTHER_SUPPORTED_METHOD
            else 0.0
        )

        # 2. Failure Metadata Indicators
        code = (snap.failure_code or "").strip().upper()
        reason = (snap.failure_reason or "").strip().lower()

        code_present = 1.0 if len(code) > 0 else 0.0
        reason_present = 1.0 if len(reason) > 0 else 0.0
        reason_len = float(len(reason))

        combined_text = f"{code.lower()} {reason}"

        # 3. Keyword Token Indicators
        kw_timeout = (
            1.0
            if any(
                w in combined_text
                for w in ("timeout", "timed_out", "switch_malfunction")
            )
            else 0.0
        )
        kw_auth = (
            1.0
            if any(
                w in combined_text
                for w in (
                    "auth",
                    "3ds",
                    "otp",
                    "2fa",
                    "declined",
                    "cancelled",
                    "verification",
                )
            )
            else 0.0
        )
        kw_bank = (
            1.0
            if any(
                w in combined_text
                for w in (
                    "bank",
                    "issuer",
                    "switch",
                    "unavailable",
                    "network",
                    "node",
                )
            )
            else 0.0
        )
        kw_insufficient = (
            1.0
            if any(
                w in combined_text
                for w in (
                    "insufficient",
                    "limit",
                    "balance",
                    "funds",
                    "exceeded",
                )
            )
            else 0.0
        )
        kw_method_error = (
            1.0
            if any(
                w in combined_text
                for w in (
                    "expired",
                    "vpa",
                    "account",
                    "restricted",
                    "card",
                    "invalid",
                )
            )
            else 0.0
        )
        kw_gateway = (
            1.0
            if any(
                w in combined_text for w in ("gateway", "acquirer", "rejected", "error")
            )
            else 0.0
        )
        kw_unknown = (
            1.0
            if any(
                w in combined_text
                for w in ("unknown", "unexpected", "system", "internal")
            )
            else 0.0
        )

        # 4. Customer History (strictly pre-decision)
        prev_p = float(snap.previous_payment_count)
        prev_s = float(snap.previous_success_count)
        prev_f = float(snap.previous_failure_count)
        prev_r = float(snap.previous_recovery_count)
        prev_retry_s = float(snap.previous_retry_success)
        prev_link_s = float(snap.previous_payment_link_success)

        tot_p = max(1.0, prev_p)
        tot_f = max(1.0, prev_f)

        hist_fail_rate = prev_f / tot_p
        hist_succ_rate = prev_s / tot_p
        hist_rec_rate = prev_r / tot_f

        # 5. Temporal Context
        hour = float(snap.hour_of_day)
        is_wknd = 1.0 if snap.is_weekend else 0.0

        if snap.time_since_previous_attempt_seconds is not None:
            time_prev_log = math.log10(
                max(1.0, float(snap.time_since_previous_attempt_seconds))
            )
            time_prev_pres = 1.0
        else:
            time_prev_log = 0.0
            time_prev_pres = 0.0

        return [
            amt_log,
            att_cnt,
            method_upi,
            method_card,
            method_netbanking,
            method_wallet,
            method_other,
            code_present,
            reason_present,
            reason_len,
            kw_timeout,
            kw_auth,
            kw_bank,
            kw_insufficient,
            kw_method_error,
            kw_gateway,
            kw_unknown,
            prev_p,
            prev_s,
            prev_f,
            prev_r,
            prev_retry_s,
            prev_link_s,
            hist_fail_rate,
            hist_succ_rate,
            hist_rec_rate,
            hour,
            is_wknd,
            time_prev_log,
            time_prev_pres,
        ]

    def fit(self, training_dataset: GovernedDataset) -> None:
        """Fit standardization statistics strictly on a TRAINING dataset."""
        if training_dataset.manifest.dataset_type != DatasetType.TRAINING:
            ds_type = training_dataset.manifest.dataset_type.value
            msg = (
                "DiagnosisFeatureBuilder.fit() is strictly permitted on "
                f"TRAINING datasets; received '{ds_type}'."
            )
            raise ValueError(msg)

        n = len(training_dataset.records)
        if n == 0:
            msg = "Cannot fit feature statistics on an empty dataset."
            raise ValueError(msg)

        raw_matrix: list[list[float]] = [
            self.extract_raw_features(rec.model_input)
            for rec in training_dataset.records
        ]

        num_features = len(FEATURE_NAMES)
        means: list[float] = [0.0] * num_features
        for row in raw_matrix:
            for j in range(num_features):
                means[j] += row[j]
        means = [m / n for m in means]

        variances: list[float] = [0.0] * num_features
        for row in raw_matrix:
            for j in range(num_features):
                diff = row[j] - means[j]
                variances[j] += diff * diff

        stds: list[float] = [
            math.sqrt(v / n) if (v / n) > 1e-8 else 1.0 for v in variances
        ]

        self._means = means
        self._stds = stds
        self._is_fitted = True

    def transform(self, model_input: ModelInputRecord) -> DiagnosisFeatureVector:
        """Transform a single ModelInputRecord into a normalized feature vector."""
        raw = self.extract_raw_features(model_input)
        if self._is_fitted and self._means and self._stds:
            scaled = [
                (raw[j] - self._means[j]) / self._stds[j] for j in range(len(raw))
            ]
        else:
            scaled = list(raw)

        return DiagnosisFeatureVector(
            record_id=model_input.record_id,
            feature_schema_version=self._schema_version,
            values=scaled,
            feature_names=self.feature_names,
        )

    def transform_dataset(
        self, dataset: GovernedDataset
    ) -> list[DiagnosisFeatureVector]:
        """Transform all records in a GovernedDataset strictly using model inputs."""
        return [self.transform(rec.model_input) for rec in dataset.records]

    def to_dict(self) -> dict[str, Any]:
        """Export builder state for artifact persistence."""
        return {
            "schema_version": self._schema_version,
            "means": self._means,
            "stds": self._stds,
            "is_fitted": self._is_fitted,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DiagnosisFeatureBuilder":
        """Reconstruct builder from exported artifact dictionary."""
        return cls(
            schema_version=data.get("schema_version", DIAGNOSIS_FEATURE_SCHEMA_VERSION),
            means=data.get("means"),
            stds=data.get("stds"),
        )
