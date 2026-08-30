"""Diagnosis label construction from Phase 6 evaluation ground truth."""

from apro.dataset.models import EvaluationTruthRecord, GovernedDataset
from apro.diagnosis.enums import (
    DIAGNOSIS_TAXONOMY_VERSION,
    DiagnosisCategory,
)
from apro.diagnosis.models import DiagnosisLabel
from apro.simulation.enums import ScenarioFamily

SCENARIO_FAMILY_TO_DIAGNOSIS_CATEGORY: dict[ScenarioFamily, DiagnosisCategory] = {
    ScenarioFamily.TRANSIENT_FAILURE: DiagnosisCategory.TRANSIENT_FAILURE,
    ScenarioFamily.BANK_SIDE_FAILURE: DiagnosisCategory.BANK_SIDE_FAILURE,
    ScenarioFamily.CUSTOMER_SIDE_FAILURE: DiagnosisCategory.CUSTOMER_SIDE_FAILURE,
    ScenarioFamily.AUTHENTICATION_FAILURE: DiagnosisCategory.AUTHENTICATION_FAILURE,
    ScenarioFamily.PAYMENT_METHOD_FAILURE: DiagnosisCategory.PAYMENT_METHOD_FAILURE,
    ScenarioFamily.GATEWAY_FAILURE: DiagnosisCategory.GATEWAY_FAILURE,
    ScenarioFamily.TIMEOUT: DiagnosisCategory.TIMEOUT,
    ScenarioFamily.UNKNOWN_FAILURE: DiagnosisCategory.UNKNOWN_FAILURE,
}


def construct_diagnosis_label(
    truth_record: EvaluationTruthRecord,
) -> DiagnosisLabel:
    """Construct a supervised DiagnosisLabel from an EvaluationTruthRecord."""
    if truth_record.scenario_family not in SCENARIO_FAMILY_TO_DIAGNOSIS_CATEGORY:
        msg = (
            f"Unrecognized scenario family '{truth_record.scenario_family}' "
            "cannot be mapped to diagnosis taxonomy."
        )
        raise ValueError(msg)

    cat = SCENARIO_FAMILY_TO_DIAGNOSIS_CATEGORY[truth_record.scenario_family]
    return DiagnosisLabel(
        record_id=truth_record.record_id,
        scenario_id=truth_record.scenario_id,
        failure_category=cat,
        taxonomy_version=DIAGNOSIS_TAXONOMY_VERSION,
        label_source="governed_simulator_ground_truth",
    )


def construct_labels_from_dataset(
    dataset: GovernedDataset,
) -> list[DiagnosisLabel]:
    """Construct supervised diagnosis labels for all records in a GovernedDataset."""
    labels: list[DiagnosisLabel] = []
    for rec in dataset.records:
        labels.append(construct_diagnosis_label(rec.evaluation_truth))
    return labels
