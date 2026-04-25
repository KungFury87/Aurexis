# Aurexis Research Sim v0.6 - Proof-category taxonomy

Engine-semantics proof system. Each category is a question; shipped reports are answers (or partial answers) to that question.

## Category index

| category | status | question |
|---|---|---|
| `VISUAL_RELATIONSHIP` | STRONG | Does each visual relationship primitive survive the display/capture chain, and by how much? |
| `PHOXEL_RASTER_LAW` | PARTIAL | Does primitive evaluation depend on ROI/phoxel-cell choice? When does ROI matter, when does it not, and how does inferred ROI compare to oracle ROI? |
| `SEMANTIC_STABILITY` | PARTIAL | Is the SEMANTIC VALUE recovered (cardinality count, repetition period, ordering axis, symmetry axis, etc.) stable across capture scenarios, or does it drift? |
| `CALIBRATION_CONFIDENCE` | PARTIAL | What is the calibrated trust state per primitive family given all available evidence: TRUST / HOLD / DOWNGRADE / REJECT / NEED_MORE_EVIDENCE? |
| `PHYSICAL_SIMULATION` | STRONG | How do primitive scores change under display/capture stress (blur, motion blur, rolling shutter, sensor Bayer, noise, quantize)? |
| `REAL_EVIDENCE_ANCHORING` | STUB | Does synthetic prediction match real captured imagery for the same primitives? |
| `LANGUAGE_CONSTRUCTION` | STRONG | Should this primitive be promoted, redesigned, or rejected as a visual-language unit? Does target-conditioned arbitration help, or is generic enough? |

## Supporting reports per category

### VISUAL_RELATIONSHIP (Visual relationship proofs)

Status: **STRONG**

Question: _Does each visual relationship primitive survive the display/capture chain, and by how much?_

Shipped reports:
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

Status: **PARTIAL**

Question: _Does primitive evaluation depend on ROI/phoxel-cell choice? When does ROI matter, when does it not, and how does inferred ROI compare to oracle ROI?_

Shipped reports:
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

Status: **PARTIAL**

Question: _Is the SEMANTIC VALUE recovered (cardinality count, repetition period, ordering axis, symmetry axis, etc.) stable across capture scenarios, or does it drift?_

Shipped reports:
- `INTERACTION.md`
- `PROOF_INDEX.md`
- `SCENARIO_ATLAS.md`
- `SEMANTIC_STABILITY.md`
- `interaction.json`
- `proof_index.json`
- `scenario_atlas.json`
- `semantic_stability.json`

### CALIBRATION_CONFIDENCE (Calibration and confidence proofs)

Status: **PARTIAL**

Question: _What is the calibrated trust state per primitive family given all available evidence: TRUST / HOLD / DOWNGRADE / REJECT / NEED_MORE_EVIDENCE?_

Shipped reports:
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

Status: **STRONG**

Question: _How do primitive scores change under display/capture stress (blur, motion blur, rolling shutter, sensor Bayer, noise, quantize)?_

Shipped reports:
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

Status: **STUB**

Question: _Does synthetic prediction match real captured imagery for the same primitives?_

Shipped reports:
- `PROOF_INDEX.md`
- `proof_index.json`

### LANGUAGE_CONSTRUCTION (Language-construction proofs)

Status: **STRONG**

Question: _Should this primitive be promoted, redesigned, or rejected as a visual-language unit? Does target-conditioned arbitration help, or is generic enough?_

Shipped reports:
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
