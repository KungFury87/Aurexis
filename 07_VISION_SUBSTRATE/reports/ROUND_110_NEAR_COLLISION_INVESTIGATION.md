# Round 110 — near-collisions are saturation, not redundancy

**Date:** 2026-05-01
**Track:** T1 vocabulary health (R109 follow-up + push backlog)
**Status:** complete — diagnostic finding: all 4 predicates in the R109 near-collision cluster are near-saturating (91-95% fire rate) on natural photographs; the collisions are calibration drift, not operator redundancy; recalibration scheduled for R111+; push.bat for R109 staged

---

## What R110 does

Two-part round per R109's plan:

**Part A — push.bat for R109.** R109 added documentation only (no
canonical-file changes). A small push.bat lands the round dir +
report on the remote per the anti-drift contract.

**Part B — investigate the 5 near-collision pairs from R109.** Are
these predicate-design problems (operator redundancy → redesign
needed), or genuine corpus correlations (no redesign, document
instead), or something else?

The "something else" turned out to be the right answer.

## Method (Part B)

For each of the 5 near-collision pairs flagged in R109:

```
has_gradient_energy ↔ has_many_corners              J = 0.986
has_gradient_energy ↔ has_circular_signature        J = 0.972
has_gradient_energy ↔ has_chroma_subsampled_sig.    J = 0.972
has_circular_signature ↔ has_many_corners           J = 0.958
has_many_corners ↔ has_chroma_subsampled_sig.       J = 0.959
```

Compute on the same N=76 corpus from R109:
- agreement counts (both-fire, both-quiet)
- disagreement counts (a-only, b-only) and which scenes
- per-source breakdown (does the collision hold across 11 sources?)

Then: classify each pair as REDESIGN-POSSIBLE (operator change could
break collision), PHYSICAL-CORRELATION (predicates legitimately agree
on every scene), or MIXED (partial disagreement).

## Results — fire rates exposed the actual problem

```
predicate                              fires    rate
has_gradient_energy                    71/76    93.4%
has_many_corners                       72/76    94.7%
has_chroma_subsampled_signature        71/76    93.4%
has_circular_signature                 69/76    90.8%
```

**All four predicates fire on > 90% of the corpus.** They aren't
"correlated specifically with each other" — they're all near-saturating
together. The pairwise Jaccards are high because the fire patterns are
near-100% overlap by virtue of being near-100% TRUE everywhere.

This is a different category of problem than the R107 retirements:

| R107 retirements | R110 finding |
|---|---|
| Pairs of predicates with **identical** fire pattern (eq class collision) | Pairs of predicates **all near-saturating** on natural photos |
| Underlying operators encode same physical signal | Underlying operators encode different signals, but THRESHOLDS are too loose |
| Fix: retire redundant predicate | Fix: tighten thresholds so predicates discriminate again |

## Per-pair disagreement scenes

```
pair                                              disagreement scenes
has_gradient_energy ↔ has_many_corners            osm_5_17_24 (b-only)  [1 scene]
has_gradient_energy ↔ has_circular_signature      inat_335031197, osm_5_9_27 (a-only)  [2 scenes]
has_gradient_energy ↔ has_chroma_subsampled       wm_..._motograter, osm_5_13_15  [2 scenes]
has_circular_signature ↔ has_many_corners         inat_335031197, osm_5_17_24, osm_5_9_27 (b-only)  [3 scenes]
has_many_corners ↔ has_chroma_subsampled          osm_5_17_24, wm_..._motograter, osm_5_13_15  [3 scenes]
```

The disagreements are concentrated on:
- **OSM raster tiles** (5_13_15, 5_17_24, 5_9_27) — flat low-detail map content
- **One iNat photo** (335031197)
- **One Wikimedia photo** (motograter)

These are the few cases where the predicates discriminate. On
everything else (diagrams, histo, microscopy, paintings, satellite,
most of Wikimedia/iNat), all four predicates fire together — because
all four "fire when there's any detail" and natural photos always
have some detail.

## Per-source breakdown (sample)

`has_gradient_energy ↔ has_many_corners`:

```
source        a_only  b_only  both    neither  total
diagrams      0       0       7       0        7
histo         0       0       5       0        5
inat          0       0       4       0        4
met           0       0       4       0        4
microscopy    0       0       8       0        8
naturalearth  0       0       3       0        3
osm           0       1       5       4        10
paintings     0       0       6       0        6
picsum        0       0       13      0        13
sat           0       0       5       0        5
wm            0       0       11      0        11
```

Ten of eleven source types are 100% "both fire." The only source
with discrimination is OSM tiles. Same shape across all five pairs.

## Verdict — recalibration, not redesign

