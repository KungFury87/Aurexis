# Aurexis Research Simulation Suite - STATUS / CHECKBACK

**Current version:** v0.6 (Engine-semantics proof system reframing)
**Date packaged:** 2026-04-25
**Runnable from clean extraction:** Yes - verified.

Aurexis Core = Engine / Codec / Standard.
Aurexis E/D = Client / Wrapper / Runtime.

The suite is an Engine-semantics proof system, not a "simulate
everything" simulator and not a "fake camera wins" generator. Every
output is meant to answer a useful Engine-semantic question.

Note on on-disk folder name: the source folder on Vincent's machine is
still `Aurexis_Research_Sim_v0_1` for historical reasons. The
delivered checkback zip expands to `Aurexis_Research_Sim_v0_6/`.

---

## v0.6 milestone implemented

Previous passes (v0.1 - v2.0 in the milestone numbering) shipped a
working sensor-path simulator with relation probes, stress sweeps,
atlas, validation, redesign, interaction, binding family, arbitration,
fusion, primitive-aware target conditioning, coverage, boundary
mapping, and unlock for ordering/symmetry. v0.5 in the
Engine-semantics framing accepts all of that as real progress.

v0.5's weakness was framing. The suite was structured more like a
relation-stress simulator than an Engine-semantics proof system. v0.6
keeps every working v0.1-v2.0 mechanism intact and adds an
Engine-semantics proof layer on top of them.

### What's new

- New `aurexis_sim/proof_taxonomy.py` - 7-category registry +
  per-report category mapping.
- New `aurexis_sim/confidence.py` - calibrated confidence-state
  evaluator combining boundary + validation per family into TRUST /
  HOLD / DOWNGRADE / REJECT / NEED_MORE_EVIDENCE.
- New `aurexis_sim/semantic_stability.py` - recovered-semantic-
  value-vs-truth stability scoring across SIM_MILD and SIM_HOSTILE
  scenarios (cardinality + repetition).
- New `aurexis_sim/proof_index.py` - master Engine-semantics index.
- New shipped reports `PROOF_TAXONOMY.md` / `proof_taxonomy.json`,
  `CONFIDENCE.md` / `confidence.json`, `SEMANTIC_STABILITY.md` /
  `semantic_stability.json`, `PROOF_INDEX.md` / `proof_index.json`.
- Streamlit UI: new "Engine-semantics proof index (v0.6)" panel.
- `aurexis_sim/__init__.py` -> `0.6.0`.
- Smoke banner: `Aurexis Research Sim v0.6 - smoke run (Engine-semantics proof system)`.
- New v0.6 smoke section: "Engine-semantics proof index" - prints
  per-category status + per-family table at the END of the smoke run.

### What v0.6 proves that v0.5 did not

The v0.6 master per-family table from `reports/PROOF_INDEX.md`:

    family       boundary_tag                  validation     confidence_state    semantic_stability
    cardinality  PRIMITIVE_AWARE_HELPS         -              HOLD                SEMANTIC_STABLE
    repetition   PRIMITIVE_AWARE_HELPS         WEAK_ROBUST    HOLD                SEMANTIC_UNSTABLE
    role_zone    PRIMITIVE_AWARE_HELPS         WEAK_ROBUST    HOLD                -
    ordering     PRIMITIVE_AWARE_HELPS         SUSPECT        REJECT              -
    symmetry     PRIMITIVE_AWARE_HELPS         -              HOLD                -
    adjacency    METRIC_GAP_ROI_INSENSITIVE    -              NEED_MORE_EVIDENCE  -
    orientation  METRIC_GAP_ROI_INSENSITIVE    -              NEED_MORE_EVIDENCE  -
    hierarchy    METRIC_GAP_ROI_INSENSITIVE    -              NEED_MORE_EVIDENCE  -

Two Engine-semantics signals here that were not surfaced in v0.5:

1. **ordering: REJECT under multi-evidence calibration.** v2.0's
   boundary map said ordering's primitive-aware metric helps in the
   distractor composite, but v0.8's validation flagged the promoted
   ordering primitive as SUSPECT under broader stress + negative
   controls. v0.6's confidence calibrator combines those signals and
   produces REJECT - the Engine-semantics conclusion is "ordering
   in its current promoted form is not law-worthy; the arbitration
   win is local, the broader test failed."
