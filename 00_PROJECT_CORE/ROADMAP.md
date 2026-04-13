# AUREXIS CORE — Post-Foundation Roadmap
**Owner:** Vincent Anderson
**Created:** April 8, 2026
**Updated:** April 13, 2026 — Integration / Release Hardening Branch COMPLETE-ENOUGH (44 bridges)
**Status:** LOCKED — follow this order, do not deviate

---

## Context

Gates 1–5 are all COMPLETE as of April 8, 2026. The foundation is proven:
the law works, the runtime obeys it, real evidence earns its tier, programs
reach EXECUTABLE status, and the architecture extends without breaking.

Everything below is the PRODUCT phase — turning the proven engine into
something people can use.

---

## Milestone order (STRICT — do not skip or reorder)

### Milestone 6: CV Extraction Quality — ✅ COMPLETE
**Completed:** April 9, 2026
**Priority:** FIRST — everything downstream depends on better observations

**What:** Improve the computer vision extraction layer so it finds more
features with higher confidence from real photos.

**Before (RobustCVExtractor V86):**
- 24.45 primitives per frame (hitting 25-cap ceiling)
- 0.618 mean confidence
- Single-scale extraction, 4 color classes

**After (EnhancedCVExtractor M6):**
- 100.0 primitives per frame (+309%)
- 0.807 mean confidence (+31%)
- Multi-scale extraction (0.5x + 1.0x)
- ORB keypoint detection (up to 200 keypoints)
- 8 color classes (added orange, cyan, purple, red_secondary)
- Improved confidence formula (circularity + log area)
- 100% Core Law compliance maintained

**Audit:** 5/5 checks passed (primitives_improved, confidence_improved,
core_law_maintained, schema_maintained, no_regression).
Gate 3 re-confirmed, Gate 4 re-confirmed (14/14 EXECUTABLE, 1281 nodes).

---

### Milestone 7: End-to-End Integration Tests — ✅ COMPLETE
**Completed:** April 9, 2026
**Priority:** SECOND — lock in quality before building on top

**What:** Comprehensive test suite covering the entire pipeline.

**Result: 90 tests, all passing, 0.67 seconds.**

**Test files created:**
- `tests/conftest.py` — shared fixtures (synthetic frames, mock EXIF, temp dirs)
- `tests/test_camera_bridge.py` — 37 tests (EXIF, metadata, phoxel records, routing)
- `tests/test_end_to_end_pipeline.py` — 24 tests (CV extraction → tokens → AST →
  IR → optimization → serialization → batch pipeline)
- `tests/test_regression_bugs.py` — 9 tests (conf=0.00, video softlock, baseline mismatch)
- `tests/test_gate_reverification.py` — 20 tests (all 5 gates re-verified)
- `pytest.ini` — config for `py -m pytest tests/ -v`

**Coverage:**
- Full pipeline: image → EXIF → phoxel → CV → tokens → AST → IR → optimize → serialize
- 3 regression guards for bugs fixed during Gate 3 push
- All 5 foundation gates re-verified via automated tests
- Evidence tier integrity (AUTHORED never escalated, threshold = 0.7)
- Synthetic test data (no real photos required to run tests)

---

### Milestone 8: Real-Time Camera Integration — ✅ COMPLETE
**Completed:** April 9, 2026
**Priority:** THIRD — bridge from file-based to live processing

**What:** Process camera frames in real-time instead of requiring file
transfer from phone to desktop.

**Before:**
- File-based ingestion only (transfer photos via USB/cloud, then run script)
- Camera bridge supports JPEG/PNG/DNG/MP4/MOV from disk
- No live camera feed support

**After (LivePipeline M8):**
- Live camera feed from Samsung S23 via IP Webcam over WiFi
- 54 frames processed in 60 seconds (0.90 effective FPS)
- All 54 frames reached EXECUTABLE status
- 54 programs saved to disk
- 100% Core Law compliance maintained
- All frames within tech floor (max 2.193s/frame, well under 30s limit)
- 100 primitives/frame, 0.609 mean confidence
- Graceful degradation working: 60 frames dropped without stalling

