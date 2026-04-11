# 05_ACTIVE_DEV — How to use these files

## What's in here

These are new modules to add to your V86 codebase. They implement the camera bridge
and batch pipeline that were previously stubs or missing entirely.

---

## Files built

### `aurexis_lang/src/aurexis_lang/camera_bridge.py`
**Replaces:** `camera_bridge_stub.py`

The real file-based camera bridge. Does:
- Reads JPEG, PNG, DNG, HEIC, MP4, MOV, and other formats from disk
- Parses EXIF metadata from Samsung S23 (and any other phone) images
- Infers which Samsung lens was used based on focal length
- Constructs canonical phoxel records from real camera metadata
- Stamps every frame as REAL_CAPTURE tier (never synthetic, never lab)
- Passes phoxel schema validation before returning

### `aurexis_lang/src/aurexis_lang/file_ingestion_pipeline.py`
**New module.** The concurrent batch processor. Does:
- Discovers all images and videos in a folder (recursively)
- Processes all files concurrently (default 4 workers, configurable)
- Runs each frame through RobustCVExtractor → core law enforcement → phoxel stamping
- Collects: primitive counts, confidence scores, schema error rates, core law compliance rates
- Runs multi-frame consistency validator on videos and multi-image files
- Runs Gate 3 evidence loop evaluation against real results
- Generates batch_report.json + batch_summary.txt in the output folder

### `run_real_capture_pipeline.py`
**Standalone runner.** The script you actually run. Usage:
```bash
python run_real_capture_pipeline.py /path/to/samsung/photos
python run_real_capture_pipeline.py /path/to/samsung/photos --workers 6 --output results/run1
```

### `tests/test_camera_bridge.py`
Tests for the camera bridge covering:
- EXIF rational parsing
- Samsung S23 lens inference from focal length
- Camera metadata construction
- Phoxel record schema validity
- Evidence tier integrity (never LAB or AUTHORED from real files)
- Extension routing

### `requirements.txt`
Updated to add `Pillow>=10.0` (used for richer EXIF parsing when available,
falls back to the built-in JPEG parser if not installed).

---

## How to add to V86

1. Copy `aurexis_lang/src/aurexis_lang/camera_bridge.py` into the V86 source tree
   at the same path: `aurexis_lang/src/aurexis_lang/`
2. Copy `aurexis_lang/src/aurexis_lang/file_ingestion_pipeline.py` to the same location
3. Copy `run_real_capture_pipeline.py` to the root of the V86 project
4. Copy `tests/test_camera_bridge.py` into the V86 `tests/` folder
5. Update V86's `requirements.txt` to add `Pillow>=10.0`
6. Install: `pip install Pillow` (or `pip install Pillow --break-system-packages`)

---

## How to use it — first real run

1. Transfer photos/videos from your Samsung S23 to a folder on your desktop
   (USB cable, or just copy from wherever they landed when you plugged in)
2. From the V86 project root, run:
   ```bash
   python run_real_capture_pipeline.py ~/Desktop/samsung_photos
   ```
3. Watch the output — each file gets processed and metrics print as they complete
4. When done, check `real_capture_pipeline_results/batch_summary.txt` for the plain-text report
5. Check `real_capture_pipeline_results/batch_report.json` for the full JSON report
   including the Gate 3 evaluation result

## What a successful first run looks like

You'll see something like:
```
============================================================
AUREXIS REAL CAPTURE PIPELINE
============================================================
Input:   /home/you/Desktop/samsung_photos
Images:  47
Videos:  8
Workers: 4
============================================================

  [  1/55] IMG_20260407_143022.jpg    frames=  1  conf=0.71  law=100%  [ok]
  [  2/55] VID_20260407_143155.mp4    frames= 42  conf=0.63  law= 97%  [ok]
  ...

BATCH COMPLETE
  Files processed:     55
  Total frames:        312
  Core law rate:       94.2%
  Schema valid frames: 298
  Promotion eligible:  6 files
  Gate 3 status:       False   ← expected until Gate 2 is also complete
  Total time:          23.4s
```

The Gate 3 status will be False initially because Gate 2 is not yet claimed complete.
But the REAL_CAPTURE tier evidence is now in the system. That's the unlock.

---

## What this enables

- First REAL_CAPTURE tier evidence in the pipeline
- Samsung S23 device profile recorded automatically from EXIF
- Multi-frame consistency tested against real video frames
- Gate 3 evidence loop can run against real data
- Device-specific performance profile generated (useful for Gate 4)
- Online phone photos (GSMArena samples etc.) also work the same way —
  just drop them in the same folder

---

## Additional files (added post-V86 coding session)

### `aurexis_lang/src/aurexis_lang/ir.py`
**Replaces:** the 7-line stub.
Full IRNode dataclass with `metadata` dict for optimization state.
Richer `ast_to_ir()` that extracts confidence from every node type
(Assignment, BinaryExpression, TokenStream, TokenExpression).

### `aurexis_lang/src/aurexis_lang/ir_optimizer.py`
**New module.** 6-pass evidence-aware IR optimizer:
1. Evidence annotation — stamps every node with phoxel provenance
2. Confidence propagation — bubbles min/mean confidence bottom-up
3. Execution status ladder — DESCRIPTIVE/ESTIMATED/VALIDATED/EXECUTABLE
4. Dead branch elimination — prunes zero-evidence leaf nodes
5. Supersession folding — marks overwritten assignment targets
6. Promotion pre-screening — fast O(1) check before expensive checklist

Result: REAL_CAPTURE + confidence ≥ 0.7 → EXECUTABLE tier (live).

### `aurexis_lang/src/aurexis_lang/parser_expanded.py`
**Updated.** Fixes confidence flow through TokenStream fallback path.
Multi-token streams now emit individual TokenExpression nodes so each
carries its own confidence into the optimizer, rather than all being
collapsed into one node with confidence=0.

### `aurexis_lang/src/aurexis_lang/program_serializer.py`
**New module.** Save/load Aurexis programs as JSON with full provenance:
- `save_program()` — writes AUREXIS_PROGRAM_V1 JSON with SHA-256 integrity hash
- `load_program()` — loads and verifies hash, reconstructs IRNode tree
- `summarize_program()` — compact summary for batch reports and Gate inputs
- `save_batch_programs()` — batch-save a list of file_to_ir results

Security properties:
- SHA-256 hash covers: source_file, frame_index, evidence_tier, evidence_chain,
  pixel_coordinates, processing_timestamp
- Tampering (e.g. forging tier upgrade) detected on load
- `expected_min_tier` parameter enforces tier floor on load
  (blocks loading LAB-tier programs as REAL_CAPTURE)

### How to copy these new files into V86

In addition to the camera_bridge.py and file_ingestion_pipeline.py steps above:
```
cp 05_ACTIVE_DEV/aurexis_lang/src/aurexis_lang/ir.py             <v86>/aurexis_lang/src/aurexis_lang/
cp 05_ACTIVE_DEV/aurexis_lang/src/aurexis_lang/ir_optimizer.py   <v86>/aurexis_lang/src/aurexis_lang/
cp 05_ACTIVE_DEV/aurexis_lang/src/aurexis_lang/parser_expanded.py <v86>/aurexis_lang/src/aurexis_lang/
cp 05_ACTIVE_DEV/aurexis_lang/src/aurexis_lang/program_serializer.py <v86>/aurexis_lang/src/aurexis_lang/
```
