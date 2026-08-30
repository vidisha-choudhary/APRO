"""Unit tests for Phase 7 report generation."""

import json

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.diagnosis.classifiers import (
    MultinomialLogisticRegressionDiagnosisModel,
)
from apro.diagnosis.evaluation import DiagnosisEvaluator
from apro.diagnosis.reports import (
    generate_confusion_matrix_json,
    generate_diagnosis_evaluation_json,
    generate_diagnosis_evaluation_markdown,
    generate_model_manifest_json,
    generate_prediction_traces_jsonl,
)


def test_diagnosis_reporting_functions() -> None:
    """AC-22: Test JSON, Markdown, confusion matrix, and traces report generators."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-rep-v1", [1], 20)
    test_ds = gen.generate_dataset(DatasetType.HELD_OUT_TEST, "test-rep-v1", [2], 10)

    model = MultinomialLogisticRegressionDiagnosisModel(max_iter=30)
    model.fit_on_dataset(train_ds)

    evaluator = DiagnosisEvaluator()
    metrics, traces = evaluator.evaluate_model(model, test_ds)
    err_analysis = evaluator.perform_error_analysis(traces)

    # 1. JSON Report
    json_str = generate_diagnosis_evaluation_json(metrics.model_dump())
    parsed = json.loads(json_str)
    assert parsed["case_count"] == 10
    assert "accuracy" in parsed

    # 2. Confusion Matrix JSON
    cm_json = generate_confusion_matrix_json(metrics.confusion_matrix)
    cm_parsed = json.loads(cm_json)
    assert len(cm_parsed["taxonomy_order"]) == 8
    assert len(cm_parsed["matrix"]) == 8

    # 3. Prediction Traces JSONL
    traces_jsonl = generate_prediction_traces_jsonl(traces)
    trace_lines = traces_jsonl.strip().split("\n")
    assert len(trace_lines) == 10

    # 4. Model Manifest JSON
    artifact = model.to_artifact()
    manifest_json = generate_model_manifest_json(artifact)
    assert "Multinomial Logistic Regression" in manifest_json

    # 5. Markdown Report
    md_report = generate_diagnosis_evaluation_markdown(
        model_name=model.model_name,
        model_version=model.model_version,
        dataset_version=test_ds.manifest.dataset_version,
        feature_schema_version=model.feature_schema_version,
        taxonomy_version=model.taxonomy_version,
        baseline_metrics={"Majority": metrics},
        candidate_metrics={"Logistic Regression": metrics},
        selected_model_name="Logistic Regression",
        held_out_metrics=metrics,
        error_analysis=err_analysis,
    )
    assert "# APRO Phase 7 Failure Diagnosis Evaluation Report" in md_report
    assert "Confusion Matrix" in md_report
    assert "Per-Class Performance Breakdown" in md_report
