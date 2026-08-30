"""Random Forest ensemble classifier for Model A failure diagnosis."""

import random
from typing import Any

from apro.diagnosis.classifiers.decision_tree import DecisionTreeNode, _gini
from apro.diagnosis.classifiers.interface import BaseDiagnosisModel
from apro.diagnosis.enums import (
    DIAGNOSIS_TAXONOMY_ORDER,
    DiagnosisCategory,
)
from apro.diagnosis.features import DiagnosisFeatureVector
from apro.diagnosis.models import DiagnosisLabel


class RandomForestDiagnosisModel(BaseDiagnosisModel):
    """Deterministic Random Forest ensemble with bootstrap aggregation."""

    def __init__(
        self,
        model_name: str = "Random Forest",
        model_version: str = "v1.0",
        n_estimators: int = 15,
        max_depth: int = 7,
        min_samples_split: int = 5,
        max_features_ratio: float = 0.75,
        seed: int = 42,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            model_name=model_name,
            model_version=model_version,
            **kwargs,
        )
        self._n_estimators = n_estimators
        self._max_depth = max_depth
        self._min_samples_split = min_samples_split
        self._max_features_ratio = max_features_ratio
        self._seed = seed
        self._trees: list[DecisionTreeNode] = []
        self._class_order = list(DIAGNOSIS_TAXONOMY_ORDER)

    @property
    def n_estimators(self) -> int:
        return self._n_estimators

    @property
    def max_depth(self) -> int:
        return self._max_depth

    def _build_tree(
        self,
        x_data: list[list[float]],
        y_data: list[int],
        depth: int,
        rng: random.Random,
    ) -> DecisionTreeNode:
        n = len(y_data)
        num_classes = len(self._class_order)

        counts = [0] * num_classes
        for y in y_data:
            counts[y] += 1

        is_pure = any(c == n for c in counts)
        if depth >= self._max_depth or n < self._min_samples_split or is_pure:
            smoothed = [
                (counts[k] + 0.1) / (n + 0.1 * num_classes) for k in range(num_classes)
            ]
            tot = sum(smoothed)
            probs = {c: (smoothed[k] / tot) for k, c in enumerate(self._class_order)}
            return DecisionTreeNode(class_probabilities=probs)

        # Feature subsampling
        num_features = len(x_data[0])
        n_sub_feat = max(1, int(round(num_features * self._max_features_ratio)))
        selected_features = rng.sample(range(num_features), n_sub_feat)

        best_gain = -1.0
        best_feat: int | None = None
        best_thresh: float | None = None
        best_left_idx: list[int] = []
        best_right_idx: list[int] = []

        current_impurity = _gini(counts, n)

        for f_idx in selected_features:
            values = sorted({x_data[i][f_idx] for i in range(n)})
            if len(values) <= 1:
                continue

            thresholds = [
                (values[i] + values[i + 1]) / 2.0
                for i in range(min(len(values) - 1, 10))
            ]

            for thresh in thresholds:
                left_idx = [i for i in range(n) if x_data[i][f_idx] <= thresh]
                right_idx = [i for i in range(n) if x_data[i][f_idx] > thresh]

                if not left_idx or not right_idx:
                    continue

                left_counts = [0] * num_classes
                for i in left_idx:
                    left_counts[y_data[i]] += 1
                right_counts = [0] * num_classes
                for i in right_idx:
                    right_counts[y_data[i]] += 1

                left_impurity = _gini(left_counts, len(left_idx))
                right_impurity = _gini(right_counts, len(right_idx))

                weighted_impurity = (len(left_idx) / n) * left_impurity + (
                    len(right_idx) / n
                ) * right_impurity
                gain = current_impurity - weighted_impurity

                if gain > best_gain:
                    best_gain = gain
                    best_feat = f_idx
                    best_thresh = thresh
                    best_left_idx = left_idx
                    best_right_idx = right_idx

        if best_gain <= 1e-6 or best_feat is None or best_thresh is None:
            smoothed = [
                (counts[k] + 0.1) / (n + 0.1 * num_classes) for k in range(num_classes)
            ]
            tot = sum(smoothed)
            probs = {c: (smoothed[k] / tot) for k, c in enumerate(self._class_order)}
            return DecisionTreeNode(class_probabilities=probs)

        left_x = [x_data[i] for i in best_left_idx]
        left_y = [y_data[i] for i in best_left_idx]
        right_x = [x_data[i] for i in best_right_idx]
        right_y = [y_data[i] for i in best_right_idx]

        left_node = self._build_tree(left_x, left_y, depth + 1, rng)
        right_node = self._build_tree(right_x, right_y, depth + 1, rng)

        return DecisionTreeNode(
            feature_idx=best_feat,
            threshold=best_thresh,
            left=left_node,
            right=right_node,
        )

    def _fit_internal(
        self,
        features: list[DiagnosisFeatureVector],
        labels: list[DiagnosisLabel],
    ) -> None:
        """Fit ensemble of randomized decision trees on bootstrap samples."""
        n = len(features)
        class_to_idx = {c: i for i, c in enumerate(self._class_order)}
        x_all = [f.values for f in features]
        y_all = [class_to_idx[lbl.failure_category] for lbl in labels]

        self._trees = []
        master_rng = random.Random(self._seed)

        for _ in range(self._n_estimators):
            tree_seed = master_rng.randint(0, 1000000)
            tree_rng = random.Random(tree_seed)

            # Bootstrap sample (sampling with replacement)
            sample_indices = [tree_rng.randint(0, n - 1) for _ in range(n)]
            x_boot = [x_all[i] for i in sample_indices]
            y_boot = [y_all[i] for i in sample_indices]

            tree = self._build_tree(x_boot, y_boot, depth=0, rng=tree_rng)
            self._trees.append(tree)

    def _traverse(
        self, node: DecisionTreeNode, x: list[float]
    ) -> dict[DiagnosisCategory, float]:
        if node.is_leaf or node.class_probabilities is not None:
            return node.class_probabilities or {
                c: (1.0 / len(self._class_order)) for c in self._class_order
            }
        if (
            node.feature_idx is not None
            and node.threshold is not None
            and x[node.feature_idx] <= node.threshold
        ):
            return self._traverse(node.left, x) if node.left else {}
        return self._traverse(node.right, x) if node.right else {}

    def predict_proba_raw(
        self, feature_vector: DiagnosisFeatureVector
    ) -> dict[DiagnosisCategory, float]:
        """Aggregate and average class probability distributions across all trees."""
        if not self._trees:
            return {c: (1.0 / len(self._class_order)) for c in self._class_order}

        avg_probs: dict[DiagnosisCategory, float] = dict.fromkeys(
            self._class_order, 0.0
        )
        for tree in self._trees:
            t_probs = self._traverse(tree, feature_vector.values)
            for c in self._class_order:
                avg_probs[c] += t_probs.get(c, 0.0)

        num_trees = len(self._trees)
        return {c: (avg_probs[c] / num_trees) for c in self._class_order}

    def export_parameters(self) -> dict[str, Any]:
        """Export serialized ensemble trees."""
        return {
            "n_estimators": self._n_estimators,
            "max_depth": self._max_depth,
            "min_samples_split": self._min_samples_split,
            "max_features_ratio": self._max_features_ratio,
            "seed": self._seed,
            "trees": [t.to_dict() for t in self._trees],
        }

    def load_parameters(self, params: dict[str, Any]) -> None:
        """Load ensemble trees from artifact parameters."""
        self._n_estimators = params.get("n_estimators", self._n_estimators)
        self._max_depth = params.get("max_depth", self._max_depth)
        self._min_samples_split = params.get(
            "min_samples_split", self._min_samples_split
        )
        self._max_features_ratio = params.get(
            "max_features_ratio", self._max_features_ratio
        )
        self._seed = params.get("seed", self._seed)
        self._trees = [DecisionTreeNode.from_dict(t) for t in params.get("trees", [])]
        self._is_fitted = True
