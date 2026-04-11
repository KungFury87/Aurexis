# AUREXIS CORE — M0 BASELINE REALITY MAP

Version: 1.0
Date: April 9, 2026
Purpose: Honest assessment of the current codebase without relying on README prose or aspirational text.

---

## 1) SUBSYSTEM MAP

### Parser/Tokenizer (6 modules) — LIVE, DETERMINISTIC
| Module | Status | Deterministic | Function |
|--------|--------|---------------|----------|
| token_kinds.py | LIVE | Yes | Token type constants |
| parser_stub.py | LIVE | Yes | Basic token→AST wrapper |
| parser_expanded.py | LIVE | Yes | Enhanced parser with confidence threading |
| parser_syntax_expanded.py | LIVE | Yes | Structured statement parsing with blocks |
| parser_scope_control.py | LIVE | Yes | Block-aware parsing with control flow scoping |
| visual_tokenizer.py | LIVE | Yes | CV observations → language tokens with confidence |

### IR/Optimization (5 modules) — LIVE, MOSTLY DETERMINISTIC
| Module | Status | Deterministic | Function |
|--------|--------|---------------|----------|
| ir.py | LIVE | Yes | Core IR node structure, AST→IR conversion |
| ir_expanded.py | LIVE | Yes | Expanded IR with operation mapping |
| ir_optimizer.py | LIVE | **Heuristic** | 6-pass evidence-aware optimizer (confidence 0.7 threshold) |
| program_graph.py | LIVE | Yes | AST→directed graph |
| program_serializer.py | LIVE | Yes | JSON save/load with SHA-256 integrity hash |

### Runtime/Execution (12 modules) — MIXED STATUS
| Module | Status | Deterministic | Function |
|--------|--------|---------------|----------|
| runtime_stub.py | **DEAD** | — | Superseded minimal stub |
| runtime_expanded.py | **DEAD** | — | Superseded one-line wrapper |
| runtime_syntax_expanded.py | **DEAD** | — | Empty syntax evaluation |
| runtime_control.py | LIVE | Yes | Graph-based control evaluation |
| runtime_semantics_stub.py | **SCAFFOLD** | Yes | Basic semantic classification placeholder |
| runtime_semantics_expanded.py | PARTIAL | Yes | Semantic annotation with resolvability flags |
| execution_semantics.py | PARTIAL | **Heuristic** | AST→execution plan with phoxel status |
| execution_semantics_deeper.py | PARTIAL | **Heuristic** | Binary expression evaluation with type coercion |
| execution_interpretation.py | LIVE | Yes | Interprets execution results into outcome states |
| execution_resolution.py | LIVE | Yes | Operand resolution + binary ops |
| execution_trace.py | PARTIAL | Yes | Execution trace with phoxel status rollup |
| execution_state_propagation.py | LIVE | Yes | Environment mutation tracking |

### CV/Perception (14 modules) — LIVE, ALL HEURISTIC
| Module | Status | Deterministic | Function |
|--------|--------|---------------|----------|
| cv_primitive_extractor.py | LIVE | **Heuristic** | Region-based CV primitive extraction |
| camera_primitive_extractor.py | LIVE | Yes | JSON zone manifest → primitives |
| image_primitive_extractor.py | LIVE | **Heuristic** | File-based primitive extraction |
| segmentation_pipeline.py | LIVE | Yes | Coarse partition → segmentation → primitives |
| cv_segmentation_quality.py | LIVE | Yes | Multi-threshold segmentation metrics |
| cv_segmentation_upgrade.py | LIVE | Yes | Connected-component segmentation |
| robust_cv_extractor.py | LIVE | **Heuristic** | Adaptive-threshold real-world extraction |
| advanced_cv_extractor.py | LIVE | **Heuristic** | Multi-technique CV (edge, contour, color, texture) |
| enhanced_cv_extractor.py | LIVE | **Heuristic** | M6 production: multi-scale + ORB + 8-color (100 prim cap) |
| robust_cv_perception.py | LIVE | Yes | Multi-layer CV fusion with disagreement |
| camera_bridge.py | LIVE | **Heuristic** | EXIF parsing + photo/video ingestion |
| camera_bridge_stub.py | **SCAFFOLD** | Yes | Minimal camera placeholder |
| live_camera_feed.py | LIVE | **Heuristic** | Real-time IP Webcam frame producer |
| simulated_camera.py | LIVE | Yes | Synthetic test image generator |

### Evidence/Provenance (6 modules) — LIVE, MOSTLY DETERMINISTIC
| Module | Status | Deterministic | Function |
|--------|--------|---------------|----------|
| evidence_tiers.py | LIVE | Yes | LAB/AUTHORED/REAL_CAPTURE/EARNED tier enum |
| real_evidence_capture.py | LIVE | **Heuristic** | Real-time capture + batch processing |
| evidence_batch_processor.py | PARTIAL | Yes | Batch processing through Gate 3 pipeline |
| phoxel_schema.py | LIVE | Yes | Canonical 6-field phoxel record schema + coercion |
| phoxel_runtime_status.py | LIVE | Yes | Phoxel observation status extraction |
| terminology.py | LIVE | Yes | Legacy phixel↔phoxel alias helpers |

