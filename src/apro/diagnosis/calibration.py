"""Probability calibration methods and reliability analysis for Phase 7."""

import math
from typing import Any

from apro.dataset.enums import DatasetType
from apro.dataset.models import GovernedDataset
from apro.diagnosis.enums import (
    DIAGNOSIS_TAXONOMY_ORDER,
    DiagnosisCategory,
)
from apro.diagnosis.labels import construct_labels_from_dataset
from apro.diagnosis.models import DiagnosisLabel


class TemperatureCalibrator:
    """Multi-class Temperature Scaling Calibrator for Model A probabilities."""

    def __init__(self, temperature: float = 1.0) -> None:
        if temperature <= 0.0:
            msg = f"Temperature must be strictly positive (got {temperature})."
            raise ValueError(msg)
        self._temperature = temperature
        self._is_fitted = False

    @property
    def temperature(self) -> float:
        return self._temperature

    @property
    def is_fitted(self) -> bool:
        return self._is_fitted

    def calibrate(
        self, probabilities: dict[DiagnosisCategory, float]
    ) -> dict[DiagnosisCategory, float]:
        """Apply temperature scaling to a probability distribution."""
        if math.isclose(self._temperature, 1.0, abs_tol=1e-6):
            return dict(probabilities)

        eps = 1e-15
        classes = list(DIAGNOSIS_TAXONOMY_ORDER)

        # Logits: z_c = ln(p_c)
        logits = [
            math.log(max(eps, min(1.0, probabilities.get(c, 0.0)))) / self._temperature
            for c in classes
        ]

        max_logit = max(logits)
        exp_logits = [math.exp(z - max_logit) for z in logits]
        sum_exp = sum(exp_logits)

        calibrated: dict[DiagnosisCategory, float] = {}
        for c, exp_z in zip(classes, exp_logits, strict=True):
            calibrated[c] = round(exp_z / sum_exp, 6)

        # Normalize any rounding residual to sum exactly to 1.0
        tot = sum(calibrated.values())
        if tot > 0:
            first_c = classes[0]
            calibrated[first_c] += round(1.0 - tot, 6)

        return calibrated

    def fit_on_dataset(
        self,
        model: Any,
        dataset: GovernedDataset,
        feature_builder: Any | None = None,
    ) -> None:
        """Fit temperature on GovernedDataset (TRAINING/VALIDATION)."""
        if dataset.manifest.dataset_type not in (
            DatasetType.TRAINING,
            DatasetType.VALIDATION,
        ):
            ds_type = dataset.manifest.dataset_type.value
            msg = (
                "Probability calibration is strictly permitted on TRAINING or "
                f"VALIDATION datasets; received '{ds_type}'."
            )
            raise ValueError(msg)

        fb = feature_builder or getattr(model, "feature_builder", None)
        labels = construct_labels_from_dataset(dataset)
        raw_probs: list[dict[DiagnosisCategory, float]] = []

        for rec in dataset.records:
            feat = fb.transform(rec.model_input) if fb else None
            p = model.predict_proba_raw(feat)
            raw_probs.append(p)

        self.fit(raw_probs, labels, dataset_type=dataset.manifest.dataset_type)

    def fit(
        self,
        probabilities_list: list[dict[DiagnosisCategory, float]],
        labels: list[DiagnosisLabel],
        dataset_type: DatasetType = DatasetType.VALIDATION,
    ) -> None:
        """Find optimal temperature on validation set via 1D grid search."""
        if dataset_type not in (
            DatasetType.TRAINING,
            DatasetType.VALIDATION,
        ):
            msg = (
                "Probability calibration is strictly permitted on TRAINING or "
                f"VALIDATION datasets; received '{dataset_type.value}'."
            )
            raise ValueError(msg)
        if len(probabilities_list) != len(labels):
            msg = "Probabilities list and labels length mismatch."
            raise ValueError(msg)
        if len(labels) == 0:
            msg = "Cannot fit calibrator on empty dataset."
            raise ValueError(msg)

        eps = 1e-15
        classes = list(DIAGNOSIS_TAXONOMY_ORDER)

        # Precompute logits and targets
        raw_logits: list[list[float]] = []
        actual_indices: list[int] = []

        class_to_idx = {c: i for i, c in enumerate(classes)}

        for probs, lbl in zip(probabilities_list, labels, strict=True):
            logits_row = [
                math.log(max(eps, min(1.0, probs.get(c, 0.0)))) for c in classes
            ]
            raw_logits.append(logits_row)
            actual_indices.append(class_to_idx[lbl.failure_category])

        # Optimize temperature over candidate temperatures [0.1, 5.0]
        candidate_temps: list[float] = [0.1 + i * 0.05 for i in range(1, 100)] + [1.0]

        best_temp = 1.0
        best_loss = float("inf")

        for temp in candidate_temps:
            loss = 0.0
            for logits, act_idx in zip(raw_logits, actual_indices, strict=True):
                scaled = [z / temp for z in logits]
                max_s = max(scaled)
                exp_s = [math.exp(z - max_s) for z in scaled]
                sum_s = sum(exp_s)
                p_act = exp_s[act_idx] / sum_s
                loss += -math.log(max(eps, p_act))

            if loss < best_loss:
                best_loss = loss
                best_temp = temp

        self._temperature = round(best_temp, 4)
        self._is_fitted = True

    def to_dict(self) -> dict[str, Any]:
        """Export serialized calibration parameters."""
        return {
            "method": "temperature_scaling",
            "temperature": self._temperature,
            "is_fitted": self._is_fitted,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TemperatureCalibrator":
        """Reconstruct calibrator from dictionary artifact."""
        cal = cls(temperature=data.get("temperature", 1.0))
        cal._is_fitted = data.get("is_fitted", False)
        return cal
