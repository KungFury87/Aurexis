# Round 68 — first batch L3 author-loop, 6 IR-clean promotions

**Date:** 2026-04-29
**Track:** T1 vocabulary health, P-10 (LLM-as-author at scale)
**Status:** complete — vocabulary 110 → 116; 6/8 candidates IR-clean and promoted in a single round; first time the author-validate-promote cycle has run in batch

---

## What this round opened on

R63 closed the first single-predicate LLM-author-validate-promote cycle.
R68 tests whether the same cycle can run *in batch* — author multiple
predicates in a single pass, run them all through IR audit, promote
the IR-clean ones, defer or retire the rest.

Vincent's R65 push ("bigger/longer sweeps with less interaction")
provides the operating discipline: pack as much into each round as the
audit can validate cleanly.

## The 8 candidates

All bodies use existing operators. No new operators registered this round.

```
is_low_contrast_image            lt(std(scene), 0.10)
is_high_contrast_image           gt(std(scene), 0.30)
has_oversaturated_palette        gt(rgb_saturation_mean(color_scene), 0.50)
has_strong_blur_signature        lt(edge_density(scene, 1.0), 0.03)
is_overexposed_dominant          gt(bright_pixel_fraction(scene, 0.85), 0.50)
is_underexposed_dominant         gt(dark_pixel_fraction(scene, 0.15), 0.50)
has_strongly_warm_palette        gt(rgb_warmth_score(color_scene), 0.20)
is_likely_jpeg_pipeline_output   AND(gt(dct_block_boundary_energy(scene), 1.05),
                                     lt(chroma_to_luma_hf_ratio(color_scene), 0.50))
```

The last is a sensor-provenance L4 composite — JPEG block residue AND
chroma subsampling. The other 7 are L1 sensory invariants in
unrepresented territory (contrast levels, exposure dominance, blur).

## Audit on R55 LANCZOS corpus (N=42)

```
candidate                                fired   rate    decision
is_low_contrast_image                    16/42   38.10%  PROMOTE
is_high_contrast_image                    4/42    9.52%  PROMOTE
has_oversaturated_palette                 3/42    7.14%  PROMOTE
has_strong_blur_signature                 4/42    9.52%  PROMOTE
is_overexposed_dominant                   5/42   11.90%  PROMOTE
is_underexposed_dominant                  7/42   16.67%  PROMOTE
has_strongly_warm_palette                42/42  100.00%  defer
is_likely_jpeg_pipeline_output            7/42   16.67%  defer
```

IR audit at N=42: 100 equivalence classes, 5 multi-member.

**Promoted (6):** all six L1 candidates were IR-clean — i.e. their
verdict patterns did not match any other predicate's pattern in the
combined 118-predicate vocabulary. Fire rates span 9–38% (healthy
discrimination range).

**Deferred (2):**

- `has_strongly_warm_palette` fired 42/42 — saturating. Corpus is mostly
  picsum/iNat/MET, all of which lean warm. Saturating predicates
  carry no information *on this corpus*. The IR audit reports
  "no twin pattern" because no other predicate happened to also be
  always-True on this exact set, but a 100% rate is a vocabulary
  red flag (R28 retired predicates with this profile). Promotion
  deferred until either threshold is tightened (rgb_warmth_score >
  0.30 might separate desert/sunset from generic warm), or corpus
  is broadened.
- `is_likely_jpeg_pipeline_output` is the L4 composite. Its verdict
  pattern matched `is_jpeg_compressed` exactly — every image with
  block-boundary residue ALSO had chroma subsampling on this corpus.
  The AND collapses to one of its inputs. Architecturally redundant
  *on this corpus*. Could dissolve later when the corpus contains
  sources that have one signature without the other (e.g. PNG-served
  with chroma upsampling vs JPEG-served with full chroma).

## What this round changes

Three architectural notes:

1. **The cycle works at batch scale.** R63 closed the first single-shot
   cycle. R68 closes the first 8-shot cycle in a single round, with
   75% promotion rate. The substrate doesn't have to grow one
   predicate per round.
