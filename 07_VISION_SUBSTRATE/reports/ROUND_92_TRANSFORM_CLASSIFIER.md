# Round 92 — substrate as partial transform-classifier

**Date:** 2026-04-29
**Track:** T6 substrate-purpose; recursive use of fingerprint deltas to characterize transformations
**Status:** complete — substrate has measurable filter-detection capability (2× within/between Jaccard ratio, 2.6× classifier lift over chance), but the signal is weak because most filter deltas are narrow

---

## What R92 measured

For each of R91's 13 filters × 5 corpus images = 65 trials:

```
delta = pre_fingerprint XOR post_fingerprint
      = (predicates that flipped from F→T) ∪ (predicates that flipped from T→F)
```

Then asked two questions:

1. **Are within-filter deltas more similar than between-filter deltas?**
2. **Can a nearest-neighbor classifier predict which filter caused a delta?**

If the substrate detects transformation type from fingerprint shift,
the predicate vocabulary measures *transformations on top of measuring
images* — a recursive substrate-purpose capability.

## Question 1: within vs between filter delta similarity

```
within-filter mean Jaccard:   0.130   (n=130 same-filter pairs)
between-filter mean Jaccard:  0.063   (n=1950 different-filter pairs)
within/between ratio:         2.08×
```

Same-filter deltas are about twice as similar as different-filter
deltas. The substrate has filter-specific signatures, but the absolute
similarity is low (0.13).

## Question 2: nearest-neighbor classifier (leave-one-out)

```
accuracy:  13/65 = 20.0%
baseline (uniform 13-class):  7.7%
lift over baseline:           2.6×
```

20% is far from 100% but well above chance. The substrate detects
filter type significantly better than random.

## Most confused filter pairs (physically sensible)

```
brighten      → contrast       (3 times)   both stretch luma upward
desaturate    → oversat        (3 times)   both move along saturation axis
sharpen       → contrast       (3 times)   both increase HF energy
invert        → solarize       (3 times)   both involve value-remapping
darken        → solarize       (2 times)   both darken pixels
contrast      → sharpen        (2 times)   reciprocal of above
```

The substrate's confusions cluster operators by physical effect — it
doesn't mistake "blur" for "invert", but it does mistake "brighten"
for "contrast" because they touch the same predicates (exposure,
contrast, dynamic range).

## Filter signature stability — invert is the cleanest signal

```
filter        mean Δsize    within-J   classification
invert            24.0       0.363     STRONGEST signature
cyanotype         19.8       0.289     STRONG (color rebuild)
hue_shift         10.0       0.239     consistent (color rotation)
vintage           14.0       0.147     consistent (color shift)
solarize          20.6       0.114     wide but inconsistent
darken             8.2       0.110     mild
blur              10.4       0.095     structural
posterize          9.0       0.078     structural
desaturate         3.2       0.076     mild (small Δ)
sharpen            7.4       0.055     mild
brighten           9.4       0.057     mild
oversat            3.0       0.040     mild (small Δ)
contrast           8.4       0.032     mild
```

**Filters that change image meaning have stronger signatures.** Invert
flips ~24 predicates with within-filter Jaccard 0.363. Mild appearance
filters (oversat, contrast, desaturate) flip 3–8 predicates with
within-Jaccard ≤ 0.08 — they're so weak the signal-to-noise ratio is
poor.

This continues R91's finding: **the substrate is more sensitive to
semantically-impactful filters and less to appearance-only filters**.
That's the right shape for a meaning-preserving substrate, even though
it limits classifier accuracy on subtle filters.

## What this means architecturally

The substrate measures transformations recursively:

> **Forward fiber:** image → fingerprint (R78 narrator)
> **Backward fiber:** target description → image whose fingerprint lands
> in right cluster (R86–R89)
> **Robustness:** fingerprint preservation tracks semantic change
> (R90, R91)
> **Transform-detection:** fingerprint *delta* tracks transformation
> type (R92, partial)

R92 is the first measurement of the substrate's transform-detection
strength. It's modest (2.6× chance, not say 10×) but real. Combined
with R91, the picture is: the substrate's fingerprint behaves as a
*meaning-preserving similarity measure*, and its delta behaves as a
*transformation-type detector*, both partial and both empirically
quantified.

## Honest caveats

- **N=65 is small for a 13-class classifier.** A 5× larger trial set
  (more images per filter) would tighten estimates.
- **Within-Jaccard 0.13 is genuinely low** — the substrate has weak
  filter-type signatures, not strong ones. Don't oversell.
- **Confusion-cluster sensibility is post-hoc.** I described
  brighten↔contrast as "both stretch luma upward" after seeing the
  result; I didn't predict it.
- **Mild filters (Δ size 3-8 predicates) have very low SNR.** Most of
  the within-Jaccard variance for them is noise.
- **No comparison to a learned classifier baseline.** A simple ML
  model on the raw fingerprint deltas could potentially beat 20% by
  far; we'd then need to ask what it learned that the Jaccard NN
  missed. R92 doesn't go there.

## Naming the cycle (charter §7)

R90 was step-1 win narrative; R91 widened it; R92 quantifies the
recursive capability. The arc from R86→R92 has been:

- R86: backward fiber works (categorical first, generic).
- R87: empirical map lifts recall.
- R88: tighter ingredients fail (substrate has no atomic ingredients).
- R89: reframe to neighborhood satisfaction (right metric).
- R90: meaning preserved through real CDN at lossy quality.
- R91: meaning preservation tracks semantic impact, not noise.
- R92: meaning *delta* partially encodes transformation type.

Each round added a refinement, and each refinement was the honest
generalization of the prior. I'm not claiming R92 closes a problem; it
characterizes one.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| Within-filter / between-filter Jaccard ratio | R92 | 2.08× (within 0.130, between 0.063) | current — substrate has filter-specific delta signatures, weakly |
| NN filter classifier accuracy (13-class) | R92 | 20% (13/65) vs 7.7% chance — 2.6× lift | current |
| Filter with strongest signature | R92 | invert (within-J 0.363, mean Δ 24 predicates) | current |
| Filter with weakest signature | R92 | contrast (within-J 0.032, mean Δ 8) | current |

## Promises ledger updates

- **C-92 closes:** substrate measures transformations partially; first
  empirical quantification of recursive substrate capability.

## Files added this round

- `round92_transform_classifier/round92_audit.py`
- `round92_transform_classifier/round92_audit.json`
- this report
- `PHOXELIS_PROMISES.md` — C-92 entry
- `PHOXELIS_BENCHMARKS.md` — R92 row

## Next round opens with

R93 — open. Plausible directions:
- **Train a learned classifier** on fingerprint deltas — does ML beat
  20% NN-Jaccard? If yes, what does it learn the substrate-as-tool
  doesn't?
- **Multi-filter chains** — apply 2-3 filters in sequence, measure
  whether composed delta = sum of individual deltas or shows
  cancellation (R88 showed forward composition is non-monotonic;
  delta composition might be too).
- **Larger trial set** — 20+ images per filter to tighten classifier
  accuracy and check if it stays at ~2-3× chance or rises.
- **Vincent-side** — phone-camera-in-the-loop or physical-capture
  stability work.
