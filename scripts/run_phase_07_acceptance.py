"""Manual End-to-End Acceptance Script for APRO Phase 7 Failure Diagnosis (Model A)."""

from pathlib import Path

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.diagnosis.artifacts import (
    load_model_artifact,
    save_model_artifact,
)
from apro.diagnosis.baselines import (
    HistoricalConditionalBaseline,
    MajorityClassBaseline,
    NaiveBayesDiagnosisModel,
    ProviderRuleBaseline,
)
from apro.diagnosis.calibration import TemperatureCalibrator
from apro.diagnosis.classifiers import (
    DecisionTreeDiagnosisModel,
    MultinomialLogisticRegressionDiagnosisModel,
    RandomForestDiagnosisModel,
)
from apro.diagnosis.enums import (
    DIAGNOSIS_TAXONOMY_ORDER,
)
from apro.diagnosis.evaluation import (
    DiagnosisEvaluator,
    select_best_candidate,
)
from apro.diagnosis.features import (
    DIAGNOSIS_FEATURE_SCHEMA_VERSION,
    DiagnosisFeatureBuilder,
)
from apro.diagnosis.labels import construct_labels_from_dataset
from apro.diagnosis.reports import (
    generate_confusion_matrix_json,
    generate_diagnosis_evaluation_json,
    generate_diagnosis_evaluation_markdown,
    generate_model_manifest_json,
    generate_prediction_traces_jsonl,
)
from apro.evaluation.benchmark import BenchmarkConfig, BenchmarkRunner
from apro.simulation.config import SimulationConfig


