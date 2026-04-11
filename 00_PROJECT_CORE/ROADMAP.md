# AUREXIS CORE — Post-Foundation Roadmap
**Owner:** Vincent Anderson
**Created:** April 8, 2026
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
