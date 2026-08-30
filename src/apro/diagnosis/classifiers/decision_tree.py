"""Multi-class Decision Tree classifier for Model A failure diagnosis."""

from typing import Any

from apro.diagnosis.classifiers.interface import BaseDiagnosisModel
from apro.diagnosis.enums import (
    DIAGNOSIS_TAXONOMY_ORDER,
    DiagnosisCategory,
)
from apro.diagnosis.features import DiagnosisFeatureVector
from apro.diagnosis.models import DiagnosisLabel


class DecisionTreeNode:
    """Internal recursive node representing a decision rule or leaf distribution."""

    def __init__(
        self,
        feature_idx: int | None = None,
        threshold: float | None = None,
        left: "DecisionTreeNode | None" = None,
        right: "DecisionTreeNode | None" = None,
        class_probabilities: dict[DiagnosisCategory, float] | None = None,
    ) -> None:
        self.feature_idx = feature_idx
        self.threshold = threshold
        self.left = left
        self.right = right
        self.class_probabilities = class_probabilities

    @property
    def is_leaf(self) -> bool:
        return self.class_probabilities is not None

    def to_dict(self) -> dict[str, Any]:
        """Serialize node structure to dictionary."""
        if self.is_leaf:
            return {
                "is_leaf": True,
                "probabilities": {
                    c.value: p for c, p in (self.class_probabilities or {}).items()
                },
            }
        return {
            "is_leaf": False,
            "feature_idx": self.feature_idx,
            "threshold": self.threshold,
            "left": self.left.to_dict() if self.left else None,
            "right": self.right.to_dict() if self.right else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DecisionTreeNode":
        """Deserialize node structure from dictionary."""
        if data.get("is_leaf", False):
            raw_probs = data.get("probabilities", {})
            probs = {DiagnosisCategory(c): float(p) for c, p in raw_probs.items()}
            return cls(class_probabilities=probs)
        return cls(
            feature_idx=data.get("feature_idx"),
            threshold=data.get("threshold"),
            left=(cls.from_dict(data["left"]) if data.get("left") else None),
            right=(cls.from_dict(data["right"]) if data.get("right") else None),
        )


def _gini(counts: list[int], total: int) -> float:
    """Calculate Gini impurity."""
    if total == 0:
        return 0.0
    return 1.0 - sum((c / total) ** 2 for c in counts)


class DecisionTreeDiagnosisModel(BaseDiagnosisModel):
    """Deterministic Multi-class Classification Tree with Gini Impurity."""

    def __init__(
        self,
        model_name: str = "Decision Tree",
        model_version: str = "v1.0",
        max_depth: int = 6,
        min_samples_split: int = 10,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            model_name=model_name,
            model_version=model_version,
            **kwargs,
        )
        self._max_depth = max_depth
        self._min_samples_split = min_samples_split
        self._root: DecisionTreeNode | None = None
        self._class_order = list(DIAGNOSIS_TAXONOMY_ORDER)

    @property
    def max_depth(self) -> int:
        return self._max_depth

    @property
    def min_samples_split(self) -> int:
        return self._min_samples_split

    def _build_tree(
        self,
        x_data: list[list[float]],
        y_data: list[int],
        depth: int,
    ) -> DecisionTreeNode:
        n = len(y_data)
        num_classes = len(self._class_order)

        # Count frequencies
        counts = [0] * num_classes
        for y in y_data:
            counts[y] += 1

        # Check stopping criteria
        is_pure = any(c == n for c in counts)
        if depth >= self._max_depth or n < self._min_samples_split or is_pure:
            # Leaf node with Laplace smoothed distribution
            smoothed = [
                (counts[k] + 0.1) / (n + 0.1 * num_classes) for k in range(num_classes)
            ]
            tot = sum(smoothed)
            probs = {c: (smoothed[k] / tot) for k, c in enumerate(self._class_order)}
            return DecisionTreeNode(class_probabilities=probs)

        # Find best split
        best_gain = -1.0
        best_feat: int | None = None
        best_thresh: float | None = None
        best_left_idx: list[int] = []
        best_right_idx: list[int] = []

        current_impurity = _gini(counts, n)
        num_features = len(x_data[0])

        for f_idx in range(num_features):
            values = sorted({x_data[i][f_idx] for i in range(n)})
            if len(values) <= 1:
                continue

            # Candidate thresholds as midpoints
            thresholds = [
                (values[i] + values[i + 1]) / 2.0
                for i in range(min(len(values) - 1, 15))
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

        # Recurse
        left_x = [x_data[i] for i in best_left_idx]
        left_y = [y_data[i] for i in best_left_idx]
        right_x = [x_data[i] for i in best_right_idx]
        right_y = [y_data[i] for i in best_right_idx]

        left_node = self._build_tree(left_x, left_y, depth + 1)
        right_node = self._build_tree(right_x, right_y, depth + 1)

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
        """Fit decision tree on numerical training data."""
        class_to_idx = {c: i for i, c in enumerate(self._class_order)}
        x_data = [f.values for f in features]
        y_data = [class_to_idx[lbl.failure_category] for lbl in labels]

        self._root = self._build_tree(x_data, y_data, depth=0)

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
        """Traverse tree to leaf node and return class distribution."""
        if not self._root:
            return {c: (1.0 / len(self._class_order)) for c in self._class_order}
        return self._traverse(self._root, feature_vector.values)

    def export_parameters(self) -> dict[str, Any]:
        """Export serialized tree structure."""
        return {
            "max_depth": self._max_depth,
            "min_samples_split": self._min_samples_split,
            "tree": self._root.to_dict() if self._root else None,
        }

    def load_parameters(self, params: dict[str, Any]) -> None:
        """Load tree structure from artifact."""
        self._max_depth = params.get("max_depth", self._max_depth)
        self._min_samples_split = params.get(
            "min_samples_split", self._min_samples_split
        )
        if params.get("tree"):
            self._root = DecisionTreeNode.from_dict(params["tree"])
        self._is_fitted = True