2. **repetition: SEMANTIC_UNSTABLE under naive metric, recoverable
   only with strip-aware metric.** v0.6's semantic-stability proof
   runs the v0.5 full-row autocorrelation across SIM_MILD and
   SIM_HOSTILE; under heavy blur the recovered period collapses to
   lag=1. The strip-aware metric introduced in v1.8 is what gives
   repetition stable semantics. Engine-semantics conclusion: the
   repetition law requires ROI/strip-aware evaluation; the simple
   metric is law-fragile.

The v0.6 reframing makes these conclusions visible because the
calibrator merges signals across categories. It is not new evidence;
it is sharper integration of existing evidence into Engine-semantics
verdicts.

### Stale-label cleanup performed

- `aurexis_sim/__init__.py` -> 0.6.0.
- `aurexis_sim/app.py` stub -> v0.6.
- `aurexis_sim/smoke.py` banner -> v0.6 (Engine-semantics proof
  system). Historical chronological section labels (v0.3 per-stage,
  v0.4 stress, v0.7 scenario atlas, v0.8 validation, v0.9 redesign,
  v1.0 - v2.0 milestone sections) are preserved as lineage markers
  so readers can trace evolution.
- Root `app.py` page title / caption -> v0.6.
- STATUS / README / RUN_ME_FIRST rewritten under Engine-semantics
  framing.

### Honest scope limits (v0.6 still NOT claiming)

- REAL_EVIDENCE_ANCHORING is STUB - no real-image intake.
- SEMANTIC_STABILITY tests cardinality and repetition only.
  ordering / symmetry / role_zone semantic stability are not yet
  evaluated explicitly.
- ROI-aware metrics for adjacency / orientation / hierarchy are NOT
  built; those families remain METRIC_GAP_ROI_INSENSITIVE.
- The confidence calibrator is a small deterministic table, not a
  learned classifier.
- All v0.1 - v2.0 mechanisms preserved; this is a reframing pass,
  not a probe-coverage pass.
- Still not a decoder, not E/D work, not a runtime, not a camera app.

---

## Files changed / added in v0.6

New:
- `aurexis_sim/proof_taxonomy.py` - 7-category registry + report
  mapping + CLI.
- `aurexis_sim/confidence.py` - confidence-state combinator + dossier
  + report writer + CLI.
- `aurexis_sim/semantic_stability.py` - recovered-value semantic
  stability across two reference scenarios + CLI.
- `aurexis_sim/proof_index.py` - master Engine-semantics index + CLI.
- `tests/test_proof_index.py` - 19 tests covering proof categories,
  category status, REAL_EVIDENCE_ANCHORING is STUB,
  categories_for_report, category index includes v0.6 artifacts,
  taxonomy report round-trip, confidence states set, confidence
  combinator boundaries (TRUST/HOLD/DOWNGRADE/REJECT/NEED_MORE_EVIDENCE),
  confidence dossier shape, semantic-stability scenarios set,
  cardinality stable verdict, repetition evaluation produces verdict,
  semantic-stability dossier shape and report round-trip, proof index
  shape, 5+ families present, ordering's calibrated REJECT, report
  round-trip.
- `reports/PROOF_TAXONOMY.md` / `proof_taxonomy.json`,
  `CONFIDENCE.md` / `confidence.json`,
  `SEMANTIC_STABILITY.md` / `semantic_stability.json`,
  `PROOF_INDEX.md` / `proof_index.json` shipped by bake.

Modified:
- `aurexis_sim/__init__.py` -> 0.6.0.
- `aurexis_sim/app.py` stub -> v0.6.
- `aurexis_sim/bake_examples.py` - calls 4 new writers.
- `aurexis_sim/smoke.py` - banner -> v0.6; v0.6 Engine-semantics
  proof index block appended.
- `app.py` (root) - v0.6 title/caption; added Engine-semantics proof
  index panel.
- `STATUS.md`, `README.md`, `RUN_ME_FIRST.txt` rewritten under the
  Engine-semantics framing.

---

## How to run locally (verified)

From the extracted `Aurexis_Research_Sim_v0_6/` folder (Python 3.10+):

    pip install -r requirements.txt
    python -m streamlit run app.py
    python -m aurexis_sim.smoke
    python -m aurexis_sim.proof_index
    python -m aurexis_sim.proof_taxonomy
    python -m aurexis_sim.confidence
    python -m aurexis_sim.semantic_stability
    python -m pytest tests -q        # expect 221 passed
    python -m aurexis_sim.bake_examples

