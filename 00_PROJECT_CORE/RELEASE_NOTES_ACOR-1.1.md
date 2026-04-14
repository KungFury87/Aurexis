# Aurexis Core Official Release 1.1 — V1 Substrate Candidate (ACOR-1.1)

**Release name:** Aurexis Core Official Release 1.1 — V1 Substrate Candidate
**Short label:** ACOR-1.1
**Release date:** April 14, 2026
**Release tag:** `core-v1-substrate-candidate-or1.1`
**Release branch:** `backup/v1-substrate-candidate-20260414-120000`
**Release commit:** `7053e6fcc06ed515eb69daca877302bac5a5d60d`
**Supersedes:** nothing — ACOR-1 remains the first published release
**Relationship to ACOR-1:** same audited build, with an additional second-pass provenance re-verification stamp. See below.

---

## Why ACOR-1.1 Exists

After ACOR-1 was tagged, the repo went through a **second-pass code provenance / copyright / protected-code re-verification**. The scope was a clean re-scan of:

- all 66 V1 source modules + 2 fixture-support modules
- the 19 pytest test modules
- the 61 standalone runners
- the lightweight `run_pytest_surface.py` pytest-compatible runner

The re-verification looked for external (non-stdlib, non-`aurexis_lang`) imports and for copy/provenance markers such as "Stack Overflow", "stackoverflow", "adapted from", "based on code from", "originally from", "copied from", "SPDX-License", "Licensed under", and URL-style attributions to github/pypi/gist.

### Re-verification findings

- **External imports in release-zip code:** 1 (unchanged) — `PIL` (Pillow), inside a `try` block in `raster_law_bridge_v1.py` with a working stdlib fallback. Already documented in `THIRD_PARTY_LICENSE_NOTES_V1.md`.
- **Risky copy markers:** 0.
- **New third-party code introduced since ACOR-1:** 0.
- **New clean-room rewrites required:** 0.

The first-pass audit findings remain valid. The ACOR-1 audit documents are now stamped with a "Re-Verification Stamp" section and a corresponding `re_verification` block in `CODE_PROVENANCE_AUDIT_V1.json`.

## What Changed Between ACOR-1 and ACOR-1.1

Only the audit documents and the release zip:

- `00_PROJECT_CORE/CODE_PROVENANCE_AUDIT_V1.md` — added Re-Verification Stamp section
- `00_PROJECT_CORE/CODE_PROVENANCE_AUDIT_V1.json` — added `re_verification` object
- `00_PROJECT_CORE/aurexis_core_v1_substrate_candidate_locked.zip` — rebuilt to include the re-verified audit docs
- `00_PROJECT_CORE/RELEASE_NOTES_ACOR-1.1.md` — this file
- `00_PROJECT_CORE/GITHUB_BACKUP_RECORD_V1.md` — release #32 entry recording the ACOR-1.1 follow-up release

**No bridge source code changed. No tests changed. No architecture changed.**

## Why Not Rewrite the ACOR-1 Tag?

Silently rewriting a published tag is dishonest. ACOR-1 was the real first published release. ACOR-1.1 is a transparent follow-up that adds the second-pass re-verification stamp. Both tags coexist so anyone auditing the release history can see exactly what happened and when.

## Package Totals (unchanged from ACOR-1)

| Metric | Value |
|--------|-------|
| Bridge milestones | 51 across 9 branches |
| Standalone assertions | 6,358 (all passing) |
| Standalone runners | 61 |
| V1 source modules | 67 |
| Pytest test modules | 19 |
| Pytest surface | 327 passed, 0 failed (clean-room verified) |
| Packaged zip | 193 files, ~2.28 MB |
| Branch capstones verified | 9 / 9 |

## Installation / Verification

```bash
git clone https://github.com/KungFury87/Aurexis.git
cd Aurexis
git checkout core-v1-substrate-candidate-or1.1

cd 05_ACTIVE_DEV/aurexis_lang
export PYTHONPATH=src
python3 run_pytest_surface.py
# Expected: TOTAL: 327 passed, 0 failed
```

## Release Removal / Revision

To remove ACOR-1.1 without removing ACOR-1:

```bash
git push origin --delete core-v1-substrate-candidate-or1.1
git tag -d core-v1-substrate-candidate-or1.1
# (Optional: delete the GitHub Release object for ACOR-1.1 via UI or
#  `gh release delete core-v1-substrate-candidate-or1.1 --repo KungFury87/Aurexis --yes`)
```

---

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
