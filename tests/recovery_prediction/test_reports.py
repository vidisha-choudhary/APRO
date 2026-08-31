"""Unit tests for Phase 8 evaluation reports and serialization."""

import json

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.recovery_prediction.classifiers import (
    LogisticRegressionOutcomeModel,
)
from apro.recovery_prediction.evaluation import (
    RecoveryOutcomeEvaluator,
)
from apro.recovery_prediction.reports import (
    generate_recovery_confusion_json,
    generate_recovery_evaluation_json,
    generate_recovery_evaluation_markdown,
    generate_recovery_model_manifest_json,
    generate_recovery_prediction_traces_jsonl,
)


def test_recovery_reports_generation() -> None:
    """AC-24: Test generating JSON, Markdown, confusion, and traces."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-rep-b-v1", [42], 25)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-rep-b-v1", [101], 10)

    model = LogisticRegressionOutcomeModel(max_iter=20)
    model.fit_on_dataset(train_ds)

    evaluator = RecoveryOutcomeEvaluator()
    metrics, traces = evaluator.evaluate_model(model, val_ds)

    # 1. Evaluation JSON
    eval_json = generate_recovery_evaluation_json(metrics.model_dump())
    assert isinstance(eval_json, str)
    parsed = json.loads(eval_json)
    assert parsed["case_count"] == 50

    # 2. Confusion JSON
    conf_json = generate_recovery_confusion_json(metrics.per_action_classification)
    assert isinstance(conf_json, str)
    parsed_conf = json.loads(conf_json)
    assert "format" in parsed_conf
    assert "matrices" in parsed_conf

    # 3. Traces JSONL
    traces_jsonl = generate_recovery_prediction_traces_jsonl(traces)
    trace_lines = [line for line in traces_jsonl.strip().split("\n") if line]
    assert len(trace_lines) == 50

    # 4. Manifest JSON
    artifact = model.to_artifact(
        training_dataset_version="train-rep-b-v1",
        training_seed=42,
    )
    manifest_json = generate_recovery_model_manifest_json(artifact)
    assert isinstance(manifest_json, str)
    parsed_man = json.loads(manifest_json)
    assert parsed_man["manifest_version"] == "1.0"
    assert parsed_man["model_name"] == model.model_name

    # 5. Markdown Report
    md_report = generate_recovery_evaluation_markdown(
        model_name=model.model_name,
        model_version=model.model_version,
        dataset_version="val-rep-b-v1",
        feature_schema_version=model.feature_schema_version,
        action_schema_version=model.action_schema_version,
        baseline_metrics={"Baseline": metrics},
        candidate_metrics={"Logistic": metrics},
        selected_model_name="Logistic",
        held_out_metrics=metrics,
    )
    assert "# APRO Phase 8 Recovery Outcome Prediction" in md_report
    assert "## 1. Executive Summary" in md_report
    assert "## 2. Validation Benchmark" in md_report
