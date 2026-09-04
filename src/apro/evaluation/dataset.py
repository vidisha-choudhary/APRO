"""Dataset snapshot loading, hashing, eligibility, and truth isolation."""

import hashlib
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apro.evaluation.config import EvaluationConfig
from apro.evaluation.enums import (
    CensoringPolicy,
    EvaluationCaseStatus,
)
from apro.evaluation.exceptions import (
    CheatingViolationError,
    DatasetInvalidError,
)
from apro.evaluation.models import (
    BenchmarkCaseRecord,
    CaseEligibilityResult,
)


def compute_deterministic_snapshot_hash(
    records: list[BenchmarkCaseRecord] | tuple[BenchmarkCaseRecord, ...],
) -> str:
    """Compute deterministic SHA-256 hash over canonical benchmark records."""
    if not records:
        return hashlib.sha256(b"empty_dataset").hexdigest()

    sorted_recs = sorted(records, key=lambda r: r.case_id)
    canonical_items: list[dict[str, Any]] = []

    for r in sorted_recs:
        item = {
            "case_id": r.case_id,
            "payment_id": r.payment_id,
            "payment_amount": r.payment_amount,
            "currency": r.currency,
            "payment_method": r.payment_method,
            "case_status": r.case_status,
            "failure_code": r.failure_code,
            "opened_at": r.opened_at.isoformat(),
            "closed_at": r.closed_at.isoformat() if r.closed_at else None,
            "is_recovered": r.is_recovered,
            "recovered_amount": r.recovered_amount,
            "cycle_count": r.cycle_count,
            "executions_count": len(r.executions),
            "outcomes_count": len(r.outcomes),
        }
        canonical_items.append(item)

    canonical_json = json.dumps(canonical_items, sort_keys=True)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class BenchmarkDatasetSnapshot(BaseModel):
    """Immutable benchmark dataset snapshot with cryptographic fingerprint."""

    model_config = ConfigDict(frozen=True)

    dataset_id: str = "apro-benchmark-v1"
    dataset_version: str = "1.0.0"
    created_at: str
    snapshot_hash: str
    records: tuple[BenchmarkCaseRecord, ...] = Field(default_factory=tuple)

    @classmethod
    def from_records(
        cls,
        records: list[BenchmarkCaseRecord] | tuple[BenchmarkCaseRecord, ...],
        dataset_id: str = "apro-benchmark-v1",
        dataset_version: str = "1.0.0",
        created_at: str | None = None,
    ) -> "BenchmarkDatasetSnapshot":
        """Construct an immutable benchmark dataset snapshot from records."""
        if not records:
            raise DatasetInvalidError(
                "Cannot create a benchmark snapshot with empty records."
            )

        rec_tuple = tuple(records)
        s_hash = compute_deterministic_snapshot_hash(rec_tuple)
        iso_now = created_at or records[0].opened_at.isoformat()

        return cls(
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            created_at=iso_now,
            snapshot_hash=s_hash,
            records=rec_tuple,
        )

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> BenchmarkCaseRecord:
        return self.records[index]