def run_phase_07_acceptance() -> None:
    print("=" * 80)
    print("APRO PHASE 7 -- FAILURE DIAGNOSIS INTELLIGENCE (MODEL A) ACCEPTANCE RUN")
    print("=" * 80)

    artifacts_dir = Path("artifacts/phase_07")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # 1. Dataset Generation
    seeds = [42, 101, 2026]
    gen = DatasetGenerator()

    print("\n[1/7] Generating Governed Datasets (Phase 6 contracts)...")
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "phase7-train-v1", seeds, 600)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "phase7-val-v1", seeds, 200)
    test_ds = gen.generate_dataset(
        DatasetType.HELD_OUT_TEST, "phase7-test-v1", seeds, 200
    )

    # Shifted benchmark
    runner = BenchmarkRunner()
    shifted_sim_config = SimulationConfig(
        scenario_family_weights={
            "TRANSIENT_FAILURE": 0.05,
            "BANK_SIDE_FAILURE": 0.10,
            "CUSTOMER_SIDE_FAILURE": 0.05,
            "AUTHENTICATION_FAILURE": 0.10,
            "PAYMENT_METHOD_FAILURE": 0.05,
            "GATEWAY_FAILURE": 0.15,
            "TIMEOUT": 0.45,
            "UNKNOWN_FAILURE": 0.05,
        }
    )
    shifted_config = BenchmarkConfig(
        benchmark_version="phase7-bench-shifted-v1",
        target_case_count=200,
        seeds=seeds,
        simulation_config=shifted_sim_config,
        distribution_shift_name="high_timeout_stress",
    )
    shifted_ds = runner.generate_benchmark_dataset(shifted_config)

    print(f"  - Training Cases:   {len(train_ds.records):,}")
    print(f"  - Validation Cases: {len(val_ds.records):,}")
    print(f"  - Held-Out Cases:   {len(test_ds.records):,}")
    print(f"  - Shifted Cases:    {len(shifted_ds.records):,}")

    # 2. Diagnosis Labels and Class Distribution
    train_labels = construct_labels_from_dataset(train_ds)

    print("\n[2/7] Class Distribution (Training Dataset):")
    class_counts: dict[str, int] = dict.fromkeys(
        [c.value for c in DIAGNOSIS_TAXONOMY_ORDER], 0
    )
    for lbl in train_labels:
        class_counts[lbl.failure_category.value] += 1
    for cat_name, cnt in class_counts.items():
        print(f"  - {cat_name:<25}: {cnt:4d} ({cnt / len(train_labels) * 100:.1f}%)")

    # 3. Decision-Time Feature Extraction (Fitting strictly on TRAINING)
    print("\n[3/7] Extracting and Standardizing Decision-Time Features...")
    builder = DiagnosisFeatureBuilder(schema_version=DIAGNOSIS_FEATURE_SCHEMA_VERSION)
    builder.fit(train_ds)
    print(f"  - Schema Version: {builder.schema_version}")
    print(f"  - Feature Count:  {len(builder.feature_names)}")

    val_feats = builder.transform_dataset(val_ds)
    test_feats = builder.transform_dataset(test_ds)
    shifted_feats = builder.transform_dataset(shifted_ds)

    # 4. Baselines Evaluation (Validation Set)
    print("\n[4/7] Evaluating Baselines (Validation Set)...")
    evaluator = DiagnosisEvaluator()
    baseline_models = {
        "Majority Class": MajorityClassBaseline(feature_builder=builder),
        "Provider Rules": ProviderRuleBaseline(feature_builder=builder),
        "Historical Conditional": HistoricalConditionalBaseline(
            feature_builder=builder
        ),
        "Naive Bayes": NaiveBayesDiagnosisModel(feature_builder=builder),
    }

    baseline_metrics = {}
    for name, base_model in baseline_models.items():
        base_model.fit_on_dataset(train_ds)
        m, _ = evaluator.evaluate_model(base_model, val_ds, val_feats)
        baseline_metrics[name] = m
        print(
            f"  - {name:<23} | Acc: {m.accuracy * 100:5.2f}% | "
            f"Macro F1: {m.macro_f1 * 100:5.2f}% | LogLoss: {m.log_loss:6.4f}"
        )

    # 5. Candidate Models Training & Validation Selection
    print("\n[5/7] Training Candidate Classifiers & Validation Model Selection...")
    candidates = {
        "Logistic Regression (Softmax L2)": (
            MultinomialLogisticRegressionDiagnosisModel(
                max_iter=300, learning_rate=0.08, l2_reg=0.01, feature_builder=builder
            )
        ),
        "Decision Tree (Gini Depth=6)": DecisionTreeDiagnosisModel(
            max_depth=6, min_samples_split=8, feature_builder=builder
        ),
        "Random Forest (15 Trees)": RandomForestDiagnosisModel(
            n_estimators=15, max_depth=7, feature_builder=builder
        ),
    }

    candidate_metrics = {}
    for name, cand_model in candidates.items():
        cand_model.fit_on_dataset(train_ds)
        m, _ = evaluator.evaluate_model(cand_model, val_ds, val_feats)
        candidate_metrics[name] = m
        print(
            f"  - {name:<32} | Acc: {m.accuracy * 100:5.2f}% | "
            f"Macro F1: {m.macro_f1 * 100:5.2f}% | LogLoss: {m.log_loss:6.4f} | "
            f"ECE: {m.expected_calibration_error:.4f}"
        )

    # Explicit Model Selection using configured Primary Metric + Tie-Breaker
    best_candidate_name, selection_rationale = select_best_candidate(
        candidate_metrics, primary_metric="macro_f1", tie_breaker_metric="log_loss"
    )

    print(f"\n>>> Model A Selection: {selection_rationale}")

    selected_model = candidates[best_candidate_name]

    # Probability Calibration (Fit Temperature Scaling on VALIDATION Set)
    print("\n[6/7] Fitting Probability Calibration on Validation Set...")
    calibrator = TemperatureCalibrator()
    calibrator.fit_on_dataset(selected_model, val_ds)
    selected_model.calibrator = calibrator
    print(f"  - Optimal Learned Temperature: {calibrator.temperature:.4f}")

    # Persist & Reload Model Artifact
    artifact_path = artifacts_dir / "model_a_diagnosis.json"
    saved_artifact = save_model_artifact(
        selected_model,
        artifact_path,
        training_dataset_version=train_ds.manifest.dataset_version,
        training_seed=42,
    )
    print(f"  - Model Artifact Persisted: {artifact_path}")
    print(f"  - Actual Created At:        {saved_artifact.created_at}")
    print(f"  - Deterministic Identity:   {saved_artifact.deterministic_identity}")

    loaded_model = load_model_artifact(artifact_path)
    print("  - Model Artifact Reloaded and Verified Compatible.")

    # 6. Final Held-Out Test Evaluation
    print("\n[7/7] Executing Final Held-Out Evaluation & Error Analysis...")
    held_out_metrics, held_out_traces = evaluator.evaluate_model(
        loaded_model, test_ds, test_feats
    )
    shifted_metrics, _ = evaluator.evaluate_model(
        loaded_model, shifted_ds, shifted_feats
    )

    error_analysis = evaluator.perform_error_analysis(held_out_traces)
    shift_comparison = evaluator.compare_distribution_shift(
        held_out_metrics, shifted_metrics
    )

    print("\n================ FINAL HELD-OUT PERFORMANCE ================")
    print(f"  Accuracy:                   {held_out_metrics.accuracy * 100:6.2f}%")
    b_acc = held_out_metrics.balanced_accuracy * 100
    print(f"  Balanced Accuracy:          {b_acc:6.2f}%")
    print(
        f"  Macro Precision:            {held_out_metrics.macro_precision * 100:6.2f}%"
    )
    print(f"  Macro Recall:               {held_out_metrics.macro_recall * 100:6.2f}%")
    print(f"  Macro F1 Score:             {held_out_metrics.macro_f1 * 100:6.2f}%")
    print(f"  Weighted F1 Score:          {held_out_metrics.weighted_f1 * 100:6.2f}%")
    print(
        f"  Top-2 Accuracy:             {held_out_metrics.top_2_accuracy * 100:6.2f}%"
    )
    print(f"  Multi-class Log Loss:       {held_out_metrics.log_loss:6.4f}")
    print(f"  Brier Score:                {held_out_metrics.brier_score:6.4f}")
    ece = held_out_metrics.expected_calibration_error
    print(f"  ECE:                        {ece:6.4f}")
    lat = held_out_metrics.average_decision_latency_ms
    print(f"  Avg Latency:                {lat:6.4f} ms/decision")

    print("\nConfusion Matrix (Held-Out Test Set):")
    classes = [c.value[:5] for c in DIAGNOSIS_TAXONOMY_ORDER]
    print("Act \\ Pred | " + "  ".join(f"{c:>5}" for c in classes))
    print("-" * 65)
    for i, row in enumerate(held_out_metrics.confusion_matrix):
        print(f"{classes[i]:<10} | " + "  ".join(f"{val:>5}" for val in row))

    print("\nDistribution Shift Comparison (In-Distribution vs Shifted Benchmark):")
    print(
        f"  Macro F1: {held_out_metrics.macro_f1 * 100:.2f}% -> "
        f"{shifted_metrics.macro_f1 * 100:.2f}% "
        f"(delta {shift_comparison['deltas']['macro_f1_delta']:+.4f})"
    )
    print(
        f"  Accuracy: {held_out_metrics.accuracy * 100:.2f}% -> "
        f"{shifted_metrics.accuracy * 100:.2f}% "
        f"(delta {shift_comparison['deltas']['accuracy_delta']:+.4f})"
    )
    print(
        f"  Log Loss: {held_out_metrics.log_loss:.4f} -> "
        f"{shifted_metrics.log_loss:.4f} "
        f"(delta {shift_comparison['deltas']['log_loss_delta']:+.4f})"
    )

    # 7. Reproducibility Proof
    print("\nVerifying Deterministic Reproducibility from Loaded Model...")
    second_metrics, second_traces = evaluator.evaluate_model(
        loaded_model, test_ds, test_feats
    )
    assert held_out_metrics.accuracy == second_metrics.accuracy
    assert held_out_metrics.macro_f1 == second_metrics.macro_f1
    assert held_out_metrics.log_loss == second_metrics.log_loss
    assert held_out_metrics.confusion_matrix == second_metrics.confusion_matrix

    # Complete prediction object equality across test cases
    for rec in test_ds.records:
        r1 = loaded_model.predict(rec.model_input)
        r2 = loaded_model.predict(rec.model_input)
        assert r1.model_dump() == r2.model_dump()
        assert r1.prediction_id == r2.prediction_id

    print(
        "  [OK] Canonical Reproducibility Verified "
        "(Identical Prediction Dumps & Metrics)."
    )

    # 8. Generate and Persist Reports
    print("\nWriting Evaluation Reports...")
    eval_json_path = artifacts_dir / "diagnosis_evaluation.json"
    eval_json_data = held_out_metrics.model_dump()
    eval_json_data["selection_decision"] = selection_rationale
    eval_json_path.write_text(
        generate_diagnosis_evaluation_json(eval_json_data),
        encoding="utf-8",
    )

    cm_path = artifacts_dir / "confusion_matrix.json"
    cm_path.write_text(
        generate_confusion_matrix_json(held_out_metrics.confusion_matrix),
        encoding="utf-8",
    )

    manifest_path = artifacts_dir / "model_manifest.json"
    manifest_path.write_text(
        generate_model_manifest_json(loaded_model.to_artifact()),
        encoding="utf-8",
    )

    trace_path = artifacts_dir / "prediction_trace.jsonl"
    trace_path.write_text(
        generate_prediction_traces_jsonl(held_out_traces), encoding="utf-8"
    )

    md_report_path = artifacts_dir / "diagnosis_evaluation.md"
    md_report_path.write_text(
        generate_diagnosis_evaluation_markdown(
            model_name=loaded_model.model_name,
            model_version=loaded_model.model_version,
            dataset_version=test_ds.manifest.dataset_version,
            feature_schema_version=loaded_model.feature_schema_version,
            taxonomy_version=loaded_model.taxonomy_version,
            baseline_metrics=baseline_metrics,
            candidate_metrics=candidate_metrics,
            selected_model_name=best_candidate_name,
            held_out_metrics=held_out_metrics,
            shifted_metrics=shifted_metrics,
            error_analysis=error_analysis,
            selection_rationale=selection_rationale,
        ),
        encoding="utf-8",
    )
    print(f"  [OK] Reports generated in '{artifacts_dir}'")
    print("\nPHASE 7 ACCEPTANCE RUN COMPLETE -- ALL GATES GREEN!")


if __name__ == "__main__":
    run_phase_07_acceptance()
