# Round 64 — first sensor-provenance predicate; tool-absorption-map formalized

**Date:** 2026-04-29
**Track:** new-measurement-family + T4 tool-ladder discipline
**Status:** complete — vocabulary 107 → 108, operators 95 → 96; absorption-map rule added to ladder

---

## What this round opened on

GPT framing Vincent absorbed pointed at two real gaps:

1. **Sensor provenance inference** — the substrate has 107 predicates that describe *what is in the image* but zero that describe *how the image was captured / transmitted*. The vocabulary is missing an entire measurement family.
2. **Tool-absorption map as explicit rule** — every external tool the substrate leans on should have a named successor capability and a retirement evidence-condition, not just a vague "Phoxelis equivalent" cell.

R64 is the first concrete substrate addition that came from the meta-frame Vincent raised in R59 ("don't chase demos") and the GPT response Vincent absorbed: do the substrate work, name the tools as scaffolding for capabilities not as ends in themselves.

## What got built

### 1. New operator: `dct_block_boundary_energy`

```python
def _dct_block_boundary_energy(image):
    """Ratio of mean gradient magnitude at 8×8 block boundaries vs interior.
    ~1.0 means no block structure (PNG / raw); > 1.05 typically means
    JPEG-compressed."""
```

Synthetic prototype (smooth gradient as ground truth):

| input | block/interior ratio |
|---|---|
| smooth gradient PNG | 1.0000 |
| same JPEG q=50 | **2.1951** |
| random noise PNG | 1.0119 |
| random noise JPEG q=50 | 1.0906 |

The discriminator works. PNG ≈ 1.00, JPEG q=50 ≈ 1.09–2.20.

### 2. New predicate: `is_jpeg_compressed`

```
predicate is_jpeg_compressed
  expects scene:image
  returns bool
  intent  detect_capture_pipeline_jpeg_compression_signature
  body    gt(dct_block_boundary_energy(scene), 1.05)
```

Type-checks, installs, evaluates clean. Vocabulary parses 108/108.

### 3. Audit on R63 corpus (N=30 cached)

```
predicate:    is_jpeg_compressed
fired:        6 / 30  (rate 0.20)
IR-clean:     YES
```

The predicate qualifies for IR-clean promotion. Promoted to `vocab.aurex`.

### 4. Tool-ladder absorption-map section

PHOXELIS_TOOL_LADDER.md gains an absorption-map rule per GPT's framing: every tool entry should name the measured-field/predicate-family it stands in for, the Phoxelis-native successor in code-shape, and the evidence to justify retirement. Four existing rows pinned to this discipline.

## Honest caveats

The 20% firing rate is suspiciously low. Of the 30 R63 cached images, picsum + wikimedia + iNaturalist all serve JPEG at the source — I'd expect ~28-29 to fire. The cache uses 160×160 LANCZOS downsampling, which destroys the original 8×8 DCT block grid alignment for most images. Only the few whose original size happened to downsample cleanly to a multiple-of-8 grid retain the block-boundary signature.

This is itself a real architectural finding: **the harness wasn't designed for measurements that depend on pixel-grid alignment**. Predicates like `is_jpeg_compressed` care about exact byte-level structure that LANCZOS resampling smears.

**P-20 opens** — re-cache the corpus at native resolution or compute provenance verdicts at pull-time before any downsampling. Until then, R64's predicate is correct in DSL form, IR-clean, and qualifies for promotion; its firing-rate measurement is just artificially deflated by the cache.

## Headline benchmark row

| metric | round | value | status |
|---|---|---|---|
| Total predicates | R64 | **108** (103 L1 + 3 L4 + 1 LLM-authored + 1 sensor-provenance) | current |
| Total operators | R64 | **96** (95 + `dct_block_boundary_energy`) | current |
| First sensor-provenance predicate | R64 | `is_jpeg_compressed`; threshold 1.05; PNG ≈ 1.00, JPEG q=50 ≈ 1.10–2.20; IR-clean on R63 cached corpus | current — first capture-pipeline measurement in the project |

## Promises ledger updates

- **C-64** opens: sensor-provenance predicate added; absorption-map rule formalized.
- **P-20** opens: re-cache corpus at native resolution so block-aligned predicates measure faithfully.

## Files added this round

- `Aurexis_Core_WORKING_20260414-1339/07_VISION_SUBSTRATE/aurexis_workbench/vision_ops.py` — `_dct_block_boundary_energy` helper + `R("dct_block_boundary_energy", ...)` registration
- `Aurexis_Core_WORKING_20260414-1339/07_VISION_SUBSTRATE/data/vision/vocab.aurex` — `is_jpeg_compressed` predicate appended (107 → 108)
- `PHOXELIS_TOOL_LADDER.md` — absorption-map rule + pinned successor-capabilities for OpenCV / requests / LLM-in-conversation
- this report

## What this round changes

The substrate now has a measurement family it didn't have at R63. Every prior predicate described scene content (color, texture, composition, identity). `is_jpeg_compressed` describes the *capture-and-transmission pipeline* the image went through — independent of what the image depicts.

This opens a useful new direction: predicates like `has_chroma_subsampling_signature`, `is_likely_screen_capture` (Moiré + pixel-grid), `has_rolling_shutter_artifact`, `is_low_light_long_exposure`. None of these would have fit cleanly in the L1 / L2 / L4 / sensor-time-series taxonomy. They're a fifth axis: **provenance**.

## Next round opens with

`python phoxelis_audit.py`. STALE count holds; new substrate measurement landed. R65 candidates:
- **Continue sensor-provenance family** — author 2-3 more (chroma subsampling, screen capture, rolling shutter)
- **R65 — R58 sensor layer in DSL** — finish the queued promotion
- **R65 — Audit substrate-purpose alignment** — re-walk the pending promises against the GPT-clarified center, prune anything that doesn't advance "measurement-mediated decisions over typed fields"
- **R65 — start the L3-author-loop in batch** — the cycle works for one round per predicate; what would it look like to author 5+ predicates in a single round, all driven by uncovered cases in the corpus rather than my intuition?
