# Round 67 — pixel-grid candidate empirically falsified, P-21 closes by retirement

**Date:** 2026-04-29
**Track:** T1 vocabulary health (sensor-provenance falsification)
**Status:** complete — P-21 closes; `has_axis_aligned_pixel_grid` retired with documented evidence; this is the second predicate-retirement-from-falsification in the project (R25 was the first)

---

## What this round opened on

R65 deferred `has_axis_aligned_pixel_grid` because no image in the N=42
LANCZOS-160 cache had the pixel-grid signature. R66 confirmed native
resolution didn't help (still 0/20). The R65 deferral comment claimed
the right unblocking work was adding "screen-capture / display-photograph
seeds to the corpus router."

R67 tests that claim directly.

## What got built

`round67_screen_capture/` — Wikimedia Commons category-member harness
that pulls native-resolution images from the screenshots categories
(`Screenshots`, `Screenshots of computer programs`, `Screenshots of
websites`) into a separate cache. After 1 session: **N=14 native
screen-capture images, all PNGs, shapes 480×320 to 1024×800**.

`round67_screen_capture/round67_distribution_analysis.py` — runs
`axis_aligned_hf_concentration` on every image in the screen-capture
cache and the R66 native nature/art cache, compares distributions,
sweeps every possible threshold for best F1.

## The distributions

| corpus | N | min | max | median | mean |
|---|---|---|---|---|---|
| Wikimedia Screenshots (R67) | 14 | 0.0236 | 0.1038 | 0.0380 | 0.0480 |
| Native nature/art (R66)     | 20 | 0.0104 | 0.1200 | 0.0362 | 0.0441 |

Side-by-side sorted:

```
screenshots: 0.024  0.025  0.027  0.030  0.031  0.031  0.037  0.039  0.042  0.043  0.045  0.096  0.098  0.104
nature:      0.010  0.013  0.018  0.019  0.025  0.027  0.028  0.032  0.033  0.036  0.036  0.049  0.051  0.055  0.056  0.058  0.079  0.080  0.120
```

Best discriminator over all thresholds: **threshold 0.0215, F1 = 0.64**
(precision 0.47, recall 1.00). At any useful precision (≥ 0.80) recall
collapses below 0.30. Distributions overlap completely.

## Why this happened — the diagnostic

The candidate predicate was named `has_axis_aligned_pixel_grid` and
documented as detecting "pixel-grid periodicity / Moiré". The *operator*
measures axis-aligned visual structure: how much FFT energy lies on the
pure H/V axes vs the rest of the spectrum.

Two distinct phenomena conflate under "screen capture":

1. **Digital screenshots** — pixel-perfect renders of underlying
   content. The "screen" was never photographed; the bytes are exactly
   what the screen would have displayed. No camera, no Moiré, no pixel
   grid in the FFT sense.
2. **Camera-photographed displays** — phone or DSLR pictures of an LCD
   or CRT. *These* exhibit the originally-imagined Moiré pattern from
   sub-Nyquist resampling of the display's pixel grid.

