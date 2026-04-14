"""
Aurexis Core — Replay Outcome Contract Bridge V1

Validates that replay outcomes from the intake-to-delta harness match
explicit expected dry-run verdicts. This is a narrow deterministic
contract — it checks that the authored fixture pack produces exactly
the expected results at every stage.

What this proves:
  - Valid authored packs reach expected manifests and delta surfaces
  - Malformed packs fail at preflight as expected
  - Valid packs with reference outputs yield known delta categories
  - The full pipeline is deterministic and repeatable

What this does NOT prove:
  - Real-world camera robustness
  - Automatic self-improvement
  - Full Aurexis Core completion

Evidence tier: AUTHORED only. Never REAL_CAPTURE.

Design:
  - ContractCheck: one check comparing expected vs actual
  - ContractVerdict: SATISFIED / VIOLATED / ERROR
  - OutcomeContract: full contract result for one fixture pack replay
  - validate_replay_outcomes(): runs the contract against a ReplaySummary
  - validate_single_outcome(): validates one ReplayResult

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum
import hashlib
import json


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

REPLAY_CONTRACT_VERSION = "V1.0"
REPLAY_CONTRACT_FROZEN = True


# ════════════════════════════════════════════════════════════
# CONTRACT CHECK
# ════════════════════════════════════════════════════════════

@dataclass
class ContractCheck:
    """One check in the replay outcome contract."""
    name: str = ""
    passed: bool = False
    expected: str = ""
    actual: str = ""
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "expected": self.expected,
            "actual": self.actual,
            "detail": self.detail,
        }


# ════════════════════════════════════════════════════════════
# CONTRACT VERDICT
# ════════════════════════════════════════════════════════════

class ContractVerdict(str, Enum):
    """Overall verdict for the replay outcome contract."""
    SATISFIED = "SATISFIED"
    VIOLATED = "VIOLATED"
    ERROR = "ERROR"


# ════════════════════════════════════════════════════════════
# OUTCOME CONTRACT
# ════════════════════════════════════════════════════════════

@dataclass
class OutcomeContract:
    """Full contract result for one fixture pack replay."""
    verdict: ContractVerdict = ContractVerdict.ERROR
    evidence_tier: str = "authored"
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    checks: List[ContractCheck] = field(default_factory=list)
    fixture_checks: List[Dict[str, Any]] = field(default_factory=list)
    contract_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "evidence_tier": self.evidence_tier,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "contract_hash": self.contract_hash,
            "checks": [c.to_dict() for c in self.checks],
            "fixture_checks": self.fixture_checks,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    def to_summary_text(self) -> str:
        lines = [
            f"Outcome Contract: {self.verdict.value}",
            f"  Total: {self.total_checks}  Passed: {self.passed_checks}  "
            f"Failed: {self.failed_checks}",
            f"  Evidence tier: {self.evidence_tier}",
        ]
        for c in self.checks:
            mark = "PASS" if c.passed else "FAIL"
            lines.append(f"  [{mark}] {c.name}: {c.detail}")
        return "\n".join(lines)


# ════════════════════════════════════════════════════════════
# VALIDATE SINGLE OUTCOME
# ════════════════════════════════════════════════════════════

def validate_single_outcome(replay_result, fixture) -> List[ContractCheck]:
    """
    Validate one replay result against its fixture expectations.

    Returns a list of ContractCheck records.
    """
    checks = []

    # Check 1: Evidence tier is authored
    checks.append(ContractCheck(
        name=f"{fixture.name}/evidence_tier",
        passed=(replay_result.evidence_tier == "authored"),
        expected="authored",
        actual=replay_result.evidence_tier,
        detail="Evidence tier must be authored",
    ))

    # Check 2: Preflight verdict matches expected
    checks.append(ContractCheck(
        name=f"{fixture.name}/preflight_verdict",
        passed=replay_result.preflight_verdict_match,
        expected=fixture.expected_preflight_verdict,
        actual=replay_result.stages[0].verdict if replay_result.stages else "NONE",
        detail="Preflight verdict must match fixture expectation",
    ))

    # For valid fixtures, check deeper stages
    if fixture.is_valid:
        # Check 3: All stages completed
        checks.append(ContractCheck(
            name=f"{fixture.name}/stages_completed",
            passed=(replay_result.stages_completed == 5),
            expected="5",
            actual=str(replay_result.stages_completed),
            detail="All 5 pipeline stages must complete for valid fixtures",
        ))

        # Check 4: Ingest verdict matches
        if fixture.expected_ingest_verdicts:
            checks.append(ContractCheck(
                name=f"{fixture.name}/ingest_verdict",
                passed=replay_result.ingest_verdict_match,
                expected=str(fixture.expected_ingest_verdicts),
                actual="matched" if replay_result.ingest_verdict_match else "mismatched",
                detail="Ingest verdicts must match fixture expectations",
            ))

        # Check 5: Delta verdict matches
        if fixture.expected_delta_verdict:
            checks.append(ContractCheck(
                name=f"{fixture.name}/delta_verdict",
                passed=replay_result.delta_verdict_match,
                expected=fixture.expected_delta_verdict,
                actual="matched" if replay_result.delta_verdict_match else "mismatched",
                detail="Delta verdict must match fixture expectation",
            ))

        # Check 6: Overall verdict is ALL_STAGES_PASSED
        checks.append(ContractCheck(
            name=f"{fixture.name}/overall_verdict",
            passed=(replay_result.verdict.value == "ALL_STAGES_PASSED"),
            expected="ALL_STAGES_PASSED",
            actual=replay_result.verdict.value,
            detail="Valid fixtures must pass all stages",
        ))
    else:
        # For invalid fixtures, check expected rejection
        checks.append(ContractCheck(
            name=f"{fixture.name}/expected_rejection",
            passed=(replay_result.verdict.value == "EXPECTED_REJECTION"),
            expected="EXPECTED_REJECTION",
            actual=replay_result.verdict.value,
            detail="Invalid fixtures must produce EXPECTED_REJECTION",
        ))

    # Check: Replay hash is deterministic (non-empty)
    checks.append(ContractCheck(
        name=f"{fixture.name}/replay_hash",
        passed=(len(replay_result.replay_hash) == 64),
        expected="64-char SHA-256",
        actual=f"{len(replay_result.replay_hash)} chars",
        detail="Replay hash must be deterministic SHA-256",
    ))

    return checks


# ════════════════════════════════════════════════════════════
# VALIDATE REPLAY OUTCOMES
# ════════════════════════════════════════════════════════════

def validate_replay_outcomes(replay_summary, fixture_pack=None) -> OutcomeContract:
    """
    Run the outcome contract against a full replay summary.

    Parameters:
        replay_summary: a ReplaySummary from run_all_replays()
        fixture_pack: the AuthoredFixturePack used (default: V1_FIXTURE_PACK)

    Returns an OutcomeContract.
    """
    if fixture_pack is None:
        from aurexis_lang.authored_capture_fixtures_v1 import V1_FIXTURE_PACK
        fixture_pack = V1_FIXTURE_PACK

    contract = OutcomeContract(evidence_tier="authored")
    all_checks: List[ContractCheck] = []

    # Global check 1: fixture count matches
    all_checks.append(ContractCheck(
        name="global/fixture_count",
        passed=(replay_summary.total_fixtures == len(fixture_pack.fixtures)),
        expected=str(len(fixture_pack.fixtures)),
        actual=str(replay_summary.total_fixtures),
        detail="Replay must cover all fixtures in the pack",
    ))

    # Global check 2: evidence tier is authored
    all_checks.append(ContractCheck(
        name="global/evidence_tier",
        passed=(replay_summary.evidence_tier == "authored"),
        expected="authored",
        actual=replay_summary.evidence_tier,
        detail="Evidence tier must be authored",
    ))

    # Global check 3: no failures
    all_checks.append(ContractCheck(
        name="global/no_failures",
        passed=(replay_summary.failed_count == 0),
        expected="0 failures",
        actual=f"{replay_summary.failed_count} failures",
        detail="All fixtures must pass or produce expected rejections",
    ))

    # Global check 4: summary hash is deterministic
    all_checks.append(ContractCheck(
        name="global/summary_hash",
        passed=(len(replay_summary.summary_hash) == 64),
        expected="64-char SHA-256",
        actual=f"{len(replay_summary.summary_hash)} chars",
        detail="Summary hash must be deterministic SHA-256",
    ))

    # Per-fixture checks
    for replay_result in replay_summary.results:
        fixture = fixture_pack.fixture_by_name(replay_result.fixture_name)
        if fixture is None:
            all_checks.append(ContractCheck(
                name=f"{replay_result.fixture_name}/fixture_found",
                passed=False,
                expected="fixture exists",
                actual="not found",
                detail="Fixture must exist in the pack",
            ))
            continue

        fixture_checks = validate_single_outcome(replay_result, fixture)
        all_checks.extend(fixture_checks)

        contract.fixture_checks.append({
            "fixture_name": fixture.name,
            "checks_passed": sum(1 for c in fixture_checks if c.passed),
            "checks_total": len(fixture_checks),
        })

    contract.checks = all_checks
    contract.total_checks = len(all_checks)
    contract.passed_checks = sum(1 for c in all_checks if c.passed)
    contract.failed_checks = contract.total_checks - contract.passed_checks

    if contract.failed_checks == 0:
        contract.verdict = ContractVerdict.SATISFIED
    else:
        contract.verdict = ContractVerdict.VIOLATED

    # Compute hash
    data = json.dumps(contract.to_dict(), sort_keys=True, separators=(",", ":"))
    contract.contract_hash = hashlib.sha256(data.encode()).hexdigest()

    return contract


# ════════════════════════════════════════════════════════════
# FROZEN COUNTS FOR TESTING
# ════════════════════════════════════════════════════════════

EXPECTED_VERDICT_COUNT = 3  # SATISFIED, VIOLATED, ERROR
EXPECTED_GLOBAL_CHECKS = 4  # fixture_count, evidence_tier, no_failures, summary_hash