**Architecture:**
- `LiveFrameSource`: Background thread frame grabber (snapshot + stream modes)
- `LiveFrameProcessor`: Full pipeline per frame (CV → phoxel → law → AST → IR)
- `LivePipeline`: Orchestrator with bounded queue (size=5, drop-oldest)
- `run_live_pipeline.py`: CLI runner with configurable URL, duration, FPS, mode

**Audit:** 5/5 checks passed (frames_processed, executable_reached,
law_compliance_100, within_tech_floor, live_source_confirmed).

---

### Milestone 9: Mobile Packaging — ✅ COMPLETE
**Completed:** April 9, 2026
**Priority:** FOURTH — get it running on a phone

**What:** Package Aurexis Core to run on mobile hardware within the
tech floor constraints defined in Core Law Section 6.

**Before:**
- Pure Python codebase (~88 files)
- Depends on OpenCV 4.5.1, NumPy 1.22.3, Pillow 8.4.0
- Runs on desktop only
- Processing time: ~1.1s per frame on desktop (M8)

**After (Kivy APK on Samsung S23 Ultra):**
- Full Android APK (36MB) built with Buildozer + Kivy
- Python 3.11.5 running natively on ARM64 (arm64-v8a)
- 30 frames processed at 0.98 effective FPS
- 82 prims/frame, 0.529 mean confidence
- 0.172s mean processing time (max 0.262s) — 175x under 30s tech floor
- 29/30 frames reached EXECUTABLE status
- 29 programs saved to on-device storage
- 100% Core Law compliance
- All frames within tech floor constraints

**Architecture:**
- `mobile_app/main.py`: Kivy app with camera preview, START/STOP, live log, M9 audit
- `mobile_app/mobile_pipeline.py`: Kivy texture → BGR adapter + MobilePipeline orchestrator
- `mobile_app/buildozer.spec`: Build config (arm64-v8a, API 33, opencv+numpy+pillow)
- Build via WSL + Buildozer, deployed as sideloaded debug APK

**Audit:** 5/5 checks passed (on_device, frames_processed,
executable_reached, law_compliance_100, within_tech_floor).

---

### Milestone 10: Visual Programming GUI — ✅ COMPLETE
**Completed:** April 9, 2026
**Priority:** FIFTH — the user interface layer

**What:** A visual interface where users can see what Aurexis Core
observes, what it promoted, and interact with programs.

**Before:**
- All interaction was command-line only
- No visualization of phoxel fields or IR trees
- No way to inspect evidence chains or promotions

**After (Tabbed Kivy GUI on S23 Ultra):**
- Tab 1 — Live Feed: Camera with real-time phoxel overlay (bounding boxes, labels, confidence scores drawn on frame)
- Tab 2 — IR Tree: Color-coded program structure (green=EXECUTABLE, yellow=VALIDATED, gray=DESCRIPTIVE)
- Tab 3 — Evidence Inspector: Tap any frame to see full evidence chain, source, tier, validation status
- Tab 4 — Promotion Tracker: Live dashboard with execution status ladder, confidence trend, per-frame timeline
- 30 frames at 0.98 FPS, 90.4 prims/frame, 0.489 confidence
- 0.160s/frame (max 0.326s), 100% law compliance, all 30 EXECUTABLE
- Touch-friendly on mobile, all four visual components operational

**Architecture:**
- `visual_gui.py`: PhoxelOverlay, IRTreeWidget, EvidenceInspector, PromotionTracker
- `main.py`: Kivy app integrating all four components (TabbedPanel → ScreenManager in M11)
- OpenCV-based annotation pipeline (bounding boxes, labels, confidence bars)

**Audit:** 7/7 checks passed (phoxel_overlay, ir_tree_rendered,
evidence_inspector, promotion_tracker, frames_processed,
executable_reached, within_tech_floor).

---

### Milestone 11: Debugger and Inspector Tools — ✅ COMPLETE
**Completed:** April 9, 2026
**Priority:** SIXTH — development tools for the language

**What:** Tools for developers (starting with Vincent) to step through
Aurexis programs, inspect state, and diagnose issues.

**Before:**
- No debugger
- Diagnosis was done by reading JSON reports and batch_report.json
- No way to step through an IR tree node by node

