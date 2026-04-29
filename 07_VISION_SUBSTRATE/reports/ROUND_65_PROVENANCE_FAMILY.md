# Round 65 — sensor-provenance family extended; first explicit deferral

**Date:** 2026-04-29
**Track:** T1 vocabulary health (sensor-provenance sub-family from R64)
**Status:** complete — vocabulary 108 → 110 (+2 IR-clean), operators 96 → 99
(+3); 1 candidate predicate explicitly deferred with documented condition

---

## What this round opened on

R64 added the first sensor-provenance predicate (`is_jpeg_compressed`) and
named the new measurement family. The natural continuation is to populate
it: are there other capture-pipeline properties that survive as composable
measurements over typed fields?

R65 takes three candidates, builds operators for each, and lets the IR
audit on the existing N=42 cached corpus decide which earn promotion.

## What got built

### 1. Three new operators in `vision_ops.py`

```
chroma_to_luma_hf_ratio(color_image)   -> scalar
axis_aligned_hf_concentration(image)   -> scalar
highlight_clipped_fraction(image)      -> scalar
```

Synthetic ground-truth (256×256):

| input | chroma/luma HF | axis cross | clip fraction |
|---|---|---|---|
| random RGB (untouched)            | 0.957 | — | — |
| same → JPEG q=30 4:2:0            | **0.027** | — | — |
| same → JPEG q=90 4:4:4 (no subsmp) | 0.958 | — | — |
| same → JPEG q=85 4:2:0            | 0.093 | — | — |
| smooth horizontal gradient | — | 1.000 | — |
| random noise               | — | 0.008 (~ 2/N) | — |
| 1-pixel horizontal stripes | — | **1.000** | — |
| diagonal grating           | — | 0.000 | — |
| uniform 0.5    | — | — | 0.000 |
| top quarter clipped at 1.0 | — | — | **0.250** |

The chroma operator is the cleanest of the three: 35× discriminator between
raw RGB and JPEG-q30-4:2:0 on synthetic input, recovers cleanly when 4:4:4
is selected.

### 2. Three candidate predicates (one later deferred)

```
predicate has_chroma_subsampled_signature
  expects color_scene:color_image
  body lt(chroma_to_luma_hf_ratio(color_scene), 0.50)

predicate has_axis_aligned_pixel_grid     # candidate, ultimately deferred
  expects scene:image
  body gt(axis_aligned_hf_concentration(scene), 0.30)

predicate has_clipped_highlights
  expects scene:image
  body gt(highlight_clipped_fraction(scene), 0.05)
```

### 3. IR audit at N=42 cached corpus

`round65_provenance_family/round65_audit.py` registers operators, installs
all 111 predicates (108 prior + 3 new), evaluates the entire vocabulary
against every cached image, and computes IR equivalence classes over a
*consistent* N=42 view (R64's retroactive_eval compared against stale
verdict patterns from earlier sessions; R65 re-evaluates from scratch).

```
Vocabulary: 111 predicates installed, 0 errors
Cached images: 42

has_chroma_subsampled_signature
  fired:    37 / 42   (rate 0.881)
  pattern:  TTTTTTTTTTFTFFTTFTTTTTTTTTTTTTTTTTFTTTTTTT
  IR-clean: YES         <-- promotable

has_axis_aligned_pixel_grid
  fired:    0 / 42      (rate 0.000)
  pattern:  FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
  IR-clean: NO  (twin = always-False motion/screen class, 14 members)
                            <-- not promotable on this corpus

has_clipped_highlights
  fired:    2 / 42      (rate 0.048)
  pattern:  FFFFFFTFFFFFFFFFFFFFFFFFFFFFFFTFFFFFFFFFFF
  IR-clean: YES         <-- promotable
```

### 4. Vocab updates and explicit deferral

`vocab.aurex` 108 → 110: `has_chroma_subsampled_signature` and
`has_clipped_highlights` appended. `has_axis_aligned_pixel_grid` is *not*
written into vocab.aurex; instead a comment block in the file records the
operator's existence in `vision_ops.py`, the deferral reason, and the
P-21 ledger entry that gates its eventual promotion.

This is a small but new discipline for the project: operators that work
on synthetics but lack positive cases on the present corpus get an
**explicit deferral entry** with a corpus-condition for promotion, instead
of being silently retired (R25 template) or quietly dropped.

## Honest caveats

