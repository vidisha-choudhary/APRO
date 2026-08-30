"""Multinomial Logistic Regression (Softmax) classifier for Model A."""

import math
import random
from typing import Any

from apro.diagnosis.classifiers.interface import BaseDiagnosisModel
from apro.diagnosis.enums import (
    DIAGNOSIS_TAXONOMY_ORDER,
    DiagnosisCategory,
)
from apro.diagnosis.features import DiagnosisFeatureVector
from apro.diagnosis.models import DiagnosisLabel


class MultinomialLogisticRegressionDiagnosisModel(BaseDiagnosisModel):
    """Multinomial Softmax Logistic Regression with L2 Regularization."""

    def __init__(
        self,
        model_name: str = "Multinomial Logistic Regression",
        model_version: str = "v1.0",
        learning_rate: float = 0.05,
        l2_reg: float = 0.01,
        max_iter: int = 300,
        batch_size: int = 64,
        seed: int = 42,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            model_name=model_name,
            model_version=model_version,
            **kwargs,
        )
        self._lr = learning_rate
        self._l2_reg = l2_reg
        self._max_iter = max_iter
        self._batch_size = batch_size
        self._seed = seed
        self._weights: list[list[float]] = []  # shape: (K, D)
        self._biases: list[float] = []  # shape: (K,)
        self._class_order = list(DIAGNOSIS_TAXONOMY_ORDER)

    @property
    def learning_rate(self) -> float:
        return self._lr

    @property
    def l2_reg(self) -> float:
        return self._l2_reg

    def _fit_internal(
        self,
        features: list[DiagnosisFeatureVector],
        labels: list[DiagnosisLabel],
    ) -> None:
        """Train parameters via mini-batch gradient descent with L2 penalty."""
        num_classes = len(self._class_order)
        num_features = len(features[0].values)
        class_to_idx = {c: i for i, c in enumerate(self._class_order)}
        n = len(features)

        # Initialize weights deterministically
        rng = random.Random(self._seed)
        self._weights = [
            [rng.uniform(-0.01, 0.01) for _ in range(num_features)]
            for _ in range(num_classes)
        ]
        self._biases = [0.0] * num_classes

        # Calculate class weights for class imbalance
        counts = [0] * num_classes
        for lbl in labels:
            counts[class_to_idx[lbl.failure_category]] += 1
        class_weights = [
            (n / (num_classes * max(1, counts[k]))) for k in range(num_classes)
        ]

        # Optimization loop
        indices = list(range(n))
        for epoch in range(self._max_iter):
            rng.shuffle(indices)
            lr_t = self._lr / (1.0 + 0.005 * epoch)

            for start_idx in range(0, n, self._batch_size):
                batch_indices = indices[start_idx : start_idx + self._batch_size]
                bs = len(batch_indices)

                # Accumulate gradients
                grad_w = [[0.0] * num_features for _ in range(num_classes)]
                grad_b = [0.0] * num_classes

                for i in batch_indices:
                    x = features[i].values
                    y_idx = class_to_idx[labels[i].failure_category]
                    w_k = class_weights[y_idx]

                    # Forward: z_k = b_k + sum(W_kj * x_j)
                    logits = [
                        self._biases[k]
                        + sum(self._weights[k][j] * x[j] for j in range(num_features))
                        for k in range(num_classes)
                    ]
                    max_logit = max(logits)
                    exp_z = [math.exp(z - max_logit) for z in logits]
                    sum_exp = sum(exp_z)
                    probs = [ez / sum_exp for ez in exp_z]

                    # Error: (p_k - y_k) * class_weight
                    for k in range(num_classes):
                        err = (probs[k] - (1.0 if k == y_idx else 0.0)) * w_k
                        grad_b[k] += err
                        for j in range(num_features):
                            grad_w[k][j] += err * x[j]

                # Update parameters with L2 weight decay
                for k in range(num_classes):
                    self._biases[k] -= lr_t * (grad_b[k] / bs)
                    for j in range(num_features):
                        reg_term = self._l2_reg * self._weights[k][j]
                        self._weights[k][j] -= lr_t * ((grad_w[k][j] / bs) + reg_term)

    def predict_proba_raw(
        self, feature_vector: DiagnosisFeatureVector
    ) -> dict[DiagnosisCategory, float]:
        """Compute Softmax probabilities from linear logits."""
        x = feature_vector.values
        num_classes = len(self._class_order)
        num_features = len(x)

        logits = [
            self._biases[k]
            + sum(self._weights[k][j] * x[j] for j in range(num_features))
            for k in range(num_classes)
        ]
        max_logit = max(logits)
        exp_z = [math.exp(z - max_logit) for z in logits]
        sum_exp = sum(exp_z)

        return {c: (exp_z[i] / sum_exp) for i, c in enumerate(self._class_order)}

    def export_parameters(self) -> dict[str, Any]:
        """Export weights and biases for artifact serialization."""
        return {
            "weights": self._weights,
            "biases": self._biases,
            "learning_rate": self._lr,
            "l2_reg": self._l2_reg,
            "max_iter": self._max_iter,
            "batch_size": self._batch_size,
            "seed": self._seed,
        }

    def load_parameters(self, params: dict[str, Any]) -> None:
        """Load weights and biases from artifact parameters."""
        self._weights = params["weights"]
        self._biases = params["biases"]
        self._lr = params.get("learning_rate", self._lr)
        self._l2_reg = params.get("l2_reg", self._l2_reg)
        self._max_iter = params.get("max_iter", self._max_iter)
        self._batch_size = params.get("batch_size", self._batch_size)
        self._seed = params.get("seed", self._seed)
        self._is_fitted = True
