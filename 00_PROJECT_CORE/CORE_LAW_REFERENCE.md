# AUREXIS CORE — Core Law Quick Reference
**Status:** FROZEN at Gate 1 (V20). Do not modify without project-law-level discussion.

---

## The 7 Frozen Law Sections

### 1. Phoxel Record Law
Every visual claim must be backed by a canonical phoxel record containing:
- `image_anchor.pixel_coordinates` — literal pixel position, never null
- `world_anchor_state.status` — one of: unknown / estimated / resolved
- `photonic_signature.pixel_data_available` — boolean
- `photonic_signature.camera_metadata` — device info
- `time_slice.image_timestamp` — when the observation was made
- `relation_set` — list of spatial relations (may be empty)
- `integrity_state.synthetic` — must be FALSE for real claims
- `integrity_state.evidence_chain` — list of frame IDs

**Violation = CRITICAL rejection.**

---

### 2. Native Relations Law
Spatial relationships must be:
- One of the allowed kinds: position, adjacency, direction, distance, containment, boundary, region_membership, sequence (primary) OR scale, hierarchy, overlap, continuity, transition (higher-order)
- Backed by a `physical_measurement` with a real observed value
- Backed by `pixel_space_verification` with `image_grounded: true`
- NOT `abstract_semantic: true`

**Abstract semantics are forbidden.** "Near" is only legal if you can measure the pixel distance.

---

### 3. World/Image Authority Law
Two registers must remain alive and separate:
- **World** = primary authority (ground truth reality)
- **Image** = primary access (what the camera actually shows)

Violations (all CRITICAL or ERROR):
- Model overrides the observed image → CRITICAL
- Image treated as sole final world truth → ERROR
- World knowledge asserted without image evidence → ERROR
- Common-sense override suppresses observed evidence → ERROR

---

### 4. Executable Promotion Law
A claim only becomes EXECUTABLE after passing ALL of:
1. `evidence_validated: true`
2. `multi_frame_consistent: true`
3. `geometric_coherence: true`
4. `cross_register_consistency: true`
5. `language_legal: true`
6. `bounded_inference: true`
7. `confidence >= 0.7`
8. No unresolved reasons / blocked reasons

`promotion_by_assumption` is forbidden.

---

### 5. Illegal Inference Law — 9 Blocked Claims

| Rule ID | What it blocks |
|---------|---------------|
| `full_world_truth_from_single_observation` | Single observation ≠ complete world truth |
| `exact_world_placement_from_weak_evidence` | Exact placement requires strong evidence |
| `hidden_geometry_or_contents_claim` | Cannot claim what you can't observe |
| `executability_from_pattern_alone` | Pattern recognition ≠ executable meaning |
| `identity_from_resemblance_alone` | "Looks like X" ≠ "Is X" |
| `causality_or_function_from_appearance_alone` | Appearance ≠ function or intent |
| `permanence_from_single_frame` | One frame ≠ persistence over time |
| `earned_physical_proof_without_earned_tier` | Can't claim earned proof from lab/authored data |
| `world_claim_without_image_grounding` | World claims need image-grounded evidence |

---

### 6. Current Tech Floor Law
System must operate within current mobile hardware constraints:
- Max processing time: 30 seconds
- Max memory: 500 MB
- Max battery impact: 5% per minute
- No exotic hardware dependencies

---

### 7. Future Tech Ceiling Law
Better hardware must improve the system without requiring:
- Ontology rewrite
- Core law shape changes
- Behavior changes tied to hardware
- Invalidation of current-floor results

Better cameras → better phoxels → better results. The law stays the same.

---

## Execution Status Ladder

| Status | Meaning |
|--------|---------|
| DESCRIPTIVE | Observed but not validated |
| ESTIMATED | Partial evidence, reasonable estimate |
| VALIDATED | Evidence-validated in a single frame |
| EXECUTABLE | Multi-frame consistent, passed all promotion gates |

Things can only move UP this ladder. They cannot skip steps.

---

## Evidence Tier System

| Tier | Label | Can claim |
|------|-------|----------|
| LAB | Simulated/synthetic | Lab-level only |
| AUTHORED | Hand-crafted test assets | Authored-asset evidence |
| REAL_CAPTURE | Actual camera input | Real-world pipeline validation |
| EARNED | Multi-frame validated real camera | Earned physical proof |

The system is architecturally incapable of claiming EARNED tier from LAB or AUTHORED data.
