# Clean-Room Remediation Log — Aurexis Core V1 Substrate Candidate (ACOR-1)

**Owner:** Vincent Anderson
**Date:** April 14, 2026
**Scope:** Decisions made during the Phase-1 provenance/copyright/protected-code audit for the ACOR-1 release zip.
**Companion docs:** `CODE_PROVENANCE_AUDIT_V1.md`, `THIRD_PARTY_LICENSE_NOTES_V1.md`

---

## Decision 1 — V1 Source Modules (`src/aurexis_lang/`)

**Classification:** LOW RISK / CLEARLY ORIGINAL
**Decision:** Retain as-is.
**Reason:** All 67 shipped source modules are authored by Vincent Anderson. No external imports except optional Pillow (see Decision 2). No copy markers, no vendored blobs, no style-inconsistent files.
**Clean-room rewrite performed:** None required.

## Decision 2 — Optional Pillow Call in `raster_law_bridge_v1.py`

**Classification:** THIRD-PARTY BUT APPARENTLY ACCEPTABLE
**Decision:** Retain as-is.
**Reason:** The Pillow import is inside a `try`/`except ImportError` block, with a fully working stdlib fallback already present. No Pillow source code is shipped. Pillow is HPND-licensed and used only through its public API. Removing the optional path would reduce real-world compatibility without provenance benefit.
**Clean-room rewrite performed:** None required.
**Note added:** `THIRD_PARTY_LICENSE_NOTES_V1.md` documents the optional dependency honestly.

## Decision 3 — Test Modules (`tests/`, `run_pytest_surface.py`)

**Classification:** LOW RISK / CLEARLY ORIGINAL
**Decision:** Retain as-is.
**Reason:** All test modules are authored project tests. The pytest-compatible runner uses only stdlib.
**Clean-room rewrite performed:** None required.

## Decision 4 — Standalone Runners (`run_v1_*.py`, 61 files)

**Classification:** LOW RISK / CLEARLY ORIGINAL
**Decision:** Retain as-is.
**Reason:** Authored project test runners. Consistent project style.
**Clean-room rewrite performed:** None required.

## Decision 5 — Documentation / Manifests / JSON Truth Surface

**Classification:** LOW RISK / CLEARLY ORIGINAL
**Decision:** Retain as-is.
**Reason:** Authored project documentation.
**Clean-room rewrite performed:** None required.

---

## Repo-Tree Hygiene Decisions (Items NOT in the Release Zip)

### Decision 6 — ChatGPT Conversation JSON Exports

**Files:**
- `ChatGPT-Aurexis ONLY.json`
- `ChatGPT-JSON Continuation and Analysis.json`
- `ChatGPT-Project Continuation Setup.json`
- Copies under `03_HANDOFFS_AND_CONTEXT/`

**Classification:** PROVENANCE UNCLEAR / NOT FOR PUBLIC RELEASE
**Decision:** Add to `.gitignore`. Do not strip from local history automatically; leave that decision to the owner. Flag as "not part of the V1 release surface."
**Reason:** Personal ChatGPT conversation exports contain the owner's own conversations, but they are third-party-product exports with mixed provenance and personal content. They do not belong in a public release surface. Already confirmed NOT in the release zip.
**Clean-room rewrite performed:** None. Files are left untouched in the local working copy but flagged from automated packaging.

### Decision 7 — `ziqHxpn5` (Legacy Local Snapshot Zip)

**Classification:** GENERATED / TOOL OUTPUT (project's own older snapshot)
**Decision:** Add to `.gitignore`. Flag as a local scratch file.
**Reason:** Content is the project's own older test and doc files. Not third-party. Misnamed. Safe to leave in local tree but not part of the public release.
**Clean-room rewrite performed:** None required.

### Decision 8 — `.buildozer/` Directory

**Classification:** GENERATED / TOOL OUTPUT (Buildozer toolchain cache)
**Decision:** Add to `.gitignore`. Not to be shipped.
**Reason:** Automated Buildozer scratch directory generated on Vincent's Android build machine. Contains recipe-template stubs that belong to the Buildozer / python-for-android project. Not redistributed by ACOR-1 (confirmed not in zip). Gitignore prevents accidental future inclusion.
**Clean-room rewrite performed:** None required.

### Decision 9 — `BACKUPS/`, `01_RELEASES/`, `Aurexis_Core_M11_Clean.zip`, etc.

**Classification:** LOW RISK / CLEARLY ORIGINAL (project's own older release zips)
**Decision:** Retain in repo for historical continuity. Confirmed NOT in ACOR-1 release zip.
**Reason:** These are project-authored earlier release snapshots. Not third-party.
**Clean-room rewrite performed:** None required.

---

## Summary

| Action | Count |
|--------|-------|
| V1 release-zip files retained as-is | 188 |
| V1 release-zip files clean-room-rewritten in this pass | 0 |
| Repo-tree files added to `.gitignore` for public-repo hygiene | ChatGPT JSON exports, `ziqHxpn5`, `.buildozer/` |
| Third-party source code vendored into the release zip | 0 |

## Honest Statement

This log records engineering decisions about code provenance for the ACOR-1 release zip. It is not a formal legal opinion. The project owner is responsible for final legal determinations before public redistribution.

---

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
