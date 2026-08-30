"""Unit tests for Phase 7 Diagnosis Taxonomy and Enumerations."""

from apro.diagnosis.enums import (
    DIAGNOSIS_TAXONOMY_ORDER,
    DIAGNOSIS_TAXONOMY_VERSION,
    DiagnosisCategory,
    UncertaintyState,
)


def test_diagnosis_taxonomy_order_and_count() -> None:
    """AC-01: Verify all 8 normalized failure categories and deterministic order."""
    expected_categories = [
        DiagnosisCategory.TRANSIENT_FAILURE,
        DiagnosisCategory.BANK_SIDE_FAILURE,
        DiagnosisCategory.CUSTOMER_SIDE_FAILURE,
        DiagnosisCategory.AUTHENTICATION_FAILURE,
        DiagnosisCategory.PAYMENT_METHOD_FAILURE,
        DiagnosisCategory.GATEWAY_FAILURE,
        DiagnosisCategory.TIMEOUT,
        DiagnosisCategory.UNKNOWN_FAILURE,
    ]

    assert len(DIAGNOSIS_TAXONOMY_ORDER) == 8
    assert list(DIAGNOSIS_TAXONOMY_ORDER) == expected_categories
    assert DIAGNOSIS_TAXONOMY_VERSION == "diagnosis-taxonomy-v1"


def test_uncertainty_states() -> None:
    """Verify uncertainty states are well-defined."""
    states = list(UncertaintyState)
    assert UncertaintyState.HIGH_CONFIDENCE in states
    assert UncertaintyState.MEDIUM_CONFIDENCE in states
    assert UncertaintyState.LOW_CONFIDENCE in states
    assert UncertaintyState.ABSTAIN in states