**After (Debugger + Inspector on S23 Ultra):**
- Step-through IR debugger with Step Into / Step Over / Step Out / Run to Breakpoint
- Preset breakpoints: EXEC status, VALID status, Confidence < 0.5
- Core Law violation inspector (checks Sections 4 and 7 per node)
- 101 nodes loaded from live IR tree, fully traversable
- Export debugger session as reproducible report
- 5-screen ScreenManager UI replacing TabbedPanel (mobile-friendly bottom nav)
- Deferred permission model (no crash on first launch)
- 29 frames at 0.97 FPS, 89 prims/frame, 0.487 confidence
- 0.172s/frame (max 0.301s), 100% law compliance, all 29 EXECUTABLE

**Architecture:**
- `debugger.py`: DebugStep, Breakpoint, LawInspector, IRDebugger, DebuggerWidget
- `main.py`: ScreenManager with 5 screens + bottom nav (v0.9.1, renamed lifecycle methods)
- Bug fixes: `on_start` → `_start_pipeline` (Kivy lifecycle collision), deferred Camera creation

**Audit:** 8/8 checks passed (phoxel_overlay, ir_tree_rendered,
evidence_inspector, promotion_tracker, debugger_loaded, frames_processed,
executable_reached, within_tech_floor).

---

## V1 Substrate Bridge Ladder (Post-M11)

After M11, the project entered the V1 Substrate Bridge phase — proving narrow law-bearing properties through a strict sequence of deterministic bridge milestones. Each bridge adds one specific capability to the substrate stack.

| # | Bridge | Status | Assertions |
|---|--------|--------|------------|
| 1 | Raster Law Bridge V1 | ✅ COMPLETE | 58 |
| 2 | Capture Tolerance Bridge V1 | ✅ COMPLETE | 99 |
| 3 | Artifact Localization Bridge V1 | ✅ COMPLETE | 54 |
| 4 | Orientation Normalization Bridge V1 | ✅ COMPLETE | 70 |
| 5 | Perspective Normalization Bridge V1 | ✅ COMPLETE | 53 |
| 6 | Composed Recovery Bridge V1 | ✅ COMPLETE | 72 |
| 7 | Artifact Dispatch Bridge V1 | ✅ COMPLETE | 58 |
| 8 | Multi-Artifact Layout Bridge V1 | ✅ COMPLETE | 68 |
| 9 | Artifact Set Contract Bridge V1 | ✅ COMPLETE | 89 |
| 10 | Recovered Set Signature Bridge V1 | ✅ COMPLETE | 86 |
| 11 | Recovered Set Signature Match Bridge V1 | ✅ COMPLETE | 100 |
| 12 | Recovered Page Sequence Contract Bridge V1 | ✅ COMPLETE | 149 |
| 13 | Recovered Page Sequence Signature Bridge V1 | ✅ COMPLETE | 154 |
| 14 | Recovered Page Sequence Signature Match Bridge V1 | ✅ COMPLETE | 141 |
| 15 | Recovered Sequence Collection Contract Bridge V1 | ✅ COMPLETE | 163 |
| 16 | Recovered Sequence Collection Signature Bridge V1 | ✅ COMPLETE | 173 |
| 17 | Recovered Sequence Collection Signature Match Bridge V1 | ✅ COMPLETE | 148 |
| 18 | Recovered Collection Global Consistency Bridge V1 | ✅ COMPLETE | 186 |
| 19 | Rolling Shutter Temporal Transport Bridge V1 | ✅ COMPLETE | 289 |
| 20 | Complementary-Color Temporal Transport Bridge V1 | ✅ COMPLETE | 317 |
| 21 | Temporal Transport Dispatch Bridge V1 | ✅ COMPLETE | 178 |
| 22 | Temporal Consistency Bridge V1 | ✅ COMPLETE | 412 |
| 23 | Frame-Accurate Transport Bridge V1 | ✅ COMPLETE | 350 |
| 24 | Combined RS+CC Temporal Fusion Bridge V1 | ✅ COMPLETE | 250 |
| 25 | Temporal Payload Contract Bridge V1 | ✅ COMPLETE | 133 |
| 26 | Temporal Payload Signature Bridge V1 | ✅ COMPLETE | 99 |
| 27 | Temporal Payload Signature Match Bridge V1 | ✅ COMPLETE | 142 |
| 28 | Temporal Global Consistency Bridge V1 | ✅ COMPLETE | 114 |
| 29 | Overlap Detection Bridge V1 | ✅ COMPLETE | 82 |
| 30 | Local Section Consistency Bridge V1 | ✅ COMPLETE | 62 |
| 31 | Sheaf-Style Composition Bridge V1 | ✅ COMPLETE | 58 |
| 32 | Cohomological Obstruction Detection Bridge V1 | ✅ COMPLETE | 56 |
| 33 | View-Dependent Marker Profile Bridge V1 | ✅ COMPLETE | 95 |
| 34 | Moment-Invariant Identity Bridge V1 | ✅ COMPLETE | 92 |
| 35 | View-Facet Recovery Bridge V1 | ✅ COMPLETE | 179 |
| 36 | View-Dependent Contract Bridge V1 | ✅ COMPLETE | 144 |
| 37 | VSA Cleanup Profile Bridge V1 | ✅ COMPLETE | 64 |
| 38 | Hypervector Binding / Bundling Bridge V1 | ✅ COMPLETE | 55 |
| 39 | Cleanup Retrieval Bridge V1 | ✅ COMPLETE | 100 |
| 40 | VSA Consistency / Contract Bridge V1 | ✅ COMPLETE | 73 |
| 41 | Unified Capability Manifest Bridge V1 | ✅ COMPLETE | 53 |
| 42 | Unified Substrate Entrypoint Bridge V1 | ✅ COMPLETE | 57 |
| 43 | Cross-Branch Compatibility Contract Bridge V1 | ✅ COMPLETE | 36 |
| 44 | V1 Substrate Release Audit Bridge V1 | ✅ COMPLETE | 40 |
| 45 | Real Capture Ingest Profile Bridge V1 | ✅ COMPLETE | 50 |
| 46 | Capture Session Manifest Bridge V1 | ✅ COMPLETE | 42 |
| 47 | Evidence Delta Analysis Bridge V1 | ✅ COMPLETE | 40 |
| 48 | Calibration Recommendation Bridge V1 | ✅ COMPLETE | 33 |

