"""Benchmark execution, baseline adapters, metrics, and reporting for APRO Phase 6."""

from apro.evaluation.aggregation import (
    MultiSeedStats,
    aggregate_by_segment,
    aggregate_multi_seed_metrics,
    compute_multi_seed_stats,
)
from apro.evaluation.baselines import (
    AlwaysRetryStrategy,
    BaseStrategy,
    GlobalActionRateStrategy,
    NoInterventionStrategy,
    StaticRulesStrategy,
)
from apro.evaluation.benchmark import (
    BenchmarkConfig,
    BenchmarkManifest,
    BenchmarkRunner,
    BenchmarkRunResult,
)
from apro.evaluation.metrics import (
    DecisionMetrics,
    EconomicMetrics,
    EvaluationMetrics,
    SafetyReliabilityMetrics,
    calculate_metrics,
)
from apro.evaluation.reports import (
    generate_benchmark_summary_json,
    generate_benchmark_summary_markdown,
)
from apro.evaluation.traces import CaseEvaluationTrace

__all__ = [
    "AlwaysRetryStrategy",
    "BaseStrategy",
    "BenchmarkConfig",
    "BenchmarkManifest",
    "BenchmarkRunResult",
    "BenchmarkRunner",
    "CaseEvaluationTrace",
    "DecisionMetrics",
    "EconomicMetrics",
    "EvaluationMetrics",
    "GlobalActionRateStrategy",
    "MultiSeedStats",
    "NoInterventionStrategy",
    "SafetyReliabilityMetrics",
    "StaticRulesStrategy",
    "aggregate_by_segment",
    "aggregate_multi_seed_metrics",
    "calculate_metrics",
    "compute_multi_seed_stats",
    "generate_benchmark_summary_json",
    "generate_benchmark_summary_markdown",
]
