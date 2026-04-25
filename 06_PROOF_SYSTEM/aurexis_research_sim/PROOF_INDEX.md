# Aurexis Engine-semantics proof index (v0.6)

This is the top-level Engine-semantics index. The Aurexis
testing suite is an Engine-semantics proof system, not a
simulator product.

It answers seven proof-category questions; below are status
tags + per-family evidence rolling up boundary tags, validation,
calibrated confidence states, and semantic-stability verdicts.

## Proof-category status

| category | status | question |
|---|---|---|
| `VISUAL_RELATIONSHIP` | **STRONG** | Does each visual relationship primitive survive the display/capture chain, and by how much? |
| `PHOXEL_RASTER_LAW` | **PARTIAL** | Does primitive evaluation depend on ROI/phoxel-cell choice? When does ROI matter, when does it not, and how does inferred ROI compare to oracle ROI? |
| `SEMANTIC_STABILITY` | **PARTIAL** | Is the SEMANTIC VALUE recovered (cardinality count, repetition period, ordering axis, symmetry axis, etc.) stable across capture scenarios, or does it drift? |
| `CALIBRATION_CONFIDENCE` | **PARTIAL** | What is the calibrated trust state per primitive family given all available evidence: TRUST / HOLD / DOWNGRADE / REJECT / NEED_MORE_EVIDENCE? |
| `PHYSICAL_SIMULATION` | **STRONG** | How do primitive scores change under display/capture stress (blur, motion blur, rolling shutter, sensor Bayer, noise, quantize)? |
| `REAL_EVIDENCE_ANCHORING` | **STUB** | Does synthetic prediction match real captured imagery for the same primitives? |
| `LANGUAGE_CONSTRUCTION` | **STRONG** | Should this primitive be promoted, redesigned, or rejected as a visual-language unit? Does target-conditioned arbitration help, or is generic enough? |

## Master per-family Engine-semantics table

| family | boundary_tag | validation | confidence_state | semantic_stability |
|---|---|---|---|---|
| adjacency | METRIC_GAP_ROI_INSENSITIVE | - | **NEED_MORE_EVIDENCE** | - |
| cardinality | PRIMITIVE_AWARE_HELPS | - | **HOLD** | SEMANTIC_STABLE |
| hierarchy | METRIC_GAP_ROI_INSENSITIVE | - | **NEED_MORE_EVIDENCE** | - |
| ordering | PRIMITIVE_AWARE_HELPS | SUSPECT | **REJECT** | - |
| orientation | METRIC_GAP_ROI_INSENSITIVE | - | **NEED_MORE_EVIDENCE** | - |
| repetition | PRIMITIVE_AWARE_HELPS | WEAK_ROBUST | **HOLD** | SEMANTIC_UNSTABLE |
| role_zone | PRIMITIVE_AWARE_HELPS | WEAK_ROBUST | **HOLD** | - |
| symmetry | PRIMITIVE_AWARE_HELPS | - | **HOLD** | - |

## Reports per category

### VISUAL_RELATIONSHIP (Visual relationship proofs)

- status: **STRONG**
- question: _Does each visual relationship primitive survive the display/capture chain, and by how much?_
- shipped reports:
  - `ATLAS.md`
  - `BOUNDARY.md`
  - `COVERAGE.md`
  - `INTERACTION.md`
  - `PRIMITIVE_AWARE.md`
  - `PROOF_INDEX.md`
  - `SCENARIO_ATLAS.md`
  - `SUMMARY.md`
  - `UNLOCK.md`
  - `VALIDATION.md`
  - `atlas.json`
  - `boundary.json`
  - `confusion_tables.json`
  - `coverage.json`
  - `interaction.json`
  - `primitive_aware.json`
  - `proof_index.json`
  - `scenario_atlas.json`
  - `stress_grids.json`
  - `stress_report.json`
  - `unlock.json`
  - `validation.json`

### PHOXEL_RASTER_LAW (Phoxel/raster law proofs)