**Total:** 6246 standalone assertions, 58 runners — all passing.

---

## Completed Branch: Higher-Order Coherence / Sheaf-Style Composition

**Status:** BRANCH COMPLETE-ENOUGH — four milestones complete as of April 13, 2026. Capstone verification passed.

**Concept:** Extends the cross-layer consistency checks into a bounded local-to-global coherence framework inspired by sheaf-theoretic ideas. Proves that the frozen collection family overlaps, agrees locally, composes globally, and has no composition obstructions.

**Completed milestones:**

- ✅ Overlap Detection Bridge V1 (29th bridge) — bounded structural overlap detection across collections and sequences. 3 pairwise collection overlaps, 1 sequence overlap, all deterministic. 82 assertions, all passing.
- ✅ Local Section Consistency Bridge V1 (30th bridge) — bounded local-section agreement verification. All 3 overlap regions consistent, 3 fabricated inconsistency types detected. 62 assertions, all passing.
- ✅ Sheaf-Style Composition Bridge V1 (31st bridge) — bounded composition proof. Global assignment of 3 sequences, all 3 collections agree. Fabricated contradictions produce NOT_COMPOSABLE. 58 assertions, all passing.
- ✅ Cohomological Obstruction Detection Bridge V1 (32nd bridge) — bounded obstruction detector. No obstructions in frozen contracts, 3 fabricated obstruction types detected. 56 assertions, all passing.

**Honest framing:** The sheaf analogy is a design inspiration, not a claim of full sheaf-theory generality. This is a bounded executable coherence proof, not a general theorem prover.

---

## Active Branch: Screen-to-Camera Temporal Transport

**Status:** BRANCH COMPLETE-ENOUGH — ten milestones complete as of April 13, 2026. Capstone verification passed.

**Concept:** Extend the static raster bridge to handle temporal transport — the process of capturing a screen-displayed visual program through a physical camera, accounting for temporal artifacts introduced by the capture process.

**Completed milestones:**