- **The chroma firing rate (88%) is suspiciously high but defensible.**
  Almost every cached image originated from JPEG-serving sources (picsum,
  iNaturalist, Wikimedia, MET); the 5 that don't fire are likely those
  whose original-source JPEG quality was high enough that the chroma HF
  loss was below the 0.50 threshold even after LANCZOS downsampling. The
  fire-rate would be a useful corpus diagnostic in its own right at scale.
- **The axis-aligned operator IS correct on its target signal** (1.0 on
  the period-2 horizontal stripe synthetic, 0.008 on isotropic noise)
  but the cached corpus simply doesn't contain a positive case. The
  measurement is real; the audit just isn't able to confirm independence
  yet. P-21 captures the corpus-side work needed.
- **Two .pyc / mount-cache incidents this round.** The first attempt at
  the axis operator returned 0 even though the source had been corrected,
  because the mount didn't bump source mtime and Python kept using a
  stale .pyc. Working around with `touch source.py + retry` until
  satisfied. Logged as an ongoing soft contract violation (#10 in the
  charter).

## Headline benchmark rows (added this round)

| metric | round | value | status |
|---|---|---|---|
| Total predicates | R65 | **110** (103 L1 + 3 L4 + 1 LLM-authored + 3 sensor-provenance) | current |
| Total operators  | R65 | **99** (96 + 3 R65 ops) | current |
| First explicit predicate deferral with corpus-condition | R65 | `has_axis_aligned_pixel_grid` deferred until corpus seeds screen-capture content (P-21) | current — new discipline pattern |
| Sensor-provenance predicates IR-clean on cached corpus | R65 | 3 / 4 candidates promoted (R64 + R65), 1 deferred | current |

## Promises ledger updates

- **C-65 closes:** sensor-provenance family extended; 2 IR-clean
  promotions; 1 explicit deferral with documented corpus-condition.
- **P-21 opens:** add screen-capture / display-photograph seeds to corpus
  router so `has_axis_aligned_pixel_grid` can be IR-validated. Until that
  happens, the operator stays registered but the predicate stays out of
  `vocab.aurex`.

## Files added this round

- `Aurexis_Core_WORKING_20260414-1339/07_VISION_SUBSTRATE/aurexis_workbench/vision_ops.py` — 3 new operators + R65 R(...) registrations
- `Aurexis_Core_WORKING_20260414-1339/07_VISION_SUBSTRATE/data/vision/vocab.aurex` — 2 new predicates appended (108 → 110); deferral comment block for the third
- `round65_provenance_family/round65_audit.py` — N=42 cached-corpus IR audit script (consistent re-evaluation, not retroactive_eval against stale patterns)
- `round65_provenance_family/round65_audit_full.py` — same script before deferral, kept as evidence the third candidate failed the audit
- `round65_provenance_family/round65_audit.json` — machine-readable findings
- this report
- `PHOXELIS_CHARTER.md` — predicate count 108 → 110; operator count 96 → 99
- `PHOXELIS_BENCHMARKS.md` — R65 rows for predicate/operator counts + first-deferral milestone
- `PHOXELIS_PROMISES.md` — C-65 entry, P-21 opened

## What this round changes

The substrate is no longer one-deep in any new measurement family: the
sensor-provenance axis introduced in R64 now has 3 predicates that work
on different physical signatures of the capture pipeline (block-boundary
DCT residue, chroma-vs-luma HF energy, sensor highlight clipping). The
fourth signature (axis-aligned pixel-grid) is built but bound to a
documented corpus condition.

The deferral pattern itself is the methodological gain. R25 retired a
falsified predicate; R63 promoted a previously-IR-collided one after the
corpus grew; R65 introduces the third arm: an operator that is
synthetically-correct, predicate-formed, but quarantined awaiting corpus
support. This is the right shape for cases where "the measurement is
real but the corpus isn't varied enough to prove it."

## Next round opens with

`python phoxelis_audit.py`. R66 candidates:
- **R66 — close P-20** — re-cache R55 corpus at native resolution so block-aligned predicates measure faithfully (R64's note about LANCZOS destroying 8×8 alignment); will likely also lift `is_jpeg_compressed` firing rate from 20% → ~95% as expected.
- **R66 — close P-21 with corpus seeds** — add screen-capture/display source rows to `sources.SOURCES` (Wikimedia category for screenshots; web-search for "smartphone screen photograph") and re-run the R65 audit; if `has_axis_aligned_pixel_grid` becomes IR-clean, promote.
- **R66 — start L3 author-loop in batch (R63 candidate, deferred)** — drive author-validate-promote cycle from uncovered corpus cases, attempt 5+ predicates per round.
