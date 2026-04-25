# Aurexis Core — unified roadmap (`core v1 incomplete`)

This is the unified, current roadmap for Aurexis **Core**.

The frame is:

- **ACOR-1.1** is the **frozen official release surface** for the V1
  Substrate Candidate. Its truth surface lives in `00_PROJECT_CORE/`
  and is preserved by the tag `core-v1-substrate-candidate-or1.1`.
- **V2 research / proof-system work** continues alongside it. V2
  evidence and dev artifacts are preserved in `V2_*.md`,
  `V2_BENCHMARK_SET/`, `05_ACTIVE_DEV/aurexis_lang/.../v2_decode/`,
  and the `working/core-v2` branch.
- **The current proof-system body** lives in `06_PROOF_SYSTEM/` and
  is the active research lane (Engine-semantics proof system at
  v0.6 framing).
- These three are not separate roads. They are one unified Core
  body called **"Core v1 incomplete"** — a working tree that
  preserves frozen surfaces and continues research work toward
  the next official Core release.

This roadmap supersedes the per-track V1-specific
(`00_PROJECT_CORE/ROADMAP.md`) and V2-specific (`V2_ROADMAP.md`)
roadmaps as the **top-level** unified plan. Both predecessors are
preserved as historical surfaces.

---

## Tracks (parallel, not sequential)

### Track A — Frozen V1 release surface (DO NOT TOUCH)

- ACOR-1.1 (`core-v1-substrate-candidate-or1.1`) is the current
  official release.
- ACOR-1 (`core-v1-substrate-candidate-or1`) is preserved as
  superseded.
- 26 `backup/v1-substrate-candidate-*` branches + matching tags +
  4 `v1-substrate-20260413-*` tags preserve all V1 substrate
  candidate iterations.
- Truth surface in `00_PROJECT_CORE/` is the canonical V1 evidence
  artifact set (M0..M11 gate verifications, capstones, audits, lock
  manifest, locked release zip).
- This track is **not modified by any other track**. It exists to
  prove the V1 substrate candidate exactly as audited.

### Track B — V2 research / proof-system continuation

- Preserve the V2 charter, capture protocol, benchmark set, and
  pilot runbook.
- Continue V2 decode-engine work in
  `05_ACTIVE_DEV/aurexis_lang/src/aurexis_lang/v2_decode/`.
- Branch `working/core-v2` is the active V2 dev branch.
- `core-v2-decode-engine-d3` is the current V2 marker tag.
- V2 deliverables (real-evidence calibration loop, screen-based
  benchmark, before/after delta) are documented in `V2_*.md`.

### Track C — Engine-semantics proof system (current research)

The active research surface, lives at
`06_PROOF_SYSTEM/aurexis_research_sim/`.

- Seven proof categories, each a real Engine-semantics question:
  VISUAL_RELATIONSHIP, PHOXEL_RASTER_LAW, SEMANTIC_STABILITY,
  CALIBRATION_CONFIDENCE, PHYSICAL_SIMULATION,
  REAL_EVIDENCE_ANCHORING, LANGUAGE_CONSTRUCTION.
- 21 source modules, 21 test files, 221 passing tests.
- Master Engine-semantics index at
  `reports/PROOF_INDEX.md`.
- Current per-family confidence states:
  - cardinality / repetition / role_zone / symmetry: HOLD
  - ordering: REJECT (multi-evidence: PRIMITIVE_AWARE_HELPS at
    boundary, SUSPECT at validation -> REJECT)
  - adjacency / orientation / hierarchy: NEED_MORE_EVIDENCE
- Streamlit UI at
  `06_PROOF_SYSTEM/aurexis_research_sim/app.py`.

---

## What's next (any-track)

The order below is a suggested order, not a fixed sequence.

1. **Move REAL_EVIDENCE_ANCHORING from STUB to PARTIAL.** At least
   one real-image intake test where a synthetic prediction is
   compared to a captured photograph. Small. Connects Track C to
   Track B's capture-protocol work.
2. **Unblock the 3 remaining METRIC_GAP_ROI_INSENSITIVE families**
   (adjacency, orientation, hierarchy): build ROI-aware variants
   of their metrics so the boundary map fills out 8/8.
3. **Promote the strip-based repetition fix to
   `binding.repetition_survival_bound`** in place. This graduates
   repetition from SEMANTIC_UNSTABLE to SEMANTIC_STABLE in the
   v0.6 dossier.
4. **Continue V2 decode-engine work** on `working/core-v2`. Keep
   it independent unless it consumes proof-system evidence.
5. **Define the next Core official release line.** ACOR-1.1 is
   frozen. The next official release will require: (a) the proof
   system showing TRUST states for promoted primitives,
   (b) at least one real-evidence anchor, (c) explicit semantic
   stability evidence for every promoted primitive,
   (d) a fresh code-provenance audit. Until those, the public
   front-page release stays at ACOR-1.1.

---

## What we're NOT doing here

- Not deleting V1 release tags or backup branches/tags.
- Not silently overwriting any prior work.
- Not pushing a new official release. ACOR-1.1 stays the public
  release until the next Core gate explicitly closes.
- Not drifting into Aurexis E/D (Client / Wrapper / Runtime)
  implementation — that lives in `Aurexis_ED/` outside this repo.
- Not turning the proof system into a product. It is research
  evidence for Core law decisions.

---

## Pointers

- Frozen V1 truth surface: `00_PROJECT_CORE/`.
- V2 charter and roadmap: `V2_CHARTER.md`, `V2_ROADMAP.md`.
- Current proof-system: `06_PROOF_SYSTEM/aurexis_research_sim/`.
- Top-level unification report: `CORE_UNIFICATION_REPORT.md`.
- Tree map: `CORE_TREE_MAP.md`.
- Grok auditor lane: `GROK_AUDIT_LANE.md`.
- Push plan: `GITHUB_PUSH_PLAN.md`.
