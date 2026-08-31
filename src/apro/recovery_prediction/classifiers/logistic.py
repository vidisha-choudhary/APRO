"""Logistic Regression model for action-conditioned recovery outcome prediction."""

import math
import random
from typing import Any

from apro.recovery_prediction.classifiers.interface import (
    BaseRecoveryOutcomeModel,
)
from apro.recovery_prediction.enums import PredictedOutcomeState, RecoveryAction
from apro.recovery_prediction.features import RecoveryFeatureVector
from apro.recovery_prediction.models import RecoveryOutcomeLabel


class LogisticRegressionOutcomeModel(BaseRecoveryOutcomeModel):
    """Action-conditioned binary logistic regression with L2 regularization."""

    def __init__(
        self,
        learning_rate: float = 0.05,
        max_iter: int = 250,
        l2_reg: float = 0.01,
        l2_penalty: float | None = None,
        seed: int = 42,
        model_version: str = "v1.0",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            model_name="Logistic Regression Outcome Model",
            model_version=model_version,
            **kwargs,
        )
        self._lr = learning_rate
        self._max_iter = max_iter
        self._l2_reg = l2_penalty if l2_penalty is not None else l2_reg
        self._seed = seed
        self._weights: list[float] = []
        self._bias: float = 0.0

    @property
    def learning_rate(self) -> float:
        return self._lr

    @property
    def max_iter(self) -> int:
        return self._max_iter

    @property
    def l2_reg(self) -> float:
        return self._l2_reg

    @property
    def weights(self) -> list[float]:
        return list(self._weights)

    @property
    def coefficients(self) -> list[float]:
        return list(self._weights)

    @property
    def bias(self) -> float:
        return self._bias

    def _fit_internal(
        self,
        features: list[RecoveryFeatureVector],
        labels: list[RecoveryOutcomeLabel],
    ) -> None:
        """Train logistic weights via mini-batch SGD with L2 penalty."""
        num_features = len(features[0].values)
        n = len(features)

        rng = random.Random(self._seed)
        self._weights = [(rng.random() - 0.5) * 0.05 for _ in range(num_features)]
        self._bias = 0.0

        targets = [
            1.0 if lbl.outcome_state == PredictedOutcomeState.SUCCESS else 0.0
            for lbl in labels
        ]

        batch_size = min(64, n)
        indices = list(range(n))

        for _ in range(self._max_iter):
            rng.shuffle(indices)
            for start_idx in range(0, n, batch_size):
                batch_idx = indices[start_idx : start_idx + batch_size]
                b_size = len(batch_idx)

                w_grad = [0.0] * num_features
                b_grad = 0.0

                for i in batch_idx:
                    x = features[i].values
                    y = targets[i]

                    # Linear logits
                    z = (
                        sum(w * val for w, val in zip(self._weights, x, strict=True))
                        + self._bias
                    )
                    p = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))
                    err = p - y

                    for j in range(num_features):
                        w_grad[j] += err * x[j]
                    b_grad += err

                # Weight updates with L2 regularization
                for j in range(num_features):
                    self._weights[j] -= self._lr * (
                        w_grad[j] / b_size + self._l2_reg * self._weights[j]
                    )
                self._bias -= self._lr * (b_grad / b_size)

    def predict_proba_raw(self, feature_vector: RecoveryFeatureVector) -> float:
        """Compute sigmoid probability P(success | context, action)."""
        x = feature_vector.values
        # Hard constraint: STOP action always produces 0.0 success probability
        if feature_vector.action == RecoveryAction.STOP:
            return 0.0

        z = sum(w * val for w, val in zip(self._weights, x, strict=True)) + self._bias
        p = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))
        return max(0.0, min(1.0, p))

    def export_parameters(self) -> dict[str, Any]:
        """Export trained weights and bias."""
        return {
            "weights": self._weights,
            "bias": self._bias,
            "hyperparameters": {
                "learning_rate": self._lr,
                "max_iter": self._max_iter,
                "l2_reg": self._l2_reg,
                "seed": self._seed,
            },
        }

    def load_parameters(self, params: dict[str, Any]) -> None:
        """Load trained weights and bias from artifact dictionary."""
        self._weights = [float(w) for w in params["weights"]]
        self._bias = float(params["bias"])
        if "hyperparameters" in params:
            hp = params["hyperparameters"]
            self._lr = float(hp.get("learning_rate", self._lr))
            self._max_iter = int(hp.get("max_iter", self._max_iter))
            self._l2_reg = float(hp.get("l2_reg", self._l2_reg))
            self._seed = int(hp.get("seed", self._seed))
        self._is_fitted = True
