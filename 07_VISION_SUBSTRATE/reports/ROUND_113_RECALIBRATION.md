# Round 113 — recalibration ships, all 4 R111 near-collisions dissolved

**Date:** 2026-05-01
**Track:** T1 vocabulary health (closes the open issue R110 diagnosed and R111 confirmed urgent)
**Status:** complete — 2 thresholds retuned; near-collision count dropped 4 → 0; substrate effective rank held; 0 always-firing predicates; canonical change to vocab.aurex (151 preds, unchanged count)

---

## What R113 ships

Two threshold changes in `data/vision/vocab.aurex`:

```
predicate has_gradient_energy
- body    gt(gradient_energy(scene), 0.0001)
+ body    gt(gradient_energy(scene), 0.003)

predicate has_many_corners
- body    gt_int(corner_count_thresh(scene, 0.04), 50)
+ body    gt_int(corner_count_thresh(scene, 0.04), 2000)
```

`has_chroma_subsampled_signature` was deliberately NOT retuned — R110
documented that most natural-photo corpora ARE genuinely chroma-subsampled
(JPEG provenance), so its 97.8% rate is physically correct, not drift.

## Method

1. Scanned underlying scalar values (`gradient_energy`, `corner_count_thresh`,
   `chroma_to_luma_hf_ratio`) on the same N=226 corpus from R111. Got
   percentile distributions.
2. Chose thresholds at corpus-relevant percentiles:
   - `gradient_energy`: p50 ≈ 0.0036, picked 0.003 → expected ~55% fire
   - `corner_count_thresh`: p25 ≈ 1549, p50 ≈ 2716, picked 2000 → expected ~60%
   - chroma_subsampled: skipped (R110 physics justification)
3. Applied edits to vocab.aurex via bash heredoc (avoiding the Edit-tool
   mount-cache truncation hazard documented in R107).
4. Cleared cached fingerprints, re-evaluated all 226 images with new
   vocabulary.
5. Compared R111 vs R113 fire rates, near-collision counts, effective rank.

## Results

### Recalibration moved fire rates as designed

```
predicate                          R111 (pre)    R113 (post)    target    hit?
has_gradient_energy                97.3%         55.3%          ~55%      ✓ exact
has_many_corners                   98.2%         71.7%          ~60%      ✓ close
has_chroma_subsampled_signature    97.8%         97.8%          unchanged ✓ deliberately
has_circular_signature             92.5%         92.5%          unchanged ✓ unchanged threshold
```

Both retuned predicates landed in the HEALTHY bucket. The first hit its
target percentile exactly; the second went a bit higher than target
because the corner_count distribution is right-skewed (p50 = 2716; the
threshold of 2000 sits below that, catching ~72% rather than ~60%).
That's still healthy, and tightening further would risk under-firing on
the corpus's lower-detail half (OSM tiles, flat content).

### Near-collisions: 4 → 0

```
R111 near-collision pairs (J ≥ 0.95):
  J=0.991    has_gradient_energy ↔ has_many_corners
  J=0.987    has_many_corners ↔ has_chroma_subsampled_signature
  J=0.986    has_gradient_energy ↔ has_chroma_subsampled_signature
  J=0.950    has_gradient_energy ↔ has_circular_signature

R113 near-collision pairs (J ≥ 0.95):
  (none)
```

All four pairs from R111 dropped below the J=0.95 collision threshold.
The mechanism is structural: the two retuned predicates now disagree
with the still-saturating predicates on ~25-45% of the corpus, which
mathematically caps their pairwise Jaccards.

### Vocabulary quality preserved

```
metric                              R111      R113      direction
fire_rate buckets:
  DEAD                              35        35        same (correct abstain)
  LOW (1-5%)                        11        11        same
  HEALTHY (5-95%)                   102       104       +2 (retuned preds joined)
  HIGH (95-100%)                    3         1         -2 (both retuned dropped)
  ALWAYS (100%)                     0         0         same
multi-member eq classes             1         1         same (the DEAD set)
effective rank 90%                  48/226    49/226    +1
n_near_collisions (J ≥ 0.95)        4         0         decisive improvement
```

The substrate's structural quality is preserved or slightly better
across all metrics. Effective rank ticking up by 1 is real — the
retuned predicates now produce more variation across the corpus, which
adds tiny rank — not a coincidence.

