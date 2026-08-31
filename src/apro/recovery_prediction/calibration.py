"""Probability calibration methods for APRO Phase 8 Recovery Prediction."""

import math
from typing import Any

from apro.dataset.enums import DatasetType
from apro.dataset.models import GovernedDataset
from apro.diagnosis.classifiers.interface import BaseDiagnosisModel
from apro.recovery_prediction.enums import (
    RECOVERY_ACTION_ORDER,
    PredictedOutcomeState,
    RecoveryAction,
)
from apro.recovery_prediction.labels import construct_outcome_label
from apro.recovery_prediction.models import RecoveryOutcomeLabel


def _binary_log_loss(probs: list[float], labels: list[int]) -> float:
    eps = 1e-15
    loss = 0.0
    for p, y in zip(probs, labels, strict=True):
        p_clipped = max(eps, min(1.0 - eps, p))
        if y == 1:
            loss -= math.log(p_clipped)
        else:
            loss -= math.log(1.0 - p_clipped)
    return loss / max(1, len(probs))


class RecoveryTemperatureCalibrator:
    """Action-conditioned temperature scaling calibrator for Model B probabilities.

    Governance Rules:
    - Calibration fitting is strictly permitted on TRAINING or VALIDATION datasets.
    - HELD_OUT_TEST and BENCHMARK datasets are strictly rejected.
    """

    def __init__(
        self,
        temperatures: dict[RecoveryAction, float] | None = None,
        default_temperature: float = 1.0,
    ) -> None:
        self._temperatures = temperatures or dict.fromkeys(
            RECOVERY_ACTION_ORDER, default_temperature
        )
        self._is_fitted = False

    @property
    def is_fitted(self) -> bool:
        return self._is_fitted

    @property
    def temperatures(self) -> dict[RecoveryAction, float]:
        return dict(self._temperatures)

    def calibrate_probability(self, raw_p: float, action: RecoveryAction) -> float:
        """Apply learned temperature scaling to an uncalibrated success probability."""
        if action == RecoveryAction.STOP:
            return 0.0
        if raw_p <= 0.0:
            return 0.0
        if raw_p >= 1.0:
            return 1.0

        temp = self._temperatures.get(action, 1.0)
        eps = 1e-7
        p_safe = max(eps, min(1.0 - eps, raw_p))
        logit = math.log(p_safe / (1.0 - p_safe))
        scaled_logit = logit / max(1e-4, temp)
        cal_p = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, scaled_logit))))
        return max(0.0, min(1.0, cal_p))

    def fit(
        self,
        raw_probs_by_action: dict[RecoveryAction, list[float]],
        labels_by_action: dict[RecoveryAction, list[RecoveryOutcomeLabel]],
        dataset_type: DatasetType = DatasetType.VALIDATION,
    ) -> None:
        """Optimize temperature scaling parameters per recovery action."""
        if dataset_type not in (DatasetType.TRAINING, DatasetType.VALIDATION):
            msg = (
                "Probability calibration is strictly permitted on TRAINING or "
                f"VALIDATION datasets; received '{dataset_type.value}'."
            )
            raise ValueError(msg)

        candidate_temps = [
            0.1,
            0.2,
            0.3,
            0.4,
            0.5,
            0.6,
            0.7,
            0.8,
            0.9,
            1.0,
            1.2,
            1.5,
            1.8,
            2.0,
            2.5,
            3.0,
            4.0,
            5.0,
        ]

        for act in RECOVERY_ACTION_ORDER:
            probs = raw_probs_by_action.get(act, [])
            labels = labels_by_action.get(act, [])

            if not probs or not labels:
                self._temperatures[act] = 1.0
                continue

            y_binary = [
                1 if lbl.outcome_state == PredictedOutcomeState.SUCCESS else 0
                for lbl in labels
            ]

            # If constant class, default to 1.0
            if len(set(y_binary)) <= 1:
                self._temperatures[act] = 1.0
                continue

            best_loss = float("inf")
            best_temp = 1.0

            for temp in candidate_temps:
                scaled_probs = [self._scale_single(p, temp) for p in probs]
                loss = _binary_log_loss(scaled_probs, y_binary)
                if loss < best_loss:
                    best_loss = loss
                    best_temp = temp

            self._temperatures[act] = round(best_temp, 4)

        self._is_fitted = True

    def _scale_single(self, raw_p: float, temp: float) -> float:
        eps = 1e-7
        p_safe = max(eps, min(1.0 - eps, raw_p))
        logit = math.log(p_safe / (1.0 - p_safe))
        scaled_logit = logit / max(1e-4, temp)
        return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, scaled_logit))))

    def fit_on_dataset(
        self,
        model: Any,
        dataset: GovernedDataset,
        diagnosis_model: BaseDiagnosisModel | None = None,
    ) -> None:
        """Fit calibration on a GovernedDataset (TRAINING or VALIDATION)."""
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

        raw_probs_by_action: dict[RecoveryAction, list[float]] = {
            act: [] for act in RECOVERY_ACTION_ORDER
        }
        labels_by_action: dict[RecoveryAction, list[RecoveryOutcomeLabel]] = {
            act: [] for act in RECOVERY_ACTION_ORDER
        }

        diag_map = {}
        if diagnosis_model is not None:
            for rec in dataset.records:
                diag_map[rec.model_input.record_id] = diagnosis_model.predict(
                    rec.model_input
                )

        fb = model.feature_builder
        for rec in dataset.records:
            diag_res = diag_map.get(rec.model_input.record_id)
            p_amount = rec.model_input.features.payment_amount
            ds_version = dataset.manifest.dataset_version

            for act in RECOVERY_ACTION_ORDER:
                feat = fb.transform(rec.model_input, act, diagnosis_result=diag_res)
                raw_p = model.predict_proba_raw(feat)
                lbl = construct_outcome_label(
                    truth_record=rec.evaluation_truth,
                    action=act,
                    payment_amount=p_amount,
                    dataset_version=ds_version,
                )
                raw_probs_by_action[act].append(raw_p)
                labels_by_action[act].append(lbl)

        self.fit(
            raw_probs_by_action,
            labels_by_action,
            dataset_type=dataset.manifest.dataset_type,
        )

    def to_dict(self) -> dict[str, Any]:
        """Export calibrator metadata for serialization."""
        return {
            "method": "action_temperature_scaling",
            "is_fitted": self._is_fitted,
            "temperatures": {k.value: v for k, v in self._temperatures.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RecoveryTemperatureCalibrator":
        """Load calibrator from dictionary."""
        raw_temps = data.get("temperatures", {})
        temps = {RecoveryAction(k): float(v) for k, v in raw_temps.items()}
        cal = cls(temperatures=temps)
        cal._is_fitted = data.get("is_fitted", True)
        return cal
