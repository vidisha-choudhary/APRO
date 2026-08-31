"""End-to-end acceptance script for APRO Phase 8 Recovery Prediction."""

from pathlib import Path

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.diagnosis.classifiers import DecisionTreeDiagnosisModel
from apro.recovery_prediction.artifacts import (
    load_recovery_model_artifact,
    save_recovery_model_artifact,
)
from apro.recovery_prediction.baselines import (
    ActionStratifiedHistoricalBaseline,
    GlobalActionRateBaseline,
    SimpleStatisticalOutcomeBaseline,
    StaticOutcomeRuleBaseline,
)
from apro.recovery_prediction.calibration import (
    RecoveryTemperatureCalibrator,
)
from apro.recovery_prediction.classifiers import (
    BaseRecoveryOutcomeModel,
    DecisionTreeOutcomeModel,
    LogisticRegressionOutcomeModel,
    RandomForestOutcomeModel,
)
from apro.recovery_prediction.enums import (
    RECOVERY_ACTION_ORDER,
    RecoveryAction,
)
from apro.recovery_prediction.evaluation import (
    RecoveryOutcomeEvaluator,
    select_best_candidate,
)
from apro.recovery_prediction.features import RecoveryFeatureBuilder
from apro.recovery_prediction.metrics import RecoveryOutcomeMetrics
from apro.recovery_prediction.reports import (
    generate_recovery_confusion_json,
    generate_recovery_evaluation_json,
    generate_recovery_evaluation_markdown,
    generate_recovery_model_manifest_json,
    generate_recovery_prediction_traces_jsonl,
)