- status: **PARTIAL**
- question: _Does primitive evaluation depend on ROI/phoxel-cell choice? When does ROI matter, when does it not, and how does inferred ROI compare to oracle ROI?_
- shipped reports:
  - `BINDING.md`
  - `COVERAGE.md`
  - `INFERRED_BINDING.md`
  - `PROOF_INDEX.md`
  - `SOFT_BINDING.md`
  - `binding.json`
  - `coverage.json`
  - `inferred_binding.json`
  - `proof_index.json`
  - `soft_binding.json`

### SEMANTIC_STABILITY (Semantic stability proofs)

- status: **PARTIAL**
- question: _Is the SEMANTIC VALUE recovered (cardinality count, repetition period, ordering axis, symmetry axis, etc.) stable across capture scenarios, or does it drift?_
- shipped reports:
  - `INTERACTION.md`
  - `PROOF_INDEX.md`
  - `SCENARIO_ATLAS.md`
  - `SEMANTIC_STABILITY.md`
  - `interaction.json`
  - `proof_index.json`
  - `scenario_atlas.json`
  - `semantic_stability.json`

### CALIBRATION_CONFIDENCE (Calibration and confidence proofs)

- status: **PARTIAL**
- question: _What is the calibrated trust state per primitive family given all available evidence: TRUST / HOLD / DOWNGRADE / REJECT / NEED_MORE_EVIDENCE?_
- shipped reports:
  - `ARBITRATION.md`
  - `BOUNDARY.md`
  - `CONFIDENCE.md`
  - `DISTRACTOR_ARBITRATION.md`
  - `FUSION.md`
  - `PROOF_INDEX.md`
  - `REDESIGN.md`
  - `UNLOCK.md`
  - `VALIDATION.md`
  - `arbitration.json`
  - `boundary.json`
  - `confidence.json`
  - `distractor_arbitration.json`
  - `fusion.json`
  - `proof_index.json`
  - `redesign.json`
  - `unlock.json`
  - `validation.json`

### PHYSICAL_SIMULATION (Simulator-supported physical proofs)

- status: **STRONG**
- question: _How do primitive scores change under display/capture stress (blur, motion blur, rolling shutter, sensor Bayer, noise, quantize)?_
- shipped reports:
  - `ATLAS.md`
  - `PROOF_INDEX.md`
  - `SCENARIO_ATLAS.md`
  - `SUMMARY.md`
  - `atlas.json`
  - `confusion_tables.json`
  - `proof_index.json`
  - `scenario_atlas.json`
  - `stress_grids.json`
  - `stress_report.json`

### REAL_EVIDENCE_ANCHORING (Real-evidence anchoring)

- status: **STUB**
- question: _Does synthetic prediction match real captured imagery for the same primitives?_
- shipped reports:
  - `PROOF_INDEX.md`
  - `proof_index.json`

### LANGUAGE_CONSTRUCTION (Language-construction proofs)

- status: **STRONG**
- question: _Should this primitive be promoted, redesigned, or rejected as a visual-language unit? Does target-conditioned arbitration help, or is generic enough?_
- shipped reports:
  - `ARBITRATION.md`
  - `BOUNDARY.md`
  - `COVERAGE.md`
  - `DISTRACTOR_ARBITRATION.md`
  - `FUSION.md`
  - `PRIMITIVE_AWARE.md`
  - `PROOF_INDEX.md`
  - `REDESIGN.md`
  - `UNLOCK.md`
  - `arbitration.json`
  - `boundary.json`
  - `coverage.json`
  - `distractor_arbitration.json`
  - `fusion.json`
  - `primitive_aware.json`
  - `proof_index.json`
  - `redesign.json`
  - `unlock.json`

## Honest scope (v0.6)

- VISUAL_RELATIONSHIP / PHYSICAL_SIMULATION /
  LANGUAGE_CONSTRUCTION are STRONG.
- PHOXEL_RASTER_LAW is PARTIAL (binding family covers it).
- SEMANTIC_STABILITY is PARTIAL (v0.6 introduces explicit
  metric; cardinality + repetition only).
- CALIBRATION_CONFIDENCE is PARTIAL (v0.6 introduces explicit
  per-family TRUST/HOLD/DOWNGRADE/REJECT/NEED_MORE_EVIDENCE).
- REAL_EVIDENCE_ANCHORING is STUB (not implemented).