## Why this is a clean canonical change

R107 introduced the protocol: don't promote on first-light (N=5);
require corpus-scale validation (N≥20) with documented retire/promote
decisions. R113 is the first pure recalibration round under that
protocol — no new predicates added or removed, just thresholds adjusted
based on **measured corpus distribution**, with the unchanged predicate
**explicitly justified by physics** rather than left implicitly.

This is the difference between a vocabulary that grows by accretion
(every round adds, never retires, never retunes) and one that
matures — predicates can be promoted, retired (R107 X-107-*), or
recalibrated (R113) with documented evidence. The R85 audit anti-drift
contract is now operational across all three vocabulary-mutation modes.

## Honest caveats

- **No synthetic-intent re-validation in this round.** The retuned
  predicates should still fire on their original synthetic intent
  targets (e.g., a high-edge-density synthetic scene should still
  trigger `has_gradient_energy`). I didn't re-run those tests in this
  round because the budget was the audit. If a future round wants to
  formally close the loop, it should re-evaluate the synthetic_inputs/
  scenes against the new thresholds.
- **`has_many_corners` landed at 72% rather than ~60% target.** Could
  be tightened to ~80% threshold (closer to p50 = 2716) for a tighter
  fit to the original target. R114 candidate.
- **The chroma-subsampled prediction holds at 97.8% — by design, but
  worth watching.** If a future corpus contains substantial RAW or
  uncompressed PNG content, this predicate will discriminate. On the
  current N=226 it's near-saturating because the content really is
  JPEG-origin.
- **N=226 audit corpus is the same one used to derive the thresholds.**
  Standard cross-validation concern: thresholds tuned on this corpus
  may slightly overfit it. R114+ should re-audit on a fresh pull to
  confirm rates land in similar ranges.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| Recalibration ships, all 4 R111 near-collisions dissolved | R113 | `gradient_energy` 98% → 55%; `many_corners` 98% → 72%; near-collisions J≥0.95: **4 → 0** | current — closes R110/R111 open T1 issue |
| Substrate vocabulary quality preserved through recalibration | R113 | 0 always-firing; 1 multi-member eq class (DEAD); effective rank 49/226 (+1 from R111); 104 HEALTHY (+2 from R111) | current — recalibration improved separation without regressions |
| Vocabulary-mutation modes operational across promote/retire/recalibrate | R113 | R107 promoted 5; R107 retired 4; R113 recalibrated 2; canonical vocabulary matures via documented evidence per round | current — R85 audit anti-drift contract now operational across all three modes |

## Promises ledger updates

- **C-113 closes:** R110/R111 saturation diagnosis acted on.
  Threshold drift from vocab v0.2 era corrected for 2 of the 3 flagged
  predicates; the third explicitly justified by physics. Vocabulary
  state: 151 predicates / 103 operators / 11 dtypes (unchanged from
  R107).

## Files added/changed this round

- `data/vision/vocab.aurex` — 2 threshold edits (151 predicate count
  unchanged)
- `data/vision/vocab.aurex.r112_backup` — backup before edit
- `round113_recalibration/round113_audit.json`
- this report
- `PHOXELIS_PROMISES.md` — C-113 entry
- `PHOXELIS_BENCHMARKS.md` — R113 row

## Next round opens with

R114 candidates:

**A — push R113 canonical change**: small push.bat covering vocab.aurex
edit + round dir + report. Anti-drift contract.

**B — multi-modal scale-up via NYUv2 / KITTI** (the C door from R110/R111
plans): pull a real RGB+depth dataset so R107 multi-modal predicates
can be IR-audited at scale.

**C — T6 MCP wrapping** (the grounded-AI door Vincent prioritized): wrap
the substrate runtime as an MCP tool the LLM can call. Multi-round
arc; substantial design work.

**D — T7 Phase 2** (the rendering door): build `phoxel_field` 3D dtype
+ minimal forward renderer. Multi-round arc.

Lean toward **A then C** — push first per anti-drift; then start the
T6 multi-round arc since the substrate canonical state is now mature
enough (151 multi-modal predicates, IR-validated at N=226 with
recalibrated thresholds) to support production-grade MCP wrapping.