---

## Verification evidence (from clean extraction)

- `python -m pytest tests -q`: **221 passed**.
- `python -m aurexis_sim.proof_index`: prints v0.6 proof-category
  status table + master per-family Engine-semantics table.
- `python -m aurexis_sim.bake_examples`: `reports/` now contains
  the full v0.5 stress / v1.x / v2.0 bundle plus
  **PROOF_INDEX.md, proof_index.json, PROOF_TAXONOMY.md,
  proof_taxonomy.json, CONFIDENCE.md, confidence.json,
  SEMANTIC_STABILITY.md, semantic_stability.json**.
- Streamlit UI shows the v0.6 Engine-semantics proof-index panel
  with per-category status + per-family table.

---

## Remaining for v0.7+

- ROI-aware metrics for adjacency / orientation / hierarchy so the
  boundary map fills out 8 of 8 and the confidence calibrator can
  promote them past NEED_MORE_EVIDENCE.
- Semantic-stability proofs for ordering, symmetry, role_zone (not
  just cardinality + repetition).
- Real-evidence anchoring intake stub.
- Promote the strip-based repetition fix to
  `binding.repetition_survival_bound` in place; this would let
  repetition's SEMANTIC_UNSTABLE verdict graduate to SEMANTIC_STABLE
  in the v0.6 dossier.
- Granularity-aware generic ranker; weighted-product fusion;
  proposal-confidence scoring + abstain.
- Decoder / recoverer module (still NOT in scope for v0.x).
- Additional primitives: local label binding, region priority,
  color-vs-spatial grouping.
- Photon-count shot noise per channel; measured-PSF loading; OLPF
  distinct from gaussian; gradient demosaic; white-balance + CCM.

---

## Folder structure (after unzip)

    Aurexis_Research_Sim_v0_6/
    app.py                                  (Streamlit entry, ROOT)
    conftest.py
    pyproject.toml
    README.md / STATUS.md / RUN_ME_FIRST.txt
    requirements.txt
    run.bat / run.sh / run_smoke.bat
    aurexis_sim/
        __init__.py                         (version 0.6.0)
        app.py                              (deprecated stub)
        color.py, sensor.py
        relations.py, stress.py, atlas.py, validation.py, redesign.py
        interaction.py, binding.py, soft_binding.py
        inferred_binding.py
        arbitration.py
        distractor_arbitration.py
        fusion.py
        primitive_aware.py
        coverage.py
        boundary.py
        unlock.py
        proof_taxonomy.py                   (NEW v0.6)
        confidence.py                       (NEW v0.6)
        semantic_stability.py               (NEW v0.6)
        proof_index.py                      (NEW v0.6)
        truth.py, simulate.py, metrics.py, presets.py
        smoke.py, bake_examples.py, utils.py
    presets/*.json                          (20 presets)
    examples/                               (per-preset baked outputs)
    reports/
        SUMMARY.md, stress_report.*, stress_grids.json,
        confusion_tables.json,
        atlas.json / ATLAS.md,
        scenario_atlas.json / SCENARIO_ATLAS.md,
        validation.json / VALIDATION.md,
        redesign.json / REDESIGN.md,
        interaction.json / INTERACTION.md,
        binding.json / BINDING.md,
        soft_binding.json / SOFT_BINDING.md,
        inferred_binding.json / INFERRED_BINDING.md,
        arbitration.json / ARBITRATION.md,
        distractor_arbitration.json / DISTRACTOR_ARBITRATION.md,
        fusion.json / FUSION.md,
        primitive_aware.json / PRIMITIVE_AWARE.md,
        coverage.json / COVERAGE.md,
        boundary.json / BOUNDARY.md,
        unlock.json / UNLOCK.md,
        proof_taxonomy.json / PROOF_TAXONOMY.md     (NEW v0.6)
        confidence.json / CONFIDENCE.md             (NEW v0.6)
        semantic_stability.json / SEMANTIC_STABILITY.md  (NEW v0.6)
        proof_index.json / PROOF_INDEX.md           (NEW v0.6)
    tests/  (21 files, 221 tests)
    runs/