### Law Enforcement (6 modules) — LIVE, 100% DETERMINISTIC, FROZEN
| Module | Status | Deterministic | Function |
|--------|--------|---------------|----------|
| core_law_enforcer.py | LIVE | Yes | Orchestrates all 6 law sections |
| illegal_inference_matrix.py | LIVE | Yes | 9 blocked-claim rules |
| relation_legality.py | LIVE | Yes | PRIMARY + HIGHER_ORDER relation validation |
| executable_promotion.py | LIVE | Yes | 8-point promotion checklist |
| future_tech_ceiling.py | LIVE | Yes | Tech ceiling constraint validation |
| mobile_demo_target.py | LIVE | Yes | Mobile demo evidence validation |

### Gate Audit (20 modules) — MIXED STATUS, ALL DETERMINISTIC
| Module | Status | Function |
|--------|--------|----------|
| gate2_completion_audit.py | LIVE | Gate 2: 11-check runtime obedience |
| gate3_evidence_loop.py | LIVE | Gate 3: earned evidence loop (6 blocking reasons) |
| gate3_completion_audit.py | LIVE | Gate 3: completion audit |
| gate3_runner.py | LIVE | Gate 3: orchestrates full loop |
| gate4_runner.py | LIVE | Gate 4: EXECUTABLE promotion from Gate 3 |
| gate5_runner.py | PARTIAL | Gate 5: cross-device validation (SHA-256 law hash) |
| gate3_batch_comparison.py | PARTIAL | Gate 3 sub-module |
| gate3_batch_reporting.py | PARTIAL | Gate 3 sub-module |
| gate3_comparison_audit.py | PARTIAL | Gate 3 sub-module |
| gate3_earned_promotion.py | PARTIAL | Gate 3 sub-module |
| gate3_gate_completion_audit.py | PARTIAL | Gate 3 sub-module |
| gate3_route_reporting.py | PARTIAL | Gate 3 sub-module |
| gate3_saved_run_audit.py | PARTIAL | Gate 3 sub-module |
| gate3_saved_seed.py | PARTIAL | Gate 3 sub-module |
| gate3_multi_route_completion.py | PARTIAL | Gate 3 sub-module |
| gate3_global_completion.py | PARTIAL | Gate 3 sub-module |
| gate3_packaged_default_state.py | PARTIAL | Gate 3 sub-module |
| gate3_default_pipeline.py | PARTIAL | Gate 3 sub-module |
| gate3_release_pipeline.py | PARTIAL | Gate 3 sub-module |
| gate4_mobile_demo_kickoff.py | PARTIAL | Gate 4 sub-module |

### Pipeline/Demo/Training (15 modules) — MIXED
| Module | Status | Deterministic | Function |
|--------|--------|---------------|----------|
| demo_pipeline.py | LIVE | Yes | Full zone-demo pipeline end-to-end |
| file_ingestion_pipeline.py | LIVE | **Heuristic** | Concurrent batch processor for photos/videos |
| perception_benchmark.py | LIVE | **Heuristic** | Scores perception against configurable profiles |
| perception_inference.py | LIVE | **Heuristic** | Ranks perception rows, detects ambiguity |
| perception_dataset_prep.py | LIVE | Yes | Loads/ranks perception rows, train/val/test splits |
| perception_dataset_export.py | LIVE | Yes | Exports image dataset as perception rows |
| training_loop_scaffold.py | **SCAFFOLD** | — | Training loop stub (no actual ML) |
| evaluation_loop_scaffold.py | **SCAFFOLD** | — | Evaluation loop stub |
| branch_state_execution.py | LIVE | Yes | Collects branch states + environment snapshots |
| control_flow_state_machine.py | LIVE | Yes | State machine + transition tracking |
| control_resolution.py | LIVE | Yes | if/while/for resolution + path labeling |
| confidence_parser.py | LIVE | Yes | Token confidence summary (min/avg/max) |
| ambiguity.py | LIVE | Yes | Candidate interpretation ranking |
| learned_candidate_model.py | LIVE | **Heuristic** | Feature vector scoring into tiers |
| multi_frame_consistency.py | LIVE | **Heuristic** | Cross-frame consistency validation |

### Utility (3 modules)
| Module | Status | Deterministic | Function |
|--------|--------|---------------|----------|
| runtime_obedience.py | PARTIAL | Yes | Gate 2 obedience helpers |
| runtime_reporting.py | LIVE | Yes | Gate 2 metadata stamping |
| cross_device_validator.py | PARTIAL | **Heuristic** | Gate 5 cross-device agreement scoring |

---

## 2) AGGREGATE STATUS

| Classification | Count |
|---------------|-------|
| LIVE | ~55 modules |
| PARTIAL | ~13 modules |
| SCAFFOLD | ~5 modules |
| DEAD | ~3 modules |
| **Total** | **~88 modules** (including __init__.py) |