- ✅ Rolling Shutter Temporal Transport Bridge V1 (19th bridge) — bounded screen-to-camera stripe transport proof using 1 kHz temporal modulation, CMOS rolling-shutter row-delay exploitation, timing-based slot decoding, and route mapping into existing Aurexis dispatch families. 289 assertions, all passing.
- ✅ Complementary-Color Temporal Transport Bridge V1 (20th bridge) — bounded screen-to-camera complementary-color transport proof using 3 frozen color pairs (cyan/red, magenta/green, yellow/blue), chrominance projection decoding, and route mapping into existing Aurexis dispatch families. 317 assertions, all passing.
- ✅ Temporal Transport Dispatch Bridge V1 (21st bridge) — bounded temporal-mode routing proof. Identifies which of the two frozen transport modes (rolling-shutter or complementary-color) produced a recovered signal via structural fingerprinting, routes to the correct decoder, and feeds the payload into the existing Aurexis dispatch path. 178 assertions, all passing.
- ✅ Temporal Consistency Bridge V1 (22nd bridge) — bounded repeated-capture agreement proof. Repeated synthetic captures of the same bounded temporal payload dispatched through the existing dispatch bridge produce a stable recovered identity (unanimous agreement across 2–10 captures), and inconsistent or drifted capture sets are honestly rejected. 412 assertions, all passing.
- ✅ Frame-Accurate Transport Bridge V1 (23rd bridge) — bounded temporal slot-identity preservation proof. A frozen family of ordered temporal display sequences (2, 3, or 4 slots) can be independently transported, captured, decoded, and the per-slot payload association and ordering deterministically recovered. Drifted or unsupported sequences are honestly rejected. 350 assertions, all passing.
- ✅ Combined RS+CC Temporal Fusion Bridge V1 (24th bridge) — bounded stripe-and-color fusion transport proof. Encoding the same bounded payload through both rolling-shutter stripe transport and complementary-color temporal transport, decoding both channels independently, and checking agreement under a frozen fusion policy produces deterministic fused payload recovery. Supports both-agree, single-channel fallback (permissive profile), fallback-denied (strict profile), disagreement rejection, and both-failed rejection. 250 assertions, all passing.
- ✅ Temporal Payload Contract Bridge V1 (25th bridge) — bounded temporal structure validation proof. Recovered temporal payload structures (from RS, CC, or fused transport) can be validated against an explicit frozen contract specifying allowed payload lengths, payload families, transport modes, and fused-channel requirements. 5 frozen contracts, deterministic accept/reject verdicts. 133 assertions, all passing.
- ✅ Temporal Payload Signature Bridge V1 (26th bridge) — bounded temporal fingerprint proof. Validated recovered temporal payload structures (contract-satisfied) can be reduced to a deterministic SHA-256 signature/fingerprint over canonical structural fields (contract name, payload bits, payload family, transport mode, fused flag, payload length). Identical validated structures produce identical signatures; changed content, family, mode, or contract produce different signatures. Structures that fail contract validation cannot be signed. 99 assertions, all passing.
- ✅ Temporal Payload Signature Match Bridge V1 (27th bridge) — bounded expected-temporal-signature verification proof. Computed temporal payload signatures can be compared against a frozen expected-signature baseline (6 frozen cases) and return deterministic MATCH / MISMATCH / UNSUPPORTED verdicts. Changed payload bits, transport mode, or contract produce honest mismatch or upstream failure. Unsupported cases fail honestly. 142 assertions, all passing.
- ✅ Temporal Global Consistency Bridge V1 (28th bridge) — bounded temporal cross-layer coherence verification proof. Cross-layer consistency checks (match verdict agreement, contract verdict agreement, signature equality, canonical field consistency, payload length consistency, cross-case distinctness) catch locally-valid but globally-contradictory temporal structures. 6 consistent cases, 5 contradictory cases, 1 unsupported case. 114 assertions, all passing.
- ✅ **TEMPORAL BRANCH CAPSTONE** — All 10 temporal milestones verified end-to-end. 2,284 temporal assertions across 10 runners, all passing. Full pipeline proven: generate → encode → capture → decode → dispatch → stabilize → fuse → contract → sign → match → global consistency. See TEMPORAL_BRANCH_CAPSTONE_V1.md.

