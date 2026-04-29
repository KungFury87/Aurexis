# Round 69 — combined-corpus re-audit + threshold recovery

**Date:** 2026-04-29
**Track:** T1 vocabulary health
**Status:** complete — 6 R68 promotions verified IR-clean at N=76; one R68 deferred candidate recovered via threshold sweep, vocabulary 116 → 117

---

## What got measured

**Combined corpus** (R55 LANCZOS + R66 native + R67 screenshots = 42 + 20 + 14 = N=76).

Full 116-predicate vocabulary evaluated against all 76 images, downsampled to 320 max-side at eval time.

```
eval done in 14.3s
102 eq classes, 3 multi-member
```

R63's small-N collapse hypothesis continues to play out: at N=42 we saw
93 eq classes / 5 multi; at N=76 we see 102 eq classes / 3 multi. As
the corpus grows, more predicates become discriminable.

## R68 promotion verification

| predicate | R68 (N=42 LANCZOS) | R69 (N=76 combined) | status |
|---|---|---|---|
| is_low_contrast_image      | 16/42 (38.10%) | **19/76 (25.00%)** | IR-clean |
| is_high_contrast_image     |  4/42 ( 9.52%) |  **7/76 ( 9.21%)** | IR-clean |
| has_oversaturated_palette  |  3/42 ( 7.14%) |  **5/76 ( 6.58%)** | IR-clean |
| has_strong_blur_signature  |  4/42 ( 9.52%) |  **4/76 ( 5.26%)** | IR-clean |
| is_overexposed_dominant    |  5/42 (11.90%) | **17/76 (22.37%)** | IR-clean |
| is_underexposed_dominant   |  7/42 (16.67%) |  **8/76 (10.53%)** | IR-clean |

All 6 hold. Two showed expected rate shifts:
- `is_low_contrast_image` rate dropped (LANCZOS thumbnails were unusually
  flat; native-resolution images have richer std).
- `is_overexposed_dominant` rate doubled (R66 native + R67 screenshots
  contain more bright-dominant content than the picsum/iNat LANCZOS mix).

## Threshold recovery on `has_strongly_warm_palette`

R68 deferred this predicate because at threshold 0.20, fire rate was
42/42 = 100% on the LANCZOS corpus. R69 sweep on the combined N=76
corpus reveals why and finds the right value.

**Warmth distribution (combined N=76):** min=0.3988, max=0.6136,
median=0.5210.

The original threshold 0.20 was below the entire corpus floor — every
image cleared it. The corpus operator value range is much narrower
than the synthetic-test value range I'd assumed.

**Threshold sweep (rgb_warmth_score > T):**

```
thr   fired/n     rate     status
0.20   76/76    100.00%   IR-clean (saturated)
0.30   76/76    100.00%
0.40   74/76     97.37%
0.46   62/76     81.58%
0.50   46/76     60.53%
0.52   38/76     50.00%
0.54   28/76     36.84%   <-- selected
```

Threshold 0.54 gives 36.84% fire rate, IR-clean, healthy
discrimination. **Promoted at 0.54.** Vocabulary 116 → 117.

## What this round changes

Two patterns reinforced:

1. **Deferred-then-recovered.** R63 promoted a R54-deferred predicate
   after corpus growth dissolved its IR collision. R69 promotes a
   R68-deferred predicate after threshold sweep on a wider corpus.
   Different mechanism (threshold tuning vs corpus growth), same
   shape: deferral isn't retirement; it's "wait for the right
   conditions."
2. **Synthetic-vs-corpus operator-value distributions diverge.** I
   chose threshold 0.20 in R68 because synthetic-warm-image tests
   (perfect orange/red blocks) easily cleared 0.30. Real-world
   corpus images are *all* "somewhat warm" by the operator's
   measurement, just at higher absolute values. **Lesson:** future
   thresholds should be calibrated against the actual corpus
   distribution at promotion time, not against synthetic ground-truth.

## Honest caveats

- **Combined corpus is small (N=76).** R63 saw IR-clean at N=30, R69
  confirms at N=76; both well below P-01's 10,000+ target.
- **Eval downsamples to 320 max-side** to fit in the bash timeout
  budget. Block-aligned predicates (R64/R65 sensor-provenance) may
  measure slightly differently here than on full-native; the R68
  candidates don't depend on pixel-grid alignment so they're stable.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| Total predicates | R69 | **117** (116 + warmth re-promoted) | current |
| R68 promotions stable at N=76 | R69 | 6/6 IR-clean | current |
| Multi-member classes | R69 | 3 (was 5 at N=42, was 6 at N=20 in R55) | current — R63 small-N collapse continues |
| Deferred-then-recovered predicates | R69 | 2 total (R63 `has_busy_textured_scene`, R69 `has_strongly_warm_palette`) | current |

## Promises ledger updates

- **C-69 closes:** combined-corpus re-audit + threshold recovery; partial fulfillment of P-10 (LLM-as-author) at scale.

## Files added this round

- `round69_combined_threshold/round69_audit.py` — chunked combined-corpus IR audit + warmth threshold sweep
- `round69_combined_threshold/round69_audit.json` — full results
- `vocab.aurex` — `has_strongly_warm_palette` appended at threshold 0.54 (116 → 117)
- this report
- `PHOXELIS_BENCHMARKS.md` — R69 row + combined-corpus row
- `PHOXELIS_PROMISES.md` — C-69 entry

## Next round opens with

R70 — second batch L3 author-loop, accumulate base-rate data on what
fraction of LLM-authored predicates survive IR audit at scale.