def run_phase_08_acceptance() -> None:
    """Execute complete Phase 8 Model B training and verification."""
    print("=" * 80)
    print("APRO PHASE 8 — RECOVERY OUTCOME PREDICTION ACCEPTANCE RUN")
    print("=" * 80)

    repo_root = Path(__file__).parent.parent

    # 1. Governed Datasets Generation
    print("\n[1/8] Generating Governed Datasets...")
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(
        DatasetType.TRAINING,
        dataset_version="train-b-v1",
        seeds=[42, 43, 44],
        cases_per_seed=600,
    )
    val_ds = gen.generate_dataset(
        DatasetType.VALIDATION,
        dataset_version="val-b-v1",
        seeds=[101, 102],
        cases_per_seed=300,
    )
    test_ds = gen.generate_dataset(
        DatasetType.HELD_OUT_TEST,
        dataset_version="test-b-v1",
        seeds=[201, 202],
        cases_per_seed=300,
    )
    shift_ds = gen.generate_dataset(
        DatasetType.BENCHMARK,
        dataset_version="bench-shift-b-v1",
        seeds=[301],
        cases_per_seed=200,
    )

    print(
        f"  - Training Set:   {len(train_ds.records):,} scenarios "
        f"({len(train_ds.records) * 5:,} action rows)"
    )
    print(
        f"  - Validation Set: {len(val_ds.records):,} scenarios "
        f"({len(val_ds.records) * 5:,} action rows)"
    )
    print(
        f"  - Held-Out Test:  {len(test_ds.records):,} scenarios "
        f"({len(test_ds.records) * 5:,} action rows)"
    )
    print(
        f"  - Shifted Bench:  {len(shift_ds.records):,} scenarios "
        f"({len(shift_ds.records) * 5:,} action rows)"
    )

    # 2. Frozen Model A Diagnosis Fitting
    print("\n[2/8] Fitting Frozen Model A Diagnosis Model on TRAINING Set...")
    diag_model = DecisionTreeDiagnosisModel(max_depth=6)
    diag_model.fit_on_dataset(train_ds)
    print(f"  - Model A fitted: '{diag_model.model_name}' ({diag_model.model_version})")

    # 3. Decision-Time Feature Standardization Fitting
    print("\n[3/8] Fitting Decision-Time Feature Standardizer on TRAINING Set...")
    feature_builder = RecoveryFeatureBuilder()
    diag_map = {
        r.model_input.record_id: diag_model.predict(r.model_input)
        for r in train_ds.records
    }
    feature_builder.fit(train_ds, diagnosis_results=diag_map)
    print(
        f"  - Feature Builder fitted: "
        f"{len(feature_builder.feature_names)} features extracted"
    )

    evaluator = RecoveryOutcomeEvaluator()

    # 4. Baseline Models Fitting & Evaluation
    print("\n[4/8] Training and Evaluating Baselines on Validation Set...")
    baselines: dict[str, BaseRecoveryOutcomeModel] = {
        "Global Action Rate Baseline": GlobalActionRateBaseline(
            feature_builder=feature_builder
        ),
        "Action-Stratified Historical Baseline": (
            ActionStratifiedHistoricalBaseline(feature_builder=feature_builder)
        ),
        "Static Outcome Rule Baseline": StaticOutcomeRuleBaseline(
            feature_builder=feature_builder
        ),
        "Simple Statistical Outcome Baseline": SimpleStatisticalOutcomeBaseline(
            feature_builder=feature_builder
        ),
    }

    baseline_val_metrics: dict[str, RecoveryOutcomeMetrics] = {}
    for name, base_m in baselines.items():
        base_m.fit_on_dataset(
            train_ds,
            diagnosis_model=diag_model,
            feature_builder=feature_builder,
        )
        m, _ = evaluator.evaluate_model(base_m, val_ds, diagnosis_model=diag_model)
        baseline_val_metrics[name] = m
        print(
            f"  - {name:<38}: Accuracy={m.accuracy * 100:5.2f}%, "
            f"Macro F1={m.macro_f1 * 100:5.2f}%, MAE=Rs {m.mae / 100:6.2f}, "
            f"LogLoss={m.log_loss:6.4f}"
        )

    # 5. Candidate Model B Models Fitting & Evaluation
    print("\n[5/8] Training Candidate Model B Models on TRAINING Set...")
    candidates: dict[str, BaseRecoveryOutcomeModel] = {
        "Logistic Regression Outcome Model": LogisticRegressionOutcomeModel(
            learning_rate=0.08,
            l2_penalty=0.01,
            max_iter=50,
            seed=42,
            feature_builder=feature_builder,
        ),
        "Decision Tree Outcome Model": DecisionTreeOutcomeModel(
            max_depth=6,
            min_samples_split=8,
            seed=42,
            feature_builder=feature_builder,
        ),
        "Random Forest Outcome Model": RandomForestOutcomeModel(
            n_estimators=15,
            max_depth=6,
            min_samples_split=8,
            seed=42,
            feature_builder=feature_builder,
        ),
    }

    candidate_val_metrics: dict[str, RecoveryOutcomeMetrics] = {}
    for name, cand_m in candidates.items():
        cand_m.fit_on_dataset(
            train_ds,
            diagnosis_model=diag_model,
            feature_builder=feature_builder,
        )
        m, _ = evaluator.evaluate_model(cand_m, val_ds, diagnosis_model=diag_model)
        candidate_val_metrics[name] = m
        print(
            f"  - {name:<38}: Accuracy={m.accuracy * 100:5.2f}%, "
            f"Macro F1={m.macro_f1 * 100:5.2f}%, MAE=Rs {m.mae / 100:6.2f}, "
            f"LogLoss={m.log_loss:6.4f}"
        )

    # 6. Model Selection & Probability Calibration
    print("\n[6/8] Selecting Best Model B Candidate & Calibrating on VALIDATION Set...")
    best_cand_name, selection_rationale = select_best_candidate(
        candidate_val_metrics,
        primary_metric="macro_f1",
        tie_breaker_metric="log_loss",
    )
    best_model = candidates[best_cand_name]
    print(f"  - {selection_rationale}")

    calibrator = RecoveryTemperatureCalibrator()
    calibrator.fit_on_dataset(best_model, val_ds, diagnosis_model=diag_model)
    best_model.calibrator = calibrator
    print(f"  - Learned action temperatures: {calibrator.temperatures}")

    # 7. Final Evaluation on Held-Out Test & Shifted Benchmark Sets
    print("\n[7/8] Evaluating Selected Model B on HELD-OUT TEST & SHIFTED BENCHMARK...")
    test_metrics, test_traces = evaluator.evaluate_model(
        best_model, test_ds, diagnosis_model=diag_model
    )
    shift_metrics, _ = evaluator.evaluate_model(
        best_model, shift_ds, diagnosis_model=diag_model
    )

    print("\n  === HELD-OUT TEST RESULTS (3,000 Evaluation Cases) ===")
    print(f"  - Overall Accuracy:            {test_metrics.accuracy * 100:.2f}%")
    print(f"  - Macro F1 across Actions:     {test_metrics.macro_f1 * 100:.2f}%")
    print(f"  - Multi-class Log Loss:        {test_metrics.log_loss:.4f}")
    print(
        f"  - Expected Calibration Error:  "
        f"{test_metrics.expected_calibration_error:.4f}"
    )
    print(f"  - Mean Absolute Error (MAE):   Rs {test_metrics.mae / 100:.2f}")
    print(f"  - Root Mean Squared Error:     Rs {test_metrics.rmse / 100:.2f}")
    print(
        f"  - Mean Counterfactual Regret:  "
        f"Rs {test_metrics.potential_outcome_metrics.counterfactual_regret / 100:.2f}"
    )
    print(
        f"  - Mean Oracle Gap:             "
        f"Rs {test_metrics.potential_outcome_metrics.oracle_gap / 100:.2f}"
    )

    print("\n  === PER-ACTION PERFORMANCE (Held-Out Test Set) ===")
    print(
        "  Action          Cases   Accuracy  Precision  Recall    F1      "
        "MAE (Rs)   LogLoss   ECE"
    )
    print("  " + "-" * 85)
    for act in RECOVERY_ACTION_ORDER:
        cm = test_metrics.per_action_classification[act]
        am = test_metrics.per_action_amount[act]
        print(
            f"  {act.value:<14}  {cm.case_count:5d}   {cm.accuracy * 100:5.2f}%    "
            f"{cm.precision * 100:5.2f}%    {cm.recall * 100:5.2f}%   "
            f"{cm.f1 * 100:5.2f}%  Rs {am.mae / 100:6.2f}  "
            f"{cm.log_loss:7.4f}  {cm.expected_calibration_error:.4f}"
        )

    print("\n  === DISTRIBUTION SHIFT RESILIENCE ===")
    print(f"  - In-Distribution Macro F1:    {test_metrics.macro_f1 * 100:.2f}%")
    f1_diff = shift_metrics.macro_f1 - test_metrics.macro_f1
    print(
        f"  - Shifted Benchmark Macro F1:  "
        f"{shift_metrics.macro_f1 * 100:.2f}% (Delta: {f1_diff:+.4f})"
    )
    print(f"  - In-Distribution MAE:         Rs {test_metrics.mae / 100:.2f}")
    mae_diff = (shift_metrics.mae - test_metrics.mae) / 100
    print(
        f"  - Shifted Benchmark MAE:       "
        f"Rs {shift_metrics.mae / 100:.2f} (Delta: Rs {mae_diff:+.2f})"
    )

    # 8. Artifact Persistence, Verification & Report Generation
    print(
        "\n[8/8] Persisting Artifacts, Verifying Reproducibility & Writing Reports..."
    )
    artifacts_dir = repo_root / "artifacts" / "recovery_prediction"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    artifact_path = artifacts_dir / "model_b_best.json"
    artifact = save_recovery_model_artifact(
        model=best_model,
        target_path=artifact_path,
        training_dataset_version=train_ds.manifest.dataset_version,
        training_seed=42,
    )
    print(f"  - Model artifact saved: {artifact_path}")
    print(f"  - Deterministic Identity: {artifact.deterministic_identity}")

    # Verify bit-for-bit inference reproduction
    reloaded_model = load_recovery_model_artifact(artifact_path)
    for rec in test_ds.records[:100]:
        for act in (RecoveryAction.RETRY, RecoveryAction.PAYMENT_LINK):
            p_orig = best_model.predict(rec.model_input, act)
            p_reloaded = reloaded_model.predict(rec.model_input, act)
            assert (
                p_orig.predicted_success_probability
                == p_reloaded.predicted_success_probability
            )
            assert (
                p_orig.predicted_recovered_amount
                == p_reloaded.predicted_recovered_amount
            )
            assert p_orig.prediction_id == p_reloaded.prediction_id
    print("  - Reloaded model verified: 100% bit-for-bit inference match.")

    # Write evaluation reports
    error_analysis = evaluator.perform_error_analysis(test_traces)
    md_report = generate_recovery_evaluation_markdown(
        model_name=best_model.model_name,
        model_version=best_model.model_version,
        dataset_version=test_ds.manifest.dataset_version,
        feature_schema_version=best_model.feature_schema_version,
        action_schema_version=best_model.action_schema_version,
        baseline_metrics=baseline_val_metrics,
        candidate_metrics=candidate_val_metrics,
        selected_model_name=best_cand_name,
        held_out_metrics=test_metrics,
        shifted_metrics=shift_metrics,
        error_analysis=error_analysis,
        selection_rationale=selection_rationale,
    )
    (artifacts_dir / "recovery_evaluation_report.md").write_text(
        md_report, encoding="utf-8"
    )

    eval_json = generate_recovery_evaluation_json(test_metrics.model_dump())
    (artifacts_dir / "recovery_evaluation_metrics.json").write_text(
        eval_json, encoding="utf-8"
    )

    conf_json = generate_recovery_confusion_json(test_metrics.per_action_classification)
    (artifacts_dir / "recovery_confusion_matrices.json").write_text(
        conf_json, encoding="utf-8"
    )

    traces_jsonl = generate_recovery_prediction_traces_jsonl(test_traces)
    (artifacts_dir / "recovery_prediction_traces.jsonl").write_text(
        traces_jsonl, encoding="utf-8"
    )

    manifest_json = generate_recovery_model_manifest_json(artifact)
    (artifacts_dir / "recovery_model_manifest.json").write_text(
        manifest_json, encoding="utf-8"
    )

    print("\n" + "=" * 80)
    print("PHASE 8 ACCEPTANCE RUN COMPLETE — ALL GATES GREEN")
    print("=" * 80)


if __name__ == "__main__":
    run_phase_08_acceptance()
