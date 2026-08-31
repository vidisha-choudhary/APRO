"""Random Forest ensemble model for action-conditioned recovery outcome prediction."""

import math
import random
from typing import Any

from apro.recovery_prediction.classifiers.decision_tree import (
    OutcomeTreeNode,
    _binary_gini,
)
from apro.recovery_prediction.classifiers.interface import (
    BaseRecoveryOutcomeModel,
)
from apro.recovery_prediction.enums import PredictedOutcomeState, RecoveryAction
from apro.recovery_prediction.features import RecoveryFeatureVector
from apro.recovery_prediction.models import RecoveryOutcomeLabel


class RandomForestOutcomeModel(BaseRecoveryOutcomeModel):
    """Action-conditioned Random Forest ensemble of outcome decision trees."""

    def __init__(
        self,
        n_estimators: int = 15,
        max_depth: int = 7,
        min_samples_split: int = 6,
        seed: int = 42,
        model_version: str = "v1.0",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            model_name="Random Forest Outcome Model",
            model_version=model_version,
            **kwargs,
        )
        self._n_estimators = n_estimators
        self._max_depth = max_depth
        self._min_samples_split = min_samples_split
        self._seed = seed
        self._trees: list[OutcomeTreeNode] = []

    @property
    def n_estimators(self) -> int:
        return self._n_estimators

    @property
    def max_depth(self) -> int:
        return self._max_depth

    @property
    def min_samples_split(self) -> int:
        return self._min_samples_split

    def _build_tree(
        self,
        x_data: list[list[float]],
        y_data: list[float],
        depth: int,
        rng: random.Random,
    ) -> OutcomeTreeNode:
        n = len(y_data)
        if n == 0:
            return OutcomeTreeNode(is_leaf=True, success_probability=0.0)

        p_success = sum(y_data) / n

        is_pure = p_success == 0.0 or p_success == 1.0
        if depth >= self._max_depth or n < self._min_samples_split or is_pure:
            smoothed_p = (sum(y_data) + 1.0) / (n + 2.0)
            return OutcomeTreeNode(
                is_leaf=True,
                success_probability=smoothed_p,
            )

        current_impurity = _binary_gini(int(sum(y_data)), n)
        num_features = len(x_data[0])

        # Random feature subset selection (max_features = sqrt(p))
        k = max(1, int(math.sqrt(num_features)))
        feature_subset = rng.sample(range(num_features), k)

        best_gain = -1.0
        best_feat: int | None = None
        best_thresh: float | None = None
        best_left_idx: list[int] = []
        best_right_idx: list[int] = []

        for f_idx in feature_subset:
            values = sorted({x_data[i][f_idx] for i in range(n)})
            if len(values) <= 1:
                continue

            thresholds = [
                (values[i] + values[i + 1]) / 2.0 for i in range(len(values) - 1)
            ]
            if len(thresholds) > 8:
                step = len(thresholds) // 8
                thresholds = thresholds[::step]

            for thresh in thresholds:
                left_idx = [i for i in range(n) if x_data[i][f_idx] <= thresh]
                right_idx = [i for i in range(n) if x_data[i][f_idx] > thresh]

                if not left_idx or not right_idx:
                    continue

                n_l, n_r = len(left_idx), len(right_idx)
                s_l = sum(y_data[i] for i in left_idx)
                s_r = sum(y_data[i] for i in right_idx)

                imp_l = _binary_gini(int(s_l), n_l)
                imp_r = _binary_gini(int(s_r), n_r)
                gain = current_impurity - (n_l / n * imp_l + n_r / n * imp_r)

                if gain > best_gain:
                    best_gain = gain
                    best_feat = f_idx
                    best_thresh = thresh
                    best_left_idx = left_idx
                    best_right_idx = right_idx

        if best_gain <= 1e-6 or best_feat is None:
            smoothed_p = (sum(y_data) + 1.0) / (n + 2.0)
            return OutcomeTreeNode(
                is_leaf=True,
                success_probability=smoothed_p,
            )

        left_x = [x_data[i] for i in best_left_idx]
        left_y = [y_data[i] for i in best_left_idx]
        right_x = [x_data[i] for i in best_right_idx]
        right_y = [y_data[i] for i in best_right_idx]

        left_child = self._build_tree(left_x, left_y, depth + 1, rng)
        right_child = self._build_tree(right_x, right_y, depth + 1, rng)

        return OutcomeTreeNode(
            feature_idx=best_feat,
            threshold=best_thresh,
            left=left_child,
            right=right_child,
        )

    def _fit_internal(
        self,
        features: list[RecoveryFeatureVector],
        labels: list[RecoveryOutcomeLabel],
    ) -> None:
        """Fit ensemble of randomized decision trees on bootstrap samples."""
        n = len(features)
        x_all = [f.values for f in features]
        y_all = [
            1.0 if lbl.outcome_state == PredictedOutcomeState.SUCCESS else 0.0
            for lbl in labels
        ]

        self._trees = []
        master_rng = random.Random(self._seed)

        for _ in range(self._n_estimators):
            tree_seed = master_rng.randint(0, 1000000)
            tree_rng = random.Random(tree_seed)

            # Bootstrap sample (with replacement)
            sample_indices = [tree_rng.randint(0, n - 1) for _ in range(n)]
            x_boot = [x_all[i] for i in sample_indices]
            y_boot = [y_all[i] for i in sample_indices]

            tree = self._build_tree(x_boot, y_boot, depth=0, rng=tree_rng)
            self._trees.append(tree)

    def _traverse(self, node: OutcomeTreeNode, x: list[float]) -> float:
        if node.is_leaf or node.success_probability is not None:
            return node.success_probability or 0.0
        if node.feature_idx is None or node.threshold is None:
            return 0.0
        if x[node.feature_idx] <= node.threshold:
            return self._traverse(node.left, x) if node.left else 0.0
        return self._traverse(node.right, x) if node.right else 0.0

    def predict_proba_raw(self, feature_vector: RecoveryFeatureVector) -> float:
        """Ensemble average of predicted success probabilities across all trees."""
        if feature_vector.action == RecoveryAction.STOP:
            return 0.0
        if not self._trees:
            return 0.0

        probs = [self._traverse(t, feature_vector.values) for t in self._trees]
        avg_p = sum(probs) / len(probs)
        return max(0.0, min(1.0, avg_p))

    def export_parameters(self) -> dict[str, Any]:
        """Export serialized forest of decision trees."""
        return {
            "trees": [t.to_dict() for t in self._trees],
            "hyperparameters": {
                "n_estimators": self._n_estimators,
                "max_depth": self._max_depth,
                "min_samples_split": self._min_samples_split,
                "seed": self._seed,
            },
        }

    def load_parameters(self, params: dict[str, Any]) -> None:
        """Load forest of decision trees from parameters dictionary."""
        tree_dicts = params.get("trees", [])
        self._trees = [OutcomeTreeNode.from_dict(d) for d in tree_dicts]
        if "hyperparameters" in params:
            hp = params["hyperparameters"]
            self._n_estimators = int(hp.get("n_estimators", self._n_estimators))
            self._max_depth = int(hp.get("max_depth", self._max_depth))
            self._min_samples_split = int(
                hp.get("min_samples_split", self._min_samples_split)
            )
            self._seed = int(hp.get("seed", self._seed))
        self._is_fitted = True