**Branch status:** COMPLETE-ENOUGH. The bounded temporal transport proof is self-contained and coherent.

**Remaining for later (not in this branch):**
- Advanced temporal/OCC work (broader transport modes, real-world noise, adaptive decoding) — TBD by Vincent
- Any future temporal extensions require a new branch or user decision

**Prerequisite:** Stable static raster substrate. All ten temporal transport milestones are complete and proven.

**Honest framing:** Temporal transport is a harder problem than static raster recovery. The ten completed milestones are narrow deterministic proofs, not full real-world camera robustness or general OCC.

---

## View-Dependent Markers / 3D Moment Invariants — ✅ BRANCH COMPLETE-ENOUGH

**Completed:** April 13, 2026
**Bridges:** 33–36 (4 milestones + branch capstone)
**New assertions:** 510 standalone, 85 pytest functions
**Branch verdict:** COMPLETE-ENOUGH — narrow bounded proof

**What was built:**
- **Bridge 33 — View-Dependent Marker Profile V1:** 4 frozen markers × 4 viewpoint buckets = 16 facets. Stable identity + view-dependent facets. (95 assertions, 20/20 gate)
- **Bridge 34 — Moment-Invariant Identity V1:** Identity hash is viewpoint-invariant by construction. All 4 markers verified stable. (92 assertions, 17/17 gate)
- **Bridge 35 — View-Facet Recovery V1:** Full recovery (identity + viewpoint + facet) from single observation. 16/16 full recoveries. Facets provably vary while identity stays constant. (179 assertions, 17/17 gate)
- **Bridge 36 — View-Dependent Contract V1:** Frozen contract validates recovered identity, viewpoint, and facet hash. 16/16 valid, 4 rejection paths tested. (144 assertions, 18/18 gate)

**Honest limits:** Viewpoint buckets are discrete (4 positions, not continuous). Markers are hand-defined, not discovered from real imagery. Facet matching uses exact hash comparison, not noise-tolerant matching.

---

## VSA / Hyperdimensional Cleanup Layer — ✅ BRANCH COMPLETE-ENOUGH



**Completed:** April 13, 2026
**Bridges:** 37–40 (4 milestones + branch capstone)
**New assertions:** 292 standalone, 59 pytest functions
**Branch verdict:** COMPLETE-ENOUGH — bounded auxiliary helper layer

**What was built:**
- **Bridge 37 — VSA Cleanup Profile V1:** 11 frozen cleanup targets mapping substrate outputs (5 set + 3 sequence + 3 collection contracts) to VSA symbol IDs. (64 assertions, 15/15 gate)
- **Bridge 38 — Hypervector Binding / Bundling V1:** 1024-dimensional bipolar MAP-style operations: atomic generation, binding (self-inverse), bundling (majority vote), permutation (order encoding). (55 assertions, 17/17 gate)
- **Bridge 39 — Cleanup Retrieval V1:** Cosine-similarity nearest-codebook-entry cleanup. All 11 symbols recovered at up to 20% bit-flip noise. (100 assertions, 15/15 gate)
- **Bridge 40 — VSA Consistency / Contract V1:** Cross-check VSA recovery against deterministic substrate truth. 11/11 CONSISTENT at 0% and 10% noise. 3 rejection paths tested. (73 assertions, 15/15 gate)

**Honest limits:** Dimension (1024) is small. Noise model is simple bit-flip. Codebook is only 11 entries. VSA is explicitly AUXILIARY — it compresses/cleans substrate outputs but the deterministic substrate remains the truth layer.

---

## Integration / Release Hardening — ✅ BRANCH COMPLETE-ENOUGH

**Completed:** April 13, 2026
**Bridges:** 41–44 (4 milestones + branch capstone)
**New assertions:** 186 standalone, 4 runners
**Branch verdict:** COMPLETE-ENOUGH — unified V1 substrate candidate release-hardened