The R109 finding "near-collision pairs flagged for T1 redesign" was
the right alarm but the wrong remedy. **The four predicates aren't
operator-redundant — they're threshold-saturated on natural photos.**

Their thresholds were set in vocabulary v0.2 era (early synthetic-corpus
work). Synthetic test images often have simpler structure than natural
photographs, so a threshold like `gradient_energy > 0.0030` discriminated
synthetic scenes well but admits virtually every natural photo as "high
gradient energy."

**The fix is recalibration**: tighten thresholds (or use percentile-based
thresholds tuned against a real-world corpus) so each predicate fires on
~50% of natural photos, restoring its discrimination power.

Recalibration is **NOT done in R110** for two reasons:

1. **Validation cost**: each retuned threshold must be re-checked against
   its synthetic intent target (e.g., does `has_gradient_energy` still
   fire on the corpus-pump synthetic input that proved it works?). That's
   a multi-predicate threshold-sweep round, like R69 was for R68.

2. **Scope discipline**: R110's stated goal was "investigate the
   collisions and determine the right intervention." That's a diagnostic
   round. The intervention is a separate round (R111 candidate).

## Proposed R111: threshold recalibration

Concrete plan for R111 if the user proceeds:

| predicate | current threshold | current rate | target rate | direction |
|---|---|---|---|---|
| `has_gradient_energy` | `> 0.0030` | 93% | ~50% | tighten threshold |
| `has_many_corners` | (check vocab.aurex) | 95% | ~50% | tighten threshold |
| `has_chroma_subsampled_signature` | (chroma/luma HF ratio < threshold) | 93% | likely keep at high — most images ARE JPEG-origin | maybe leave |
| `has_circular_signature` | `orientation_distribution_continuity` threshold | 91% | ~30-50% | tighten |

After retuning, re-run R109's IR audit to confirm:
1. Fire rates land in target ranges (not ALWAYS / not DEAD)
2. Pairwise Jaccards drop below the 0.95 collision threshold
3. Predicates still fire on their original intent-target synthetic inputs

## Honest caveats

- **`has_chroma_subsampled_signature` may legitimately fire at 93%.** Most
  internet-cached images come from JPEG sources, so chroma-subsampling
  artifacts are genuinely common. Recalibration of THIS predicate may
  not move much. The other three should respond strongly.
- **N=76 corpus is mostly photographic.** A retuned threshold derived
  from this corpus will fire correctly on real-world photos but might
  saturate on a hypothetical "super-detailed" corpus or under-fire on
  a "minimalist" corpus. Multi-corpus calibration (R80 cross-corpus
  drift framework) is the right long-term solution.
- **Disagreement scenes are tiny (1-3 per pair).** Even at saturating
  rates, the predicates ARE different at the operator level — they
  just rarely express that difference on natural photos. The
  underlying physics is fine; only the boolean threshold needs work.

## Files added this round

- `round110_collisions/round110_collisions.py`
- `round110_collisions/round110_audit.json`
- this report
- `push_round109_ir_at_scale.bat` (workspace-level — covers R109's
  documentation-only push)

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| R109 near-collisions diagnosed as saturation, not redundancy | R110 | All 4 predicates fire 91-95% on natural photos; collisions are calibration drift, not operator redundancy | current — actionable diagnostic for R111+ recalibration |
| Per-source collision breakdown | R110 | 10 of 11 source types show 100% both-fire on the worst pair (`has_gradient_energy ↔ has_many_corners`); only OSM raster tiles produce discrimination | current — saturation pattern is corpus-wide, not source-localized |

## Promises ledger updates

- **C-110 closes:** R109 near-collision investigation. Diagnosed as
  threshold saturation. Recalibration scheduled for R111. No
  predicate retirements; no canonical-file changes; substrate state
  unchanged.

## Next round opens with

R111 candidates:

**A — execute threshold recalibration**: tighten thresholds on
`has_gradient_energy`, `has_many_corners`, and `has_circular_signature`
based on N=76 corpus distribution; re-run IR audit; verify
collision-J drops below 0.95 and synthetic-intent tests still pass.

**B — multi-modal corpus IR audit**: pull a real RGB+depth dataset
(NYUv2 small subset) so the R107 multi-modal predicates can be
audited at scale. Currently they correctly abstain on all 76
RGB-only images; we don't yet know their fire rates on actual
multi-modal data.

**C — ship the R109 push first** then do A. Both A and B require
canonical-file changes (vocab.aurex thresholds for A; possibly
visual_intake.py for B), so pushing R109's docs first keeps each
push scoped.

Lean toward **C then A** — push first per anti-drift, then attack
the now-actionable recalibration.