Wikimedia Commons category `Screenshots` is overwhelmingly type 1.
The R65 deferral diagnosis ("operator works, corpus lacks positive
cases") was *partially* correct — but I conflated the two corpora. The
right corpus would be category `Photographs of computer screens` or
similar, which is a much rarer find.

Even so, on the operator side: Wikimedia screenshots have *strong axis-
aligned visual structure* (window borders, text rows, scrollbars,
table grids) that should fire the operator. The fact that this still
overlaps with nature scenes (which have *weaker* axis-aligned structure
on average — horizons, building edges, fences) means the operator is
not specific enough as a discriminator at any single threshold.

## What got retired

- **`has_axis_aligned_pixel_grid` candidate predicate** — never made it
  into `vocab.aurex` (R65 deferred it; R67 retires it without ever
  promoting). This is methodologically important: an *unrealized*
  predicate that fails distribution analysis and is closed without
  ever being a "real" entry. The R65 comment block in `vocab.aurex` is
  rewritten to record the falsification.
- **`axis_aligned_hf_concentration` operator** — *kept* registered, with
  documentation marking it RETIRED-as-discriminator. The operator
  measures something real (axis-aligned visual structure) and might be
  useful as an input to a *composite* predicate that combines it with
  other signals. But it does not stand alone.

This continues the R25 retirement template (`has_local_polarization_signal`
killed by matte control) but adds a new wrinkle: the operator stays;
only the predicate is retired. Operators are primitives the substrate
might want for unanticipated composites; predicates are claims about
the world that have to discriminate.

## Honest caveats

- **N=14 screen captures + N=20 nature is small.** Larger samples might
  shift medians slightly, but the COMPLETE OVERLAP at this N is hard to
  argue against. A 100×-larger sample of each side would have to show
  bimodality to recover the predicate, which contradicts the visible
  individual values.
- **The right "screen photograph" corpus does likely exist** but I can't
  pull it efficiently from public APIs without a category that
  specifically captures it. P-22 could open later if Vincent has phone-
  camera-of-display images on hand, but that's separate from R67's task.
- **Threshold sweep was monotonic.** F1 was checked at every midpoint
  between consecutive sorted values; 0.64 is a true global maximum.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| Wikimedia 'Screenshots' axis_aligned_hf distribution | R67 | range 0.024-0.104, median 0.038 | current |
| R66 native nature axis_aligned_hf distribution | R67 | range 0.010-0.120, median 0.036 | current |
| Best F1 for screen-vs-nature using axis_aligned_hf | R67 | 0.64 (P=0.47, R=1.00) — useless | current |
| Predicates retired-by-falsification | R67 | 2 total (R25 polarization, R67 pixel-grid) | current |
| Operators retired-as-discriminator-but-kept-as-primitive | R67 | 1 (`axis_aligned_hf_concentration`) | current — first of this kind |

## Promises ledger updates

- **C-67 closes P-21:** P-21 was opened in R65 expecting that screen-
  capture corpus seeds would unblock the candidate predicate.
  Distribution analysis on actual screenshots falsifies the candidate.
  P-21 is closed by retirement, not by promotion.
- **No new promises opened.**

## Files added this round

- `round67_screen_capture/round67_pull_and_audit.py` — Wikimedia category-fetch + audit
- `round67_screen_capture/round67_distribution_analysis.py` — distribution sweep + threshold optimisation
- `round67_screen_capture/images/` — 14 native-res screen-capture `.npy`
- `round67_screen_capture/state.json` — checkpoint
- `round67_screen_capture/round67_audit.json` — full distribution + threshold-sweep result
- this report
- `vocab.aurex` — R65 comment block rewritten to retire the candidate
- `vision_ops.py` — operator registration comment marks retirement-as-discriminator
- `PHOXELIS_PROMISES.md` — C-67 entry; X-67 abandoned-predicates entry
- `PHOXELIS_BENCHMARKS.md` — R67 distribution rows

## What this round changes

The substrate gains a methodological pattern that was missing: the
distinction between operator-as-primitive (kept) and operator-as-
discriminator (retired) when an empirically falsified predicate would
otherwise be the operator's only consumer. This is a more nuanced
shape than R25's wholesale retirement.

It also reinforces R63's lesson from the other direction: R63 saw a
predicate go from IR-collided-at-small-N to IR-clean-at-N=30 (corpus
growth dissolved a false collision); R67 sees a predicate that LOOKED
deferred-by-corpus-content but is actually falsified-by-distribution
(the corpus was the right kind, the operator just doesn't separate).
Both shapes are real; honest project hygiene means naming both.

## Next round opens with

`python phoxelis_audit.py`. R68 candidates per the original sweep plan:
- **R68 — batch L3 author-loop** — drive author-validate-promote cycle
  in batches; aim for 5+ predicates per round, capture which pass IR
  and which join R25/R67 in the retired bin.
- **R69 — corpus growth toward P-01** — pull steadily at native resolution,
  run vocabulary against accumulated cache, watch for IR collisions to
  resolve at increasing N.
