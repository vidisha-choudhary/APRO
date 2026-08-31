"""Decision Tree model for action-conditioned recovery outcome prediction."""

from dataclasses import dataclass
from typing import Any

from apro.recovery_prediction.classifiers.interface import (
    BaseRecoveryOutcomeModel,
)
from apro.recovery_prediction.enums import PredictedOutcomeState, RecoveryAction
from apro.recovery_prediction.features import RecoveryFeatureVector
from apro.recovery_prediction.models import RecoveryOutcomeLabel


@dataclass
class OutcomeTreeNode:
    """Internal node or leaf in an action-conditioned outcome decision tree."""

    feature_idx: int | None = None
    threshold: float | None = None
    left: "OutcomeTreeNode | None" = None
    right: "OutcomeTreeNode | None" = None
    success_probability: float | None = None
    is_leaf: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize tree node recursively to dictionary."""
        if self.is_leaf:
            return {
                "is_leaf": True,
                "success_probability": self.success_probability,
            }
        return {
            "is_leaf": False,
            "feature_idx": self.feature_idx,
            "threshold": self.threshold,
            "left": self.left.to_dict() if self.left else None,
            "right": self.right.to_dict() if self.right else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OutcomeTreeNode":
        """Deserialize tree node recursively from dictionary."""
        if data.get("is_leaf", False):
            return cls(
                is_leaf=True,
                success_probability=data.get("success_probability", 0.0),
            )
        return cls(
            is_leaf=False,
            feature_idx=data.get("feature_idx"),
            threshold=data.get("threshold"),
            left=cls.from_dict(data["left"]) if data.get("left") else None,
            right=cls.from_dict(data["right"]) if data.get("right") else None,
        )


def _binary_gini(success_count: int, total_count: int) -> float:
    if total_count == 0:
        return 0.0
    p = success_count / total_count
    return 1.0 - (p**2 + (1.0 - p) ** 2)


class DecisionTreeOutcomeModel(BaseRecoveryOutcomeModel):
    """Action-conditioned binary decision tree classifier."""

    def __init__(
        self,
        max_depth: int = 6,
        min_samples_split: int = 6,
        seed: int = 42,
        model_version: str = "v1.0",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            model_name="Decision Tree Outcome Model",
            model_version=model_version,
            **kwargs,
        )
        self._max_depth = max_depth
        self._min_samples_split = min_samples_split
        self._seed = seed
        self._root: OutcomeTreeNode | None = None

    @property
    def seed(self) -> int:
        return self._seed

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
        depth: int = 0,
    ) -> OutcomeTreeNode:
        n = len(y_data)
        if n == 0:
            return OutcomeTreeNode(is_leaf=True, success_probability=0.0)

        p_success = sum(y_data) / n

        # Stopping criteria: pure node, max depth, or min samples
        if (
            depth >= self._max_depth
            or n < self._min_samples_split
            or p_success == 0.0
            or p_success == 1.0
        ):
            # Laplace-smoothed probability
            smoothed_p = (sum(y_data) + 1.0) / (n + 2.0)
            return OutcomeTreeNode(
                is_leaf=True,
                success_probability=smoothed_p,
            )

        current_impurity = _binary_gini(int(sum(y_data)), n)
        num_features = len(x_data[0])

        best_gain = -1.0
        best_feat: int | None = None
        best_thresh: float | None = None
        best_left_idx: list[int] = []
        best_right_idx: list[int] = []

        for f_idx in range(num_features):
            values = sorted({x_data[i][f_idx] for i in range(n)})
            if len(values) <= 1:
                continue

            thresholds = [
                (values[i] + values[i + 1]) / 2.0 for i in range(len(values) - 1)
            ]
            # Subsample candidate thresholds for efficiency if many unique values
            if len(thresholds) > 12:
                step = len(thresholds) // 12
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

        left_child = self._build_tree(left_x, left_y, depth + 1)
        right_child = self._build_tree(right_x, right_y, depth + 1)

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
        """Fit decision tree on numerical training data."""
        x_data = [f.values for f in features]
        y_data = [
            1.0 if lbl.outcome_state == PredictedOutcomeState.SUCCESS else 0.0
            for lbl in labels
        ]
        self._root = self._build_tree(x_data, y_data, depth=0)

    def _traverse(self, node: OutcomeTreeNode, x: list[float]) -> float:
        if node.is_leaf or node.success_probability is not None:
            return node.success_probability or 0.0
        if node.feature_idx is None or node.threshold is None:
            return 0.0
        if x[node.feature_idx] <= node.threshold:
            return self._traverse(node.left, x) if node.left else 0.0
        return self._traverse(node.right, x) if node.right else 0.0

    def predict_proba_raw(self, feature_vector: RecoveryFeatureVector) -> float:
        """Produce uncalibrated success probability from decision tree."""
        if feature_vector.action == RecoveryAction.STOP:
            return 0.0
        if self._root is None:
            return 0.0
        p = self._traverse(self._root, feature_vector.values)
        return max(0.0, min(1.0, p))

    def export_parameters(self) -> dict[str, Any]:
        """Export serialized decision tree structure."""
        return {
            "tree": self._root.to_dict() if self._root else None,
            "hyperparameters": {
                "max_depth": self._max_depth,
                "min_samples_split": self._min_samples_split,
            },
        }

    def load_parameters(self, params: dict[str, Any]) -> None:
        """Load decision tree structure from parameters dictionary."""
        tree_dict = params.get("tree")
        self._root = OutcomeTreeNode.from_dict(tree_dict) if tree_dict else None
        if "hyperparameters" in params:
            hp = params["hyperparameters"]
            self._max_depth = int(hp.get("max_depth", self._max_depth))
            self._min_samples_split = int(
                hp.get("min_samples_split", self._min_samples_split)
            )
        self._is_fitted = True
