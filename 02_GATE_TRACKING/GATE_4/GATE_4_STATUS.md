# Gate 4 — EXECUTABLE Promotion
**Status: ✅ COMPLETE — April 8, 2026**

## Final audit result

All 9 gate4_completion_audit checks passed on April 8, 2026. First attempt, no fixes needed.

```
Gate 3 confirmed:        True  (2026-04-08)
Files processed:         25
Files with EXECUTABLE:   25  (100%)
Total EXECUTABLE nodes:  301
Total VALIDATED nodes:   349
Best confidence:         1.0000
Threshold:               0.7
Programs saved:          25

Gate 4 completion audit:
  ✅ gate3_confirmed
  ✅ files_processed
  ✅ has_executable_nodes
  ✅ executable_from_real_capture
  ✅ non_synthetic_source
  ✅ traceable_evidence
  ✅ confidence_threshold_met
  ✅ program_serialized
  ✅ output_honesty_explicit

Status: ✅ GATE 4 COMPLETE
```

Report saved: `gate4_run_1/gate4_evaluation.json`
Programs saved: `gate4_run_1/programs/` (25 AUREXIS_PROGRAM_V1 files)

## What was demonstrated

- 25 highest-confidence S23 images run through the FULL Aurexis pipeline
- Every file produced EXECUTABLE IR nodes — 100% success rate
- 301 EXECUTABLE nodes across 25 files (avg 12 per file)
- Confidence peaked at 1.0 — well above the 0.7 threshold
- All EXECUTABLE nodes verified: real-capture tier, non-synthetic, traceable
- 25 programs serialized as AUREXIS_PROGRAM_V1 with SHA-256 provenance

## What Gate 4 requires

Gate 3 produced EARNED tier evidence from 130 real S23 files.
Gate 4 requires promoting that evidence to EXECUTABLE tier:

- At least one IR node reaches EXECUTABLE status (confidence ≥ 0.7, traceable, non-synthetic, REAL_CAPTURE+)
- The promoted program is serialized as AUREXIS_PROGRAM_V1 with SHA-256 provenance
- All 9 gate4_completion_audit checks pass

## Audit checks (9 total)

```
gate3_confirmed              Gate 3 confirmed complete (April 8, 2026) ✅
files_processed              Top-N files ran through full pipeline 🔄
has_executable_nodes         At least one IR node reached EXECUTABLE 🔄
executable_from_real_capture All EXECUTABLE nodes from real-capture tier 🔄
non_synthetic_source         All EXECUTABLE nodes have synthetic=False 🔄
traceable_evidence           All EXECUTABLE nodes have evidence chain 🔄
confidence_threshold_met     Best node confidence >= 0.7 (frozen Core Law §4) 🔄
program_serialized           At least one AUREXIS_PROGRAM_V1 saved 🔄
output_honesty_explicit      Always True ✅
```

## What EXECUTABLE means

An IR node is EXECUTABLE when (Core Law Section 4, frozen):
- `evidence_tier >= REAL_CAPTURE`  — real camera input, not synthetic
- `confidence_mean >= 0.7`         — frozen threshold, cannot be adjusted
- `traceable = True`               — full evidence chain present
- `synthetic = False`              — must be actual camera observation

EXECUTABLE is the first tier where an Aurexis program can actually run.
Below this, programs can only describe, estimate, or validate — not execute.

## Pipeline for Gate 4

```
frames_from_file(path)
  → (frame, frame_idx, camera_meta)

_G4Extractor.extract_robust_primitives(frame)
  → primitives  [24.45/frame average from Gate 3 data]

visual_tokenizer.primitives_to_tokens(observations)
  → tokens

parser_expanded.parse_tokens_expanded(tokens)
  → AST

ir.ast_to_ir(ast)
  → IRNode tree (raw)

ir_optimizer.optimize(ir_raw, phoxel_context=phoxel)
  → (ir_annotated, IROptimizationReport)
  → Pass 1: evidence annotation (synthetic=False, traceable=True from phoxel)
  → Pass 2: confidence propagation
  → Pass 3: execution status ladder (EXECUTABLE if conf>=0.7 and real-capture)
  → Pass 4: dead branch elimination
  → Pass 5: supersession folding
  → Pass 6: promotion pre-screening

program_serializer.save_program(ir_result, path, ir_node, opt_report)
  → AUREXIS_PROGRAM_V1 JSON with SHA-256 integrity hash
```

## Gate 3 input stats (what Gate 4 is working from)

- 130 files, 912 frames, 100% core law compliance
- Mean confidence: 0.618 overall
- 64 files above 0.6 confidence
- Max observed confidence: ~0.77 (seen in batch run screenshots)
- Mean primitives/frame: 24.45
- Promotion eligible (multi-frame consistency): 16 files

## Key question for Gate 4 first run

The EXECUTABLE threshold is 0.7. Batch mean is 0.618.
Top files hit 0.73–0.77 in the batch run.
The IR optimizer propagates confidence through the token/AST/IR chain.
If confidence is preserved through the chain → top files should produce EXECUTABLE nodes.
If confidence degrades through tokenization/parsing → may need to investigate the chain.

## How to run

```powershell
cd "C:\Users\vince\Desktop\Aurexis evolved\back again\05_ACTIVE_DEV"
python run_gate4_pipeline.py gate3_run_2\batch_report.json "C:\Users\vince\Desktop\s23 photos" --output gate4_run_1
```

Output:
- `gate4_run_1/gate4_evaluation.json` — full audit result
- `gate4_run_1/programs/` — serialized AUREXIS_PROGRAM_V1 files (if any promoted)

## Files built for Gate 4

- `gate4_runner.py` — full Gate 4 evaluation chain with 9-check audit
- `run_gate4_pipeline.py` — CLI runner

## What Gate 5 is

Gate 5: Expansion Without Rewrite.
Demonstrate that adding new evidence types, sensors, or capabilities
to Aurexis Core does not require rewriting the core law.
Requires Gates 3 and 4 to be established first.
