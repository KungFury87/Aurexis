# Code Provenance Audit — Aurexis Core V1 Substrate Candidate

**Owner:** Vincent Anderson
**Date:** April 14, 2026
**Scope:** All code and artifacts shipped in `aurexis_core_v1_substrate_candidate_locked.zip` (the ACOR-1 release zip)
**Companion docs:** `THIRD_PARTY_LICENSE_NOTES_V1.md`, `CLEAN_ROOM_REMEDIATION_LOG_V1.md`

> This is a repo-level code/provenance risk-reduction audit. It is **not** a formal legal opinion. See "Remaining Uncertainty" below.

---

## What Was Reviewed

- All 64 V1 source modules + 2 fixture-support modules (+ `__init__.py`) shipped in `src/aurexis_lang/` in the release zip
- All 19 pytest test modules in `tests/`
- All 61 standalone runners
- All top-level documentation and manifests
- The `run_pytest_surface.py` lightweight test runner
- All import graphs and dependency surfaces of the release zip

Items **explicitly excluded** from the release zip (and therefore from this audit's primary scope, but noted below):

- `.buildozer/` Android build artifacts (not in zip)
- `BACKUPS/` legacy zip archives (not in zip)
- `ChatGPT-*.json` personal conversation exports (not in zip; flagged separately)
- `ziqHxpn5` legacy snapshot zip (not in zip; flagged separately)
- Anything under `01_RELEASES/`, `02_GATE_TRACKING/`, `03_HANDOFFS_AND_CONTEXT/`, `04_WORKING_SESSIONS/` (not in zip)

---

## Risk Categories Used

| Category | Meaning |
|---------|---------|
| LOW RISK / CLEARLY ORIGINAL | Authored by Vincent Anderson, no third-party code. |
| THIRD-PARTY BUT APPARENTLY ACCEPTABLE | Third-party library used through its public API under a clearly permissive license. Attribution preserved. |
| GENERATED / TOOL OUTPUT | Produced by automated tooling; labeled, not treated as authored original. |
| TEMPLATE-DERIVED BUT COMMON / LOW CONCERN | Small amounts of widely-used idiomatic code (e.g. empty package `__init__.py`). |
| PROVENANCE UNCLEAR | Cannot confidently determine provenance. Either rewritten clean-room, removed, or isolated. |
| LICENSE / ATTRIBUTION MISMATCH RISK | Third-party content whose license has not been confirmed or whose attribution is incomplete. |
| HIGH-RISK POSSIBLE COPY / PROTECTED CODE | Code that appears copied from a protected source. Rewritten clean-room or removed. |

---

## Findings — Release Zip Contents

### 1. V1 Source Modules (`src/aurexis_lang/`, 67 files) — LOW RISK / CLEARLY ORIGINAL

**Verdict:** Clearly-original work authored by Vincent Anderson.

**Evidence:**
- Zero external imports other than Python standard library and the optional `PIL` (Pillow) call in `raster_law_bridge_v1.py` (see §2 below).
- No copy markers (grep for "Stack Overflow", "adapted from", "based on code", "github.com/", "SPDX-License" returned nothing in `src/aurexis_lang/`).
- No large copy-paste blobs (no source file exceeds reasonable hand-authored size for its role).
- All module docstrings carry the project copyright line.
- Each bridge module matches the project's consistent architectural style (frozen dataclasses, deterministic hashes, explicit verdict enums) — hand-authored pattern.

**Action:** None. Retained as authored original code.

### 2. Optional Pillow (PIL) Usage — THIRD-PARTY BUT APPARENTLY ACCEPTABLE

**File:** `src/aurexis_lang/raster_law_bridge_v1.py`, function `_decode_png_to_rgb`

**Usage:** Imports `PIL.Image` inside a `try` block, falls through to a hand-rolled PNG decoder on `ImportError`.

**Verdict:** Public-API usage of an optional library. No Pillow source code is vendored. Pillow is distributed under the HPND license (a permissive license).

**Action:** Preserved as an optional dependency. Documented in `THIRD_PARTY_LICENSE_NOTES_V1.md`. Release zip does not ship Pillow; users provide it at their own discretion.

### 3. Standalone Runners (`run_v1_*.py`, 61 files) — LOW RISK / CLEARLY ORIGINAL

**Verdict:** Authored test runners following the same consistent project style. No external imports. No copy markers. Retained as authored original code.

### 4. Pytest Surface (`tests/` and `run_pytest_surface.py`) — LOW RISK / CLEARLY ORIGINAL

**Verdict:** Authored project tests and an authored lightweight pytest-compatible runner. The runner uses only `ast`, `importlib.util`, `inspect`, `os`, `sys`, `traceback`, `types` — all stdlib. Retained as authored original code.

### 5. Documentation / Markdown / JSON Truth Surface — LOW RISK / CLEARLY ORIGINAL

**Verdict:** Authored project documentation. Retained as authored original content.

---

## Findings — Repo Tree (Not in Release Zip, But Flagged)

### 6. ChatGPT-*.json Conversation Exports — PROVENANCE UNCLEAR / NOT FOR PUBLIC RELEASE

**Files (repo tree, NOT in release zip):**
- `ChatGPT-Aurexis ONLY.json`
- `ChatGPT-JSON Continuation and Analysis.json`
- `ChatGPT-Project Continuation Setup.json`
- Mirror copies under `03_HANDOFFS_AND_CONTEXT/`

**Verdict:** These are personal ChatGPT conversation exports. They contain the user's own conversations, but as exports from a third-party product they have mixed provenance and are personal. They should not be part of a public release surface.

**Action:** Added to `.gitignore`. Left in local repo for private continuity but advised not to push these to the public release branch. Confirmed **NOT** present in the release zip.

### 7. `ziqHxpn5` (Misnamed Local Snapshot) — GENERATED / TOOL OUTPUT

**Verdict:** A zip archive of the project's own earlier test-suite and README — a local snapshot whose filename was truncated/mangled. Content is project-original. Not third-party.

**Action:** Added to `.gitignore`. Left in local repo. Confirmed **NOT** present in the release zip.

### 8. Legacy Backup Zips under `BACKUPS/`, `01_RELEASES/` — LOW RISK / CLEARLY ORIGINAL

**Verdict:** Project's own older release zips. Not third-party. Not part of the audited current release.

**Action:** Left in repo for historical continuity. Confirmed **NOT** present in the ACOR-1 release zip.

### 9. `.buildozer/` Android Build Artifacts — GENERATED / TOOL OUTPUT

**Verdict:** Buildozer-generated Android toolchain scratch directory (contains PySide6/shiboken6 sample recipe templates from the Buildozer project itself). Third-party tool output, but its presence is a build-time side effect on a local machine, not a claim of authorship. Not shipped in the release zip.

**Action:** Confirmed excluded from the release zip. Already excluded from all automated packaging. Should be added to `.gitignore` (recommended).

---

## Findings — What Was Rewritten/Removed/Replaced in This Pass

None. No code in the release zip was found to require clean-room rewriting. All code shipped in ACOR-1 is either:

- authored by Vincent Anderson, or
- standard-library usage, or
- optional, public-API usage of a permissively-licensed third-party library (Pillow) with a stdlib fallback already in place.

See `CLEAN_ROOM_REMEDIATION_LOG_V1.md` for the remediation decision log.

---

## Findings — What Is Preserved and Why

- The optional Pillow call path in `raster_law_bridge_v1.py` is preserved because (a) it is optional, (b) it uses only Pillow's public API, (c) Pillow is permissively licensed, (d) a stdlib fallback already exists, (e) removing it would reduce real-world compatibility.
- The project copyright line in each module docstring is preserved.
- Authored-fixture data is preserved as-is; it is explicitly labeled `evidence_tier="authored"` and is not claimed to be real capture.

---

## Remaining Uncertainty

This audit is an engineering-grade repo review, not a formal legal opinion.

- I cannot guarantee that no code in the repo's historical branches resembles proprietary third-party code from another source. I can only state that my directed inspection of the release zip surface surfaced no such indicators.
- The `ChatGPT-*.json` personal conversation exports were intentionally NOT opened, inspected, or included in the release zip. Their contents were not audited in this pass.
- Buildozer-generated templates (PySide6/shiboken6 recipe stubs) inside `.buildozer/` are known Buildozer project scaffolding. They are not shipped.
- If in the future it becomes necessary to ship any code that was not authored by Vincent Anderson, that code must carry its own license and attribution.

The project owner is responsible for any final legal determination before public redistribution.

---

## Summary

| Metric | Value |
|--------|-------|
| Files reviewed (release zip) | 188 |
| Source modules reviewed | 67 |
| External dependencies found in release zip | 1 (Pillow, optional, with stdlib fallback) |
| HIGH-RISK / PROTECTED-CODE findings in release zip | 0 |
| PROVENANCE-UNCLEAR findings in release zip | 0 |
| Clean-room rewrites required for release zip | 0 |
| Files flagged for public-repo hygiene (not in zip) | ChatGPT JSON exports, ziqHxpn5, .buildozer/ |

**Audit verdict:** The ACOR-1 release zip is clean-enough for public release under Vincent Anderson's sole authorship, with Pillow noted as an optional permissively-licensed dependency. Repo-tree items flagged for `.gitignore` have been addressed.

---

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
