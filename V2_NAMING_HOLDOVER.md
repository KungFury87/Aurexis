# Aurexis Core V2 — Naming Holdover Note

**Date:** 2026-04-14
**Scope:** explains why the Python package path and a handful of identifier strings still contain the token `lang` / `language` even though Aurexis Core has been re-branded from "programming language" to **Engine**.

## Short version

**Aurexis Core is an Engine, not a programming language.** All public-facing identity documentation (README, `WHAT_AUREXIS_IS.md`, `PROJECT_STATUS.md`, handoff docs, etc.) has been updated to reflect this.

However, certain on-disk identifiers that date from the older terminology **have been preserved deliberately**. Renaming them would:

1. Break imports in the frozen V1 substrate (V2_EXCLUSIONS.md §9 — "V1 substrate must not be rewritten").
2. Invalidate `00_PROJECT_CORE/aurexis_core_v1_substrate_candidate_locked.zip` (the ACOR-1.1 release asset).
3. Corrupt the V1 clean-room provenance audit (`CODE_PROVENANCE_AUDIT_V1.md`) which is hash-locked against current paths.
4. Require retagging the V1 release tags `core-v1-substrate-candidate-or1` and `or1.1`, which is forbidden by the V1/V2 isolation rule in `V2_CHARTER.md`.

The cost of renaming is substantially greater than the cost of documenting the holdover.

## What stays as-is

| Identifier | Type | Reason |
|---|---|---|
| `05_ACTIVE_DEV/aurexis_lang/` | directory name | Python package root for V1 substrate + V2 extensions; `import aurexis_lang` is V1's public API |
| `05_ACTIVE_DEV/aurexis_lang/src/aurexis_lang/` | directory name | same |
| `05_ACTIVE_DEV/mobile_app/aurexis_lang/` | directory name | V1 mobile-copy mirror; frozen |
| `import aurexis_lang` in V1 and V2 Python source | import statement | follows the package directory name |
| `language_legal` field in V1 Core law contract | runtime API field | live V1 runtime field; see `CORE_LAW_REFERENCE.md` and V1 source |
| Historical V1 gate verification docs (`00_PROJECT_CORE/*_V1_GATE_VERIFICATION.md`) | audit records | frozen audit surface |
| `M0_BASELINE_REALITY_MAP.md` | historical baseline | records the state at M0 — rewriting it would falsify the baseline |
| V1 release tags `core-v1-substrate-candidate-or1`, `or1.1` | git refs | isolation rule absolute |

## What has been updated

All public-facing identity language has been rewritten to **Engine**:

- `README.md` (repo landing page)
- `00_PROJECT_CORE/WHAT_AUREXIS_IS.md`
- `00_PROJECT_CORE/PROJECT_STATUS.md`
- `00_PROJECT_CORE/ROADMAP.md`
- `AUREXIS_CORE_OLLAMA_QWEN30B_HANDOFF_V80.md` (root + `03_HANDOFFS_AND_CONTEXT/` copy)

All new V2 documentation refers to Aurexis Core as an Engine. Any future public material — release notes, marketing copy, external docs — uses "Engine" and does not reintroduce "programming language" framing.

## GitHub repo metadata (outside this repo's control)

The GitHub repo **description** and **topics** at `github.com/KungFury87/Aurexis` are stored on GitHub, not in the repo tree. If either currently says "programming language" or similar, they must be updated via the GitHub web UI:

1. `github.com/KungFury87/Aurexis` → gear icon next to "About" → edit description and topics
2. Replace any "programming language" / "language" framing with "Engine"
3. Save

This repo cannot update those fields; only the account owner (Vincent) can.

## Future V2-internal naming

All V2-only code introduced after 2026-04-14 uses Engine-consistent names where a new name is needed. V2 does **not** introduce new identifiers containing `lang` or `language` to describe Aurexis Core itself. The existing `aurexis_lang` Python package is the exception, grandfathered for the reasons above.