| Behavior | Count |
|----------|-------|
| Deterministic | ~55 modules |
| Heuristic | ~15 modules |
| Mixed (deterministic logic + heuristic scoring) | ~5 modules |
| Scaffold/Dead (no meaningful behavior) | ~13 modules |

---

## 3) TEST INVENTORY

| Test file | Tests | Coverage |
|-----------|-------|----------|
| test_camera_bridge.py | 37 | Camera bridge, EXIF, metadata, phoxel records |
| test_end_to_end_pipeline.py | 24 | Full pipeline: CV → tokens → AST → IR → optimize → serialize |
| test_gate_reverification.py | 20 | All 5 gates re-verified |
| test_live_camera_pipeline.py | 26 | Live frame source/processor/pipeline |
| test_regression_bugs.py | 9 | Conf=0.00, video softlock, baseline mismatch |
| **Total** | **116 tests** | All passing |

**Coverage gaps:** Law enforcement modules (core_law_enforcer, illegal_inference_matrix, relation_legality, executable_promotion) have no dedicated unit tests — they are exercised indirectly through pipeline and gate tests.

---

## 4) CURRENT PROOF INVENTORY

| Proof | Status | Notes |
|-------|--------|-------|
| 116 pytest tests | Verified | All passing |
| Gate 1 (Core Law Frozen) | Verified | Law at V20, all 7 sections |
| Gate 2 (Runtime Obeys Law) | Verified | 11 audit checks |
| Gate 3 (Earned Evidence) | Verified | 130 S23 files, 912 frames, 100% law compliance |
| Gate 4 (EXECUTABLE Promotion) | Verified | 25 files, 301 EXECUTABLE nodes |
| Gate 5 (Expansion Without Rewrite) | Verified | SHA-256 proof, cross-device |
| M6 (CV Extraction Quality) | Verified | 100 prims/frame, 0.807 confidence |
| M7 (Integration Tests) | Verified | 90 tests at time of completion |
| M8 (Real-Time Camera) | Verified | 54 frames, all EXECUTABLE |
| M9 (Mobile Packaging) | Verified | APK on S23 Ultra, 0.172s/frame |
| M10 (Visual GUI) | Verified | 4-component GUI, 7/7 checks |
| M11 (Debugger/Inspector) | Verified | Step-through debugger, 8/8 checks |

---

## 5) GAP ANALYSIS: CURRENT STATE vs CORE DIRECTION

### What exists and is real:
- Perception/evidence/inspection pipeline (the strongest lane)
- Frozen law enforcement (deterministic, non-self-clearing)
- Evidence tier system with provenance tracking
- Mobile feasibility proven on S23 Ultra
- 116-test suite with gate re-verification
- Debugger and visual inspector tools

### What does not exist:
- **Deterministic visual grammar** — no formal visual language spec where visual primitives carry law-governed semantic meaning
- **Image-as-program** — no mechanism for visual artifacts to encode executable meaning under stable rules
- **Formal parse rules tied to visual law** — current parsing tokenizes CV observations but doesn't enforce a visual grammar
- **Deterministic execution of visual programs** — current "execution" is IR optimization with promotion, not true semantic evaluation of visual meaning
- **Versioned standards/dispatch** — Gate 5 has SHA-256 law hashing but no version dispatch or compatibility routing for visual law versions
- **Print/scan resilience** — no testing of visual artifacts surviving physical media cycles
- **Developer-facing substrate** — no clean API surface for external consumers

### Where heuristics substitute for law:
- CV extraction uses confidence scoring (edge density, contrast, color stats) — **temporary scaffolding, not Core law**
- IR optimizer uses 0.7 confidence threshold for EXECUTABLE promotion — **should become law-governed, not magic number**
- Multi-frame consistency uses spatial tolerance (50px) and confidence tolerance (0.2) — **provisional, not deterministic law**
- Perception inference uses ambiguity delta (0.12) — **heuristic, honest but not Core law**

### Dead code to clean:
- runtime_stub.py (superseded)
- runtime_expanded.py (superseded)
- runtime_syntax_expanded.py (empty)
- camera_bridge_stub.py (superseded by camera_bridge.py)

---

## 6) HONEST VERDICT

**Current milestone position:** The project has completed the perception/evidence/inspection lane through what was previously labeled M6-M11. Under the new milestone ladder, the project is at **M0 (Baseline Freeze)** because the transition from "structured observation pipeline" to "deterministic Core law" has not yet begun.

**What the codebase is:** A mature, tested, mobile-proven perception/evidence/inspection subsystem with frozen law enforcement. The architecture is honest and well-structured. The heuristic components are explicitly provisional.

**What the codebase is not:** A deterministic visual computing substrate. There is no formal visual grammar, no image-as-program mechanism, and no law-governed semantic execution of visual meaning.

**Readiness for M1:** The foundation is solid. The parser pipeline, IR structure, law enforcement engine, and evidence system provide the scaffolding onto which deterministic visual semantics can be built. The transition from M0 to M1 requires defining a narrow visual grammar spec and implementing deterministic parse/execute behavior for that spec.

---

## Ownership

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
Sole inventor and owner: Vincent Anderson.