2. **Saturation and IR-collision are different rejection signatures.**
   `has_strongly_warm_palette` saturates (always-True); `is_likely_
   jpeg_pipeline_output` IR-collides (always matches another). Both
   are valid reasons to defer, but they need different unblock paths
   (threshold tightening vs corpus diversification).
3. **L4 composites can collapse to their constituents.** If the AND
   never disagrees with one of its inputs, the composite adds no
   discrimination. R68's deferred composite is the first explicit
   example of this in the project.

## Honest caveats

- **Audit was on R55 LANCZOS only (N=42), not the combined R55+R66+R67
  corpus (~76).** I attempted the combined audit but the bash session
  timed out at 45s. The R55 cache is the largest single consistent
  view; using it gave a clean answer for promotion decisions.
  Re-running on combined N=76 in R69 is reasonable check-back work.
- **The 100% saturation of `has_strongly_warm_palette` is suspicious
  on its own.** rgb_warmth_score returns positive whenever R+G > B,
  which is most of the visible spectrum. The threshold 0.20 is too
  permissive. Tightening to 0.30 would likely yield a usable
  predicate but would also need a fresh audit; it's deferred
  rather than tweaked-and-promoted in the same round to keep the
  audit chain auditable.
- **The "rejected" rate (2/8 = 25%) is a single data point** about
  what fraction of LLM-authored candidates survives. Future rounds
  will accumulate the actual base rate.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| Total predicates | R68 | **116** (110 + 6 batch-authored) | current — first batch promotion |
| Batch L3 author-loop promotion rate | R68 | 6/8 (75%) at single round | current; first datapoint |
| Predicates deferred for saturation | R68 | 1 (`has_strongly_warm_palette`, 100% on R55) | current; new defer reason class |
| L4 composites collapsing to constituent | R68 | 1 (`is_likely_jpeg_pipeline_output`) | current; first observed |

## Promises ledger updates

- **C-68 closes:** first batch L3 author-loop; 6 promotions in one round.
  This is partial fulfillment of P-10 ("LLM-as-predicate-author at
  scale"). Full closure of P-10 would mean recurring batches as
  needed, not a single one-shot round.

## Files added this round

- `round68_batch_authoring/round68_candidates.aurex` — 8 candidate predicates as DSL source
- `round68_batch_authoring/round68_audit.py` — full audit script
- `round68_batch_authoring/round68_audit.json` — IR-cleanness per candidate, promotable + rejected lists
- this report
- `vocab.aurex` — 6 promoted predicates appended (110 → 116) + comment block on the 2 deferred candidates
- `PHOXELIS_CHARTER.md` — predicate count 110 → 116
- `PHOXELIS_BENCHMARKS.md` — R68 row
- `PHOXELIS_PROMISES.md` — C-68 entry

## Sweep summary R65 → R68

| round | substrate change | preds | ops | category |
|---|---|---|---|---|
| R65 | Sensor-provenance family extended | 108 → 110 | 96 → 99 | new measurement family |
| R66 | Native-resolution corpus closes P-20 | (no DSL change) | (no op change) | corpus-quality fix |
| R67 | Pixel-grid candidate retired by falsification | (predicate not promoted) | 99 (op kept) | retirement-by-distribution |
| R68 | Batch L3 author-loop, 6 promotions | 110 → 116 | 99 (no new ops) | first batch promotion |

Net across the 4-round sweep: **+8 predicates** (6 R65+R68 promoted, 2 R65 sensor-provenance, 0 retired-from-vocab; 1 R67 candidate killed before vocab entry), **+3 operators** (R65 sensor-provenance), **2 promises closed** (P-20, P-21), **0 new pending promises opened**, **stale promise count holds** at the 6 long-running ones.

## Next round opens with

R69 candidates:
- **Re-audit at combined N=76 corpus** — sanity-check R68 promotions on the larger view; expect minor IR shifts but not collisions.
- **Threshold sweep on `has_strongly_warm_palette`** — find a value > 0.20 that gives a healthy fire rate (say 20–60%) and re-audit.
- **Continue batch L3 author-loop** — run another 6–10 candidates in a single round, accumulate base-rate data on what fraction of LLM-authored predicates survive.
- **Push toward P-01** — incremental corpus growth at native resolution, run vocabulary against accumulated cache.
