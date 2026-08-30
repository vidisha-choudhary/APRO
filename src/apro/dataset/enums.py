"""Dataset-related enumerations for APRO Phase 6."""

from enum import StrEnum


class DatasetType(StrEnum):
    """Governed dataset classification types."""

    TRAINING = "TRAINING"
    VALIDATION = "VALIDATION"
    HELD_OUT_TEST = "HELD_OUT_TEST"
    BENCHMARK = "BENCHMARK"


class SplitStrategy(StrEnum):
    """Supported dataset splitting strategies."""

    RANDOM = "RANDOM"
    TEMPORAL = "TEMPORAL"
    GROUPED = "GROUPED"