class EligibilityClassifier:
    """Deterministic case accounting and eligibility evaluation."""

    @staticmethod
    def classify_case(
        record: BenchmarkCaseRecord,
        config: EvaluationConfig,
        seen_case_ids: set[str] | None = None,
    ) -> CaseEligibilityResult:
        """Classify a single case record for benchmark eligibility."""
        # 1. Duplicate detection
        if seen_case_ids is not None:
            if record.case_id in seen_case_ids:
                return CaseEligibilityResult(
                    case_id=record.case_id,
                    status=EvaluationCaseStatus.DUPLICATE_CASE,
                    exclusion_reason="Duplicate case_id encountered in dataset",
                    is_eligible=False,
                )
            seen_case_ids.add(record.case_id)

        # 2. Invalid Case Checks
        if record.payment_amount <= 0:
            return CaseEligibilityResult(
                case_id=record.case_id,
                status=EvaluationCaseStatus.INVALID_CASE,
                exclusion_reason="Non-positive payment amount",
                is_eligible=False,
            )

        # 3. Missing required artifacts
        is_exclude_policy = (
            config.missing_data_policy == config.missing_data_policy.EXCLUDE_CASE
        )
        if (
            is_exclude_policy
            and not record.executions
            and record.case_status not in ("CLOSED_STOPPED", "STOPPED")
        ):
            return CaseEligibilityResult(
                case_id=record.case_id,
                status=EvaluationCaseStatus.MISSING_REQUIRED_ARTIFACT,
                exclusion_reason="Missing execution artifacts for non-stopped case",
                is_eligible=False,
            )

        # 4. Pending / Censored Checks
        is_pending = (
            "PENDING" in record.case_status.upper()
            or "OPEN" in record.case_status.upper()
        )
        if is_pending:
            if config.censoring_policy == CensoringPolicy.EXCLUDE:
                return CaseEligibilityResult(
                    case_id=record.case_id,
                    status=EvaluationCaseStatus.CENSORED,
                    exclusion_reason="Pending case excluded under censoring policy",
                    is_eligible=False,
                )
            if config.censoring_policy == CensoringPolicy.RIGHT_CENSOR:
                return CaseEligibilityResult(
                    case_id=record.case_id,
                    status=EvaluationCaseStatus.PENDING,
                    exclusion_reason="Pending case right-censored",
                    is_eligible=True,
                )

        # 5. Unknown outcome checks
        if record.case_status == "UNKNOWN":
            return CaseEligibilityResult(
                case_id=record.case_id,
                status=EvaluationCaseStatus.UNKNOWN,
                exclusion_reason="Unknown case status",
                is_eligible=True,
            )

        # 6. Eligible
        return CaseEligibilityResult(
            case_id=record.case_id,
            status=EvaluationCaseStatus.ELIGIBLE,
            exclusion_reason=None,
            is_eligible=True,
        )

    @classmethod
    def filter_and_account_cases(
        cls,
        records: list[BenchmarkCaseRecord] | tuple[BenchmarkCaseRecord, ...],
        config: EvaluationConfig,
    ) -> tuple[list[BenchmarkCaseRecord], list[CaseEligibilityResult], dict[str, int]]:
        """Filter dataset records into eligible cohort and count all exclusions."""
        seen_ids: set[str] = set()
        eligible_records: list[BenchmarkCaseRecord] = []
        classification_results: list[CaseEligibilityResult] = []
        counts: dict[str, int] = {
            "total_cases": len(records),
            "eligible": 0,
            "excluded": 0,
            "missing_required_artifact": 0,
            "invalid_case": 0,
            "duplicate_case": 0,
            "pending": 0,
            "unknown": 0,
            "censored": 0,
        }

        for r in records:
            res = cls.classify_case(r, config, seen_ids)
            classification_results.append(res)

            status_key = res.status.value.lower()
            if status_key in counts and status_key != "eligible":
                counts[status_key] += 1

            if res.is_eligible:
                counts["eligible"] += 1
                eligible_records.append(r)
            else:
                counts["excluded"] += 1

        return eligible_records, classification_results, counts


class TruthPlaneSeparation:
    """Strict structural and dynamic anti-cheating isolation validator."""

    @staticmethod
    def verify_isolation(
        records: list[BenchmarkCaseRecord] | tuple[BenchmarkCaseRecord, ...],
    ) -> None:
        """Verify that offline truth is structurally isolated from runtime inputs."""
        oracle_keys = {
            "ground_truth_recovered",
            "ground_truth_recovered_amount",
            "ground_truth_best_action",
            "ground_truth_failure_class",
            "counterfactual_outcomes",
            "latent_customer_intent",
            "latent_bank_condition",
            "true_action_probabilities",
            "potential_outcomes",
            "oracle_action",
            "hidden_recoverability",
        }

        for r in records:
            for d in r.decisions:
                if any(k in str(d.reason) for k in oracle_keys):
                    msg = (
                        f"Oracle truth leaked into runtime Decision "
                        f"{d.decision_id} in case {r.case_id}"
                    )
                    raise CheatingViolationError(msg)
            for pd in r.policy_decisions:
                if any(k in str(pd.reason) for k in oracle_keys):
                    msg = (
                        f"Oracle truth leaked into runtime PolicyDecision "
                        f"{pd.policy_decision_id} in case {r.case_id}"
                    )
                    raise CheatingViolationError(msg)
            if r.diagnosis and any(k in str(r.diagnosis.evidence) for k in oracle_keys):
                msg = (
                    f"Oracle truth leaked into runtime Diagnosis "
                    f"{r.diagnosis.diagnosis_id} in case {r.case_id}"
                )
                raise CheatingViolationError(msg)