**What was built:**
- **Bridge 41 — Unified Capability Manifest V1:** Machine-readable manifest of all 40 bridges, 5 branches, 52 modules. JSON export. Deterministic manifest hash. (53 assertions, 19/19 gate)
- **Bridge 42 — Unified Substrate Entrypoint V1:** Thin orchestrator routing into all branches. 40-bridge registry. 7 routes (5 branch + manifest + compatibility). Dynamic import. (57 assertions, 17/17 gate)
- **Bridge 43 — Cross-Branch Compatibility Contract V1:** 12 structural compatibility rules. Module namespace, bridge numbering, branch ranges, VSA auxiliary precedence, no circular imports. All 12 COMPATIBLE. (36 assertions, 17/17 gate)
- **Bridge 44 — V1 Substrate Release Audit V1:** 10 release-level audit checks. Manifest, entrypoint, compatibility, module imports, route success, hash determinism, foundation, exclusions, version consistency. All 10 PASS. (40 assertions, 16/16 gate)

**Honest limits:** Integration checks are structural (imports, namespaces, routing). Not runtime interoperation under load or production deployment validation.

---

## Observed Evidence Loop / Real Capture Calibration — ✅ BRANCH COMPLETE-ENOUGH

**Completed:** April 13, 2026
**Bridges:** 45–48 (4 milestones + branch capstone)
**New assertions:** 165 standalone, 4 runners
**Branch verdict:** COMPLETE-ENOUGH — bounded real-capture calibration loop

**What was built:**
- **Bridge 45 — Real Capture Ingest Profile V1:** 5 frozen ingest cases (phone JPEG, phone PNG, webcam JPEG, video frame PNG, scanner TIFF). File shape, metadata, and assumption validation. (50 assertions, 17/17 gate)
- **Bridge 46 — Capture Session Manifest V1:** Deterministic session manifests linking capture files, ingest results, device metadata, evidence tiers. SHA-256 manifest hash. (42 assertions, 15/15 gate)
- **Bridge 47 — Evidence Delta Analysis V1:** Structured comparison of expected vs observed substrate outputs. Missing/extra/changed primitives, contract deltas, signature deltas. Bounded tolerances. (40 assertions, 16/16 gate)
- **Bridge 48 — Calibration Recommendation V1:** 7 recommendation rules producing 5 kinds of advisory outputs. All recommendations advisory and subordinate to the deterministic truth layer. (33 assertions, 17/17 gate)

**Honest limits:** No real capture files have been processed yet — the loop infrastructure is proven but requires user-supplied capture datasets to exercise against real data. All recommendations are advisory; none auto-execute. No root-cause analysis or continuous monitoring.

**What still requires user action later:** User-supplied real capture datasets to feed through the loop. Until then, the infrastructure is proven against synthetic/deterministic test cases only.

---

## Explicitly Excluded

The following technologies and approaches are **explicitly excluded** from the V1 substrate roadmap:

- **OAM (Orbital Angular Momentum)** — Exotic optical encoding not relevant to standard camera/screen capture pipelines.
- **Optical Skyrmions** — Topological light structures requiring specialized detection hardware. Outside the scope of standard vision systems.
- **NLOS (Non-Line-of-Sight) Imaging** — Imaging around corners or through scattering media. Interesting but irrelevant to the direct camera-to-screen pipeline.
- **Exotic Specialized Optics** — Any approach requiring non-standard optical hardware (metamaterials, computational optics, holographic elements, etc.). The V1 substrate must work with standard consumer cameras and displays.

**Rationale:** The V1 substrate is grounded in physics-of-light as captured by standard consumer hardware. Exotic optics violate the Current Tech Floor (Gate 6 of the Core Law: must run on current mobile hardware) and would create dependencies on unavailable equipment.

---

## Rules for this roadmap

1. **Do not skip milestones** unless doing so would directly benefit
   later milestones. If skipping, document the reasoning and which
   downstream milestone benefits.
2. **Do not reorder milestones** unless the same exception applies.
3. **Do not modify Core Law.** It's frozen. If something doesn't work
   within the law, the solution must be architectural, not legal.
4. **Each milestone gets a completion audit.** Just like the gates.
   Define the audit checks BEFORE starting the work.
5. **Test before ship.** Milestone 7 exists specifically because
   untested changes caused 3 bugs during the Gate 3 push.
6. **Honest limits only.** If a milestone is blocked, document why.
   Do not fake completion.

---

## Ownership

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
Sole inventor and owner: Vincent Anderson.
