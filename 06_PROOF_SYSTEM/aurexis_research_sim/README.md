# Aurexis Research Simulation Suite - v0.6

**Engine-semantics proof system.**

The Aurexis testing suite is not "simulate everything" and not
"generate fake camera wins." It is an Engine-semantics proof system:
controlled evidence, exposed failure modes, mapped limits, and
information that helps decide which Engine law or semantic rule
needs to change.

v0.6 reframes the suite around seven proof categories and adds three
explicit Engine-semantics outputs: a proof-category taxonomy, a
calibrated confidence-state evaluator (TRUST/HOLD/DOWNGRADE/REJECT/
NEED_MORE_EVIDENCE) per primitive family, and a semantic-stability
evaluator that asks whether the recovered semantic value (count,
period) matches the truth across capture scenarios. A master
PROOF_INDEX rolls everything up.

**Aurexis Core** = the Engine / Codec / Standard.
**Aurexis E/D** = the Client / Wrapper / Runtime.

**Not:** E/D, runtime, camera app, decoder.
**Is:** a local Engine-semantics proof harness; inspectable;
parameter-swept; honest.

## Install + run

    pip install -r requirements.txt
    run.bat                                   # or ./run.sh, or: python -m streamlit run app.py
    run_smoke.bat                             # or: python -m aurexis_sim.smoke
    python -m aurexis_sim.proof_index         # v0.6 master Engine-semantics index
    python -m aurexis_sim.proof_taxonomy      # v0.6 proof-category taxonomy
    python -m aurexis_sim.confidence          # v0.6 calibrated confidence states
    python -m aurexis_sim.semantic_stability  # v0.6 semantic-stability proof
    # ... all v0.1-v2.0 lineage modules still runnable:
    python -m aurexis_sim.stress
    python -m aurexis_sim.atlas
    python -m aurexis_sim.validation
    python -m aurexis_sim.redesign
    python -m aurexis_sim.interaction
    python -m aurexis_sim.binding
    python -m aurexis_sim.soft_binding
    python -m aurexis_sim.inferred_binding
    python -m aurexis_sim.arbitration
    python -m aurexis_sim.distractor_arbitration
    python -m aurexis_sim.fusion
    python -m aurexis_sim.primitive_aware
    python -m aurexis_sim.coverage
    python -m aurexis_sim.boundary
    python -m aurexis_sim.unlock
    python -m pytest tests -q                 # expect 221 passed
    python -m aurexis_sim.bake_examples

## Seven proof categories (v0.6)

| category | status | question |
|---|---|---|
| `VISUAL_RELATIONSHIP` | STRONG | Does each visual relationship primitive survive the display/capture chain? |
| `PHOXEL_RASTER_LAW` | PARTIAL | Does primitive evaluation depend on ROI / phoxel-cell choice? |
| `SEMANTIC_STABILITY` | PARTIAL | Is the recovered semantic value (count, period) stable across capture scenarios? |
| `CALIBRATION_CONFIDENCE` | PARTIAL | What is the calibrated trust state per primitive family? |
| `PHYSICAL_SIMULATION` | STRONG | How do scores change under display/capture stress? |
| `REAL_EVIDENCE_ANCHORING` | STUB | Does synthetic prediction match real captured imagery? (not implemented) |
| `LANGUAGE_CONSTRUCTION` | STRONG | Should this primitive be promoted, redesigned, or rejected? |

## Master per-family Engine-semantics table (v0.6 shipped)

| family | boundary_tag | validation | confidence_state | semantic_stability |
|---|---|---|---|---|
| cardinality  | PRIMITIVE_AWARE_HELPS        | -           | HOLD              | SEMANTIC_STABLE     |
| repetition   | PRIMITIVE_AWARE_HELPS        | WEAK_ROBUST | HOLD              | SEMANTIC_UNSTABLE   |
| role_zone    | PRIMITIVE_AWARE_HELPS        | WEAK_ROBUST | HOLD              | -                   |
| ordering     | PRIMITIVE_AWARE_HELPS        | SUSPECT     | **REJECT**        | -                   |
| symmetry     | PRIMITIVE_AWARE_HELPS        | -           | HOLD              | -                   |
| adjacency    | METRIC_GAP_ROI_INSENSITIVE   | -           | NEED_MORE_EVIDENCE | -                  |
| orientation  | METRIC_GAP_ROI_INSENSITIVE   | -           | NEED_MORE_EVIDENCE | -                  |
| hierarchy    | METRIC_GAP_ROI_INSENSITIVE   | -           | NEED_MORE_EVIDENCE | -                  |

Headline Engine-semantics findings v0.6 surfaces:

- **ordering: REJECT** despite PRIMITIVE_AWARE_HELPS at the boundary.
  The validation pass flagged the promoted ordering primitive as
  SUSPECT under hard-variant + negative-control stress (an existing
  v0.8 result). The v0.6 calibrator combines those two signals and
  produces REJECT - the multi-evidence calibrated state. This is
  the kind of cross-evidence trust calibration the Engine-semantics
  framing demands.
- **repetition: SEMANTIC_UNSTABLE** under the v0.6 semantic-stability
  proof (full-row autocorrelation under blur returns lag=1, not the
  truth period). The strip-based metric introduced in v1.8 does
  recover the period - so the Engine-semantics signal is "the
  primitive needs an ROI / strip-aware metric to have stable
  semantics." That's a law-worthy distinction.
- **adjacency / orientation / hierarchy: NEED_MORE_EVIDENCE.** Their
  metrics are still ROI-insensitive; the suite does not yet have
  ROI-aware variants for them. The Engine-semantics index
  surgically tags these as "test not possible until metric is
  built," not "fine."

## What v0.6 is NOT claiming

- A learned ranker, learned classifier, or any ML.
- Real-evidence anchoring (REAL_EVIDENCE_ANCHORING is STUB).
- Component-level structural symmetry / vertical-axis ordering /
  spatial-arrangement role_zone (carryforward limits).
- ROI-aware variants for adjacency / orientation / hierarchy.
- Still not a decoder, not E/D, not a runtime, not a camera app.

## Roadmap (v0.7+)

ROI-aware metrics for adjacency / orientation / hierarchy so the
boundary map fills out to 8 of 8; richer semantic-stability tests
(ordering direction, symmetry axis); a real-evidence intake stub
that anchors at least one synthetic prediction against a captured
image; promote the strip-based repetition fix to
`binding.repetition_survival_bound` in place; granularity-aware
generic ranker; proposal-confidence scoring + abstain.

## Folder layout (after unzip)

See STATUS.md for the full tree. Summary: root `app.py` entry,
`aurexis_sim/` with 31 source files (v0.6 adds proof_taxonomy,
confidence, semantic_stability, proof_index), 20 presets, baked
`examples/`, shipped `reports/` (v0.5 stress bundle through v2.0
unlock + **v0.6 proof-system reframing artifacts: PROOF_INDEX.md,
PROOF_TAXONOMY.md, CONFIDENCE.md, SEMANTIC_STABILITY.md**) totaling
40+ artifacts, 21-file `tests/` suite (221 tests).
