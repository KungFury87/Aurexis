"""
Aurexis Core — Authored Capture Session Fixture Pack V1

Frozen family of clearly labeled AUTHORED mock session packs for
exercising the intake/preflight/manifest/delta/recommendation pipeline
end-to-end WITHOUT requiring real user-supplied capture files.

CRITICAL LABELING:
  These are AUTHORED fixtures at evidence_tier="authored".
  They must NEVER be labeled as REAL_CAPTURE.
  They exist ONLY to prove the pipeline runs correctly.
  They do NOT prove real-world camera robustness.

Fixture cases:
  1. VALID_PHONE_JPEG   — valid phone JPEG session, should CLEAR preflight
  2. VALID_SCANNER_TIFF  — valid scanner TIFF session, should CLEAR preflight
  3. VALID_TWO_FILE      — valid session with two files, should CLEAR preflight
  4. INVALID_MISSING_FIELDS — missing required session fields, should REJECT
  5. INVALID_BAD_EXTENSION  — unsupported file extension, should REJECT
  6. INVALID_DUPLICATE_FILES — duplicate filenames, should REJECT

Each fixture provides:
  - session_manifest: dict matching the intake preflight schema
  - expected_preflight_verdict: the PreflightVerdict this should produce
  - expected_ingest_verdict: the IngestVerdict for each file (if preflight passes)
  - expected_delta_verdict: the DeltaVerdict when compared against reference output
  - evidence_tier: always "authored" — never "real-capture"

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple, Optional
import hashlib
import json


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

FIXTURES_VERSION = "V1.0"
FIXTURES_FROZEN = True
EVIDENCE_TIER = "authored"  # NEVER "real-capture"


# ════════════════════════════════════════════════════════════
# FIXTURE RECORD
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class AuthoredFixture:
    """
    One authored capture session fixture for dry-run replay.

    name: unique fixture identifier
    description: what this fixture tests
    evidence_tier: always "authored"
    session_manifest: dict matching preflight schema
    expected_preflight_verdict: expected PreflightVerdict string
    expected_ingest_verdicts: per-file expected IngestVerdict strings
    expected_delta_verdict: expected DeltaVerdict string when compared
    is_valid: whether this fixture represents a valid session
    """
    name: str
    description: str
    evidence_tier: str = "authored"
    session_manifest: Dict[str, Any] = field(default_factory=dict)
    expected_preflight_verdict: str = ""
    expected_ingest_verdicts: Tuple[str, ...] = ()
    expected_delta_verdict: str = ""
    is_valid: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "evidence_tier": self.evidence_tier,
            "expected_preflight_verdict": self.expected_preflight_verdict,
            "expected_ingest_verdicts": list(self.expected_ingest_verdicts),
            "expected_delta_verdict": self.expected_delta_verdict,
            "is_valid": self.is_valid,
            "session_manifest": self.session_manifest,
        }

    def fixture_hash(self) -> str:
        data = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(data.encode()).hexdigest()


# ════════════════════════════════════════════════════════════
# FIXTURE PACK
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class AuthoredFixturePack:
    """
    Frozen family of authored fixtures for dry-run replay.

    version: pack version
    frozen: always True
    evidence_tier: always "authored"
    fixtures: tuple of AuthoredFixture records
    """
    version: str = FIXTURES_VERSION
    frozen: bool = True
    evidence_tier: str = "authored"
    fixtures: Tuple[AuthoredFixture, ...] = ()

    def valid_fixtures(self) -> List[AuthoredFixture]:
        return [f for f in self.fixtures if f.is_valid]

    def invalid_fixtures(self) -> List[AuthoredFixture]:
        return [f for f in self.fixtures if not f.is_valid]

    def fixture_by_name(self, name: str) -> Optional[AuthoredFixture]:
        for f in self.fixtures:
            if f.name == name:
                return f
        return None

    def pack_hash(self) -> str:
        data = json.dumps(
            {"version": self.version, "fixtures": [f.to_dict() for f in self.fixtures]},
            sort_keys=True, separators=(",", ":"),
        )
        return hashlib.sha256(data.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "frozen": self.frozen,
            "evidence_tier": self.evidence_tier,
            "fixture_count": len(self.fixtures),
            "valid_count": len(self.valid_fixtures()),
            "invalid_count": len(self.invalid_fixtures()),
            "pack_hash": self.pack_hash(),
            "fixtures": [f.to_dict() for f in self.fixtures],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


# ════════════════════════════════════════════════════════════
# REFERENCE SUBSTRATE OUTPUTS FOR VALID FIXTURES
# (used by delta analysis to produce deterministic deltas)
# ════════════════════════════════════════════════════════════

# Reference expected output for a single phone JPEG capture
REFERENCE_PHONE_JPEG_PRIMITIVES = (
    {"name": "POINT_A", "kind": "POINT", "confidence": 0.85, "x": 100.0, "y": 200.0},
    {"name": "LINE_1", "kind": "LINE", "confidence": 0.78, "x": 150.0, "y": 250.0},
    {"name": "REGION_1", "kind": "REGION", "confidence": 0.92, "x": 300.0, "y": 400.0},
)

REFERENCE_PHONE_JPEG_CONTRACTS = (
    {"contract_name": "artifact_set_contract", "passed": True, "detail": "authored reference"},
)

REFERENCE_PHONE_JPEG_SIGNATURES = (
    {"signature_name": "set_signature_v1", "matched": True, "similarity": 1.0},
)

# Reference for scanner TIFF
REFERENCE_SCANNER_TIFF_PRIMITIVES = (
    {"name": "POINT_A", "kind": "POINT", "confidence": 0.95, "x": 100.0, "y": 200.0},
    {"name": "POINT_B", "kind": "POINT", "confidence": 0.91, "x": 500.0, "y": 600.0},
    {"name": "LINE_1", "kind": "LINE", "confidence": 0.88, "x": 150.0, "y": 250.0},
    {"name": "REGION_1", "kind": "REGION", "confidence": 0.96, "x": 300.0, "y": 400.0},
)

REFERENCE_SCANNER_TIFF_CONTRACTS = (
    {"contract_name": "artifact_set_contract", "passed": True, "detail": "authored reference"},
    {"contract_name": "page_sequence_contract", "passed": True, "detail": "authored reference"},
)

REFERENCE_SCANNER_TIFF_SIGNATURES = (
    {"signature_name": "set_signature_v1", "matched": True, "similarity": 1.0},
    {"signature_name": "sequence_signature_v1", "matched": True, "similarity": 1.0},
)


# ════════════════════════════════════════════════════════════
# FROZEN FIXTURE DEFINITIONS
# ════════════════════════════════════════════════════════════

FIXTURE_VALID_PHONE_JPEG = AuthoredFixture(
    name="valid_phone_jpeg",
    description="Valid phone JPEG capture session — single file, all fields present, should CLEAR preflight",
    evidence_tier="authored",
    session_manifest={
        "session_id": "authored-fixture-phone-jpeg-001",
        "description": "Authored fixture: phone JPEG capture of printed artifact",
        "created_at": "2026-04-13T10:00:00Z",
        "files": [
            {
                "file_ref": "artifact_photo_001.jpg",
                "file_ext": ".jpg",
                "file_size_bytes": 2_500_000,
                "width_px": 4032,
                "height_px": 3024,
                "capture_device": "Samsung S23 Ultra",
                "capture_timestamp": "2026-04-13T10:30:00Z",
            }
        ],
        "conditions": {
            "adequate_lighting": True,
            "subject_in_frame": True,
        },
    },
    expected_preflight_verdict="CLEARED",
    expected_ingest_verdicts=("ACCEPTED",),
    expected_delta_verdict="IDENTICAL",
    is_valid=True,
)

FIXTURE_VALID_SCANNER_TIFF = AuthoredFixture(
    name="valid_scanner_tiff",
    description="Valid scanner TIFF capture session — single file, all fields present, should CLEAR preflight",
    evidence_tier="authored",
    session_manifest={
        "session_id": "authored-fixture-scanner-tiff-001",
        "description": "Authored fixture: flatbed scanner output of printed artifact",
        "created_at": "2026-04-13T11:00:00Z",
        "files": [
            {
                "file_ref": "scanned_artifact_001.tif",
                "file_ext": ".tif",
                "file_size_bytes": 15_000_000,
                "width_px": 2400,
                "height_px": 3600,
                "capture_device": "Epson V600",
                "capture_timestamp": "2026-04-13T11:00:00Z",
            }
        ],
        "conditions": {
            "adequate_lighting": True,
            "subject_in_frame": True,
        },
    },
    expected_preflight_verdict="CLEARED",
    expected_ingest_verdicts=("ACCEPTED",),
    expected_delta_verdict="IDENTICAL",
    is_valid=True,
)

FIXTURE_VALID_TWO_FILE = AuthoredFixture(
    name="valid_two_file",
    description="Valid session with two files (phone JPEG + PNG) — should CLEAR preflight",
    evidence_tier="authored",
    session_manifest={
        "session_id": "authored-fixture-two-file-001",
        "description": "Authored fixture: two-file phone capture session",
        "created_at": "2026-04-13T12:00:00Z",
        "files": [
            {
                "file_ref": "page1_photo.jpg",
                "file_ext": ".jpg",
                "file_size_bytes": 3_000_000,
                "width_px": 4032,
                "height_px": 3024,
                "capture_device": "Samsung S23 Ultra",
                "capture_timestamp": "2026-04-13T12:00:00Z",
            },
            {
                "file_ref": "page2_photo.png",
                "file_ext": ".png",
                "file_size_bytes": 8_000_000,
                "width_px": 4032,
                "height_px": 3024,
                "capture_device": "Samsung S23 Ultra",
                "capture_timestamp": "2026-04-13T12:01:00Z",
            },
        ],
        "conditions": {
            "adequate_lighting": True,
            "subject_in_frame": True,
        },
    },
    expected_preflight_verdict="CLEARED",
    expected_ingest_verdicts=("ACCEPTED", "ACCEPTED"),
    expected_delta_verdict="WITHIN_TOLERANCE",
    is_valid=True,
)

FIXTURE_INVALID_MISSING_FIELDS = AuthoredFixture(
    name="invalid_missing_fields",
    description="Invalid session — missing required session fields (session_id, created_at), should REJECT at preflight",
    evidence_tier="authored",
    session_manifest={
        "description": "Authored fixture: intentionally missing session_id and created_at",
        "files": [
            {
                "file_ref": "artifact_photo.jpg",
                "file_ext": ".jpg",
                "file_size_bytes": 2_000_000,
                "width_px": 1920,
                "height_px": 1080,
                "capture_device": "Generic Camera",
                "capture_timestamp": "2026-04-13T13:00:00Z",
            }
        ],
    },
    expected_preflight_verdict="REJECTED",
    expected_ingest_verdicts=(),
    expected_delta_verdict="",
    is_valid=False,
)

FIXTURE_INVALID_BAD_EXTENSION = AuthoredFixture(
    name="invalid_bad_extension",
    description="Invalid session — unsupported .bmp extension, should REJECT at preflight",
    evidence_tier="authored",
    session_manifest={
        "session_id": "authored-fixture-bad-ext-001",
        "description": "Authored fixture: unsupported file extension",
        "created_at": "2026-04-13T14:00:00Z",
        "files": [
            {
                "file_ref": "artifact_photo.bmp",
                "file_ext": ".bmp",
                "file_size_bytes": 5_000_000,
                "width_px": 1920,
                "height_px": 1080,
                "capture_device": "Generic Camera",
                "capture_timestamp": "2026-04-13T14:00:00Z",
            }
        ],
        "conditions": {
            "adequate_lighting": True,
            "subject_in_frame": True,
        },
    },
    expected_preflight_verdict="REJECTED",
    expected_ingest_verdicts=(),
    expected_delta_verdict="",
    is_valid=False,
)

FIXTURE_INVALID_DUPLICATE_FILES = AuthoredFixture(
    name="invalid_duplicate_files",
    description="Invalid session — duplicate file_ref values, should REJECT at preflight",
    evidence_tier="authored",
    session_manifest={
        "session_id": "authored-fixture-dup-files-001",
        "description": "Authored fixture: duplicate file refs",
        "created_at": "2026-04-13T15:00:00Z",
        "files": [
            {
                "file_ref": "same_name.jpg",
                "file_ext": ".jpg",
                "file_size_bytes": 2_000_000,
                "width_px": 1920,
                "height_px": 1080,
                "capture_device": "Samsung S23",
                "capture_timestamp": "2026-04-13T15:00:00Z",
            },
            {
                "file_ref": "same_name.jpg",
                "file_ext": ".jpg",
                "file_size_bytes": 2_100_000,
                "width_px": 1920,
                "height_px": 1080,
                "capture_device": "Samsung S23",
                "capture_timestamp": "2026-04-13T15:01:00Z",
            },
        ],
        "conditions": {
            "adequate_lighting": True,
            "subject_in_frame": True,
        },
    },
    expected_preflight_verdict="REJECTED",
    expected_ingest_verdicts=(),
    expected_delta_verdict="",
    is_valid=False,
)


# ════════════════════════════════════════════════════════════
# FROZEN V1 FIXTURE PACK
# ════════════════════════════════════════════════════════════

FROZEN_FIXTURES = (
    FIXTURE_VALID_PHONE_JPEG,
    FIXTURE_VALID_SCANNER_TIFF,
    FIXTURE_VALID_TWO_FILE,
    FIXTURE_INVALID_MISSING_FIELDS,
    FIXTURE_INVALID_BAD_EXTENSION,
    FIXTURE_INVALID_DUPLICATE_FILES,
)

V1_FIXTURE_PACK = AuthoredFixturePack(
    version=FIXTURES_VERSION,
    frozen=True,
    evidence_tier="authored",
    fixtures=FROZEN_FIXTURES,
)


# ════════════════════════════════════════════════════════════
# FROZEN COUNTS FOR TESTING
# ════════════════════════════════════════════════════════════

EXPECTED_FIXTURE_COUNT = 6
EXPECTED_VALID_COUNT = 3
EXPECTED_INVALID_COUNT = 3
EXPECTED_EVIDENCE_TIER = "authored"
EXPECTED_REFERENCE_PRIMITIVES_PHONE = 3
EXPECTED_REFERENCE_PRIMITIVES_SCANNER = 4
