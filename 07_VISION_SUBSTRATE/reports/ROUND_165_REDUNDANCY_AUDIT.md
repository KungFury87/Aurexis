# Round 165 — Vocab-redundancy audit CORRECTS R161+R164 framing: canonical 151-pred vocab has ZERO J=1.0 equivalence pairs at N=623; "hidden equivalences" reported in R161+R164 were artifacts (R161 = degenerate singleton-firing case, R164 = my own duplicate-threshold choices) — vocab is structurally cleaner than recent rounds suggested

**Date:** 2026-05-01
**Track:** P-01 (vocab-redundancy diagnostic)
**Status:** complete — systematic pairwise Jaccard scan of all 11,325 pairs in canonical 151-pred vocab on N=623 corpus finds **0 pairs at J=1.0**, **0 pairs at J ∈ [0.95, 1.0)**, and only **4 pairs at J ∈ [0.90, 0.95)**; the "3 hidden equivalences" claim from R161+R164 was a measurement artifact — R161's J=1.0 was a degenerate single-firing-predicate case (`has_high_edge_density` fires only 1/623 image so any conjunction with it has trivial J=1.0 to itself), R164's J=1.0 collisions were my own R164 thresholds happening to match existing canonical predicates' thresholds; canonical vocab structurally cleaner than recent rounds claimed; effective canonical vocab size = 151, NO collapse needed; 4 highest near-equivalences are the documented JPEG-artifact family (chroma_subsampled / extreme_chroma / circular / many_corners / jpeg_compressed clusters at J=0.86-0.95)

---

## What R165 settles

R161 and R164 surfaced "hidden vocab equivalences" as side-effects of
L4 and operator-level vocab work. R165 systematically scanned all
11,325 pairs in the canonical 151-pred vocab to catalog true
equivalences and corrects the prior framing.

Result: **0 J=1.0 pairs and 0 J≥0.95 pairs in the canonical vocab.**
The prior "3 hidden equivalences" claim was wrong — those were
measurement artifacts:

1. **R161's `has_high_edge_density ≡ has_high_frequency_residual`** —
   their actual Jaccard is **0.009**, not 1.0. The J=1.0 collision
   was between R161's `is_textured_busy_scene` (their conjunction)
   and `has_high_edge_density`, but only because `has_high_edge_density`
   fires on just **1 of 623** images — every conjunction with a
   1-image-firing predicate trivially has J=1.0 to itself.
2. **R164's `has_low_overall_brightness ≡ has_low_key`** — these
   were R164's own threshold choices duplicating existing
   canonical predicates. Not a hidden vocab redundancy; just
   redundant authoring on my part.
3. **R164's `has_low_local_variance ≡ is_low_contrast_image`** —
   same reason as #2.

The canonical 151-pred vocab is structurally cleaner than recent
rounds suggested.

## Method

Built firing matrix M (623 × 151). For each of 11,325 unique pairs
(i,j), computed Jaccard `|A ∩ B| / |A ∪ B|`. Bucketed by Jaccard
threshold:

```
J >= 1.0   (exact equivalence):       0 pairs
J >= 0.95  (near-equivalence):        0 pairs
J >= 0.90  (high near-equivalence):   4 pairs
J >= 0.80  (moderate near-eq):        17 pairs (above this band)
```

Built equivalence-class graph from J=1.0 pairs (Union-Find). Compared
rank with full vocab vs collapsed-equivalence vocab.

## Results

### 0 exact equivalences in canonical vocab

```
Pairs at J=1.0: 0
Pairs at J in [0.95, 1.0): 0
Effective canonical vocab size = 151 (matches published)
Δrank from collapsing equivalences = 0 (nothing to collapse)
```

### 4 pairs at J in [0.90, 0.95)

```
1. has_chroma_subsampled_signature ↔ has_extreme_chroma_subsampling    J=0.948
2. has_chroma_subsampled_signature ↔ has_circular_signature           J=0.926
3. has_circular_signature ↔ has_extreme_chroma_subsampling            J=0.917
4. has_extreme_chroma_subsampling ↔ has_many_corners                   J=0.903
```

All 4 involve the JPEG-artifact predicate family (sensor-provenance
predicates from R64-R65 and R67). They cluster because JPEG-compressed
images tend to have:
- Chroma subsampling (4:2:0 detected → `has_chroma_subsampled_signature`)
- Extreme chroma subsampling (more aggressive → `has_extreme_chroma_subsampling`)
- 8×8 DCT block boundaries → `has_circular_signature` (block patterns
  look ring-like)
- DCT artifacts → `has_many_corners` (block boundaries register as corners)

These are correlated by physics (JPEG compression has these signatures
together) but each captures a distinct measurement axis. Not redundant,
not equivalent; just correlated. Documented properly.

### Top 17 pairs at J ≥ 0.80

```
rank  a                                  b                                  J
1     has_chroma_subsampled_signature    has_extreme_chroma_subsampling     0.948
2     has_chroma_subsampled_signature    has_circular_signature             0.926
3     has_circular_signature             has_extreme_chroma_subsampling     0.917
4     has_extreme_chroma_subsampling     has_many_corners                   0.903
5     has_anisotropy_in_brightest_patch  has_chroma_subsampled_signature    0.893
6     has_chroma_subsampled_signature    has_many_corners                   0.893
7     has_clear_horizon                  has_horizontal_dominant_edges      0.890
8     has_anisotropy_in_brightest_patch  has_extreme_chroma_subsampling     0.875
9     has_many_corners                   is_jpeg_compressed                 0.869
10    has_chroma_subsampled_signature    is_jpeg_compressed                 0.861
11    has_extreme_chroma_subsampling     is_jpeg_compressed                 0.860
12    has_anisotropy_in_brightest_patch  is_jpeg_compressed                 0.860
13    has_anisotropy_in_brightest_patch  has_many_corners                   0.859
14    has_circular_signature             has_many_corners                   0.855
15    has_strongly_warm_palette          is_high_red_warm_scene             0.848
16    has_anisotropy_in_brightest_patch  has_circular_signature             0.831
17    has_atmospheric_haze               has_depth_indicators               0.807
```

12 of 17 involve JPEG-artifact family clustering. 1 reasonable
horizon-edge correlation (`has_clear_horizon ↔ has_horizontal_dominant_edges`,
J=0.890 — horizons usually have horizontal edges).
1 warm-palette redundancy (`has_strongly_warm_palette ↔ is_high_red_warm_scene`,
J=0.848 — semi-redundant authoring).
1 atmospheric/depth correlation (J=0.807).

### Correction: how the R161+R164 "equivalences" arose

```
R161 claim: has_high_edge_density ≡ has_high_frequency_residual
R165 actual: J = 0.009 (essentially no overlap)
R161 mechanism: has_high_edge_density fires only 1/623 images (almost
                dead); R161's `is_textured_busy_scene = high_edge_density
                ∧ high_frequency_residual` also fires only when
                high_edge_density fires (1 image); so J(textured_busy,
                high_edge_density) = 1.0 trivially. NOT an existing-vocab
                equivalence.

R164 claim 1: has_low_overall_brightness ≡ has_low_key
R165 actual: R164's predicate was my own authoring with threshold
             mean_i < 0.30, which happened to match existing has_low_key's
             threshold criterion. Not a hidden canonical-vocab
             equivalence; just redundant authoring by me.

R164 claim 2: has_low_local_variance ≡ is_low_contrast_image
R165 actual: Same reason. R164 std_i < 0.10 threshold was effectively
             the same as is_low_contrast_image's existing threshold.
             Authoring redundancy, not vocab redundancy.
```

In all 3 cases, the "hidden vocab equivalence" framing was wrong.
Canonical vocab has 0 J=1.0 pairs. The 4 J ∈ [0.90, 0.95) pairs
are documented correlations from sensor-provenance physics (R64-R65),
not redundancies.

### Implications for the architectural picture

The substrate scaling law from R160-R164 is unchanged:
- L4 vocab: 0.200 rank/pred (4-batch validated, R160-R163)
- Op-level vocab: 0.333 rank/pred (1-batch, R164)
- Corpus: 0.005 rank/image (saturated, R158→R159)

But the framing refines:
- Pre-R165: "vocab has hidden equivalences; effective vocab smaller
  than published count"
- Post-R165: "vocab has 0 exact equivalences; the published 151 IS
  the effective count; correlations exist (JPEG-family, horizon-edge)
  but each predicate captures a distinct measurement axis"

This actually makes the substrate's "alternative computational paradigm"
framing CLEANER — there's no hidden inefficiency in the canonical
vocab; the 151 predicates are 151 genuinely-distinct shapes of meaning.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| **Canonical 151-pred vocab has 0 exact equivalences at N=623** | R165 | systematic pairwise Jaccard scan of all 11,325 pairs: 0 at J=1.0, 0 at J in [0.95, 1.0), 4 at J in [0.90, 0.95); effective canonical vocab size = 151 (matches published) | round165 | current — vocab is structurally clean as published |
| **R161+R164 "hidden equivalences" claim CORRECTED to artifacts** | R161+R164+R165 | R161's J=1.0 was degenerate single-firing case (has_high_edge_density fires 1/623); R164's 2 J=1.0 collisions were my own threshold choices duplicating existing preds; canonical vocab unaffected | round161-165 | corrected — no hidden vocab redundancy exists |
| **4 documented near-equivalences in JPEG-artifact family** | R165 | chroma_subsampled / extreme_chroma / circular / many_corners cluster at J=0.85-0.95; correlations from sensor-provenance physics (R64-R65), not authoring redundancy; each captures distinct measurement axis | round165 | current — substrate vocab structurally documented |

## Honest caveats

- **My own work caused 2 false-positive "hidden equivalence" reports**
  in R164. Should have checked Jaccard between the new pred and the
  alleged equivalent existing pred more carefully before claiming
  equivalence in the canonical vocab.
- **R161's "hidden equivalence" report was based on degenerate
  has_high_edge_density (fires 1/623).** This single-firing case is
  itself a vocab-health issue worth flagging — R113 recalibrated this
  predicate to fire LESS, but at N=623 it now fires only 1 time,
  effectively dead at this corpus. R166 candidate could re-recalibrate.
- **The J=0.948 pair (chroma_subsampled ↔ extreme_chroma_subsampling)**
  is borderline — they could plausibly be distinguished by a corpus
  with mixed-quality JPEGs. Picsum's quality range might be too narrow
  to separate them.
- **Recent rounds R160-R164 correctly added rank** (validated by R163's
  scaling law). The "hidden equivalence" framing was a separate honest
  mistake; correcting it doesn't invalidate the scaling-law findings.
- **Pre-registration: directional "find equivalences" CONFIRMED**
  (found correlated pairs). Quantitative (3+ found per R161+R164)
  REJECTED — actual was 0 J=1.0 pairs in canonical vocab, the 3
  reported were artifacts. Pattern: reading too much into measurement
  artifacts caught by systematic audit.

## Promises ledger updates

- **C-165 closes:** Vocab-redundancy audit pass corrected R161+R164
  framing. Canonical 151-pred vocab has **0 exact equivalences (J=1.0)**
  and **0 near-equivalences (J ≥ 0.95)** at N=623. The "3 hidden
  equivalences" reported in R161+R164 were measurement artifacts
  (R161 degenerate single-firing case; R164 my own duplicate-threshold
  authoring). Effective canonical vocab size = 151, matching published.
  4 documented near-equivalences at J ∈ [0.90, 0.95) are from JPEG-
  artifact sensor-provenance physics, each distinct measurement axis.
  Substrate scaling laws from R160-R164 unchanged; framing refined to
  "no hidden inefficiency in canonical vocab."

## Files added this round

- `round165_redundancy/r165_redundancy_audit.py`
- `round165_redundancy/r165_redundancy_v2.py` (high-Jaccard pair listing)
- `round165_redundancy/round165_audit.json`
- this report
- `PHOXELIS_PROMISES.md` — C-165 entry
- `PHOXELIS_BENCHMARKS.md` — R165 rows + correction

## Next round opens with

R166 candidates:

**A — push R165.** Single-round-add to fresh push.bat.

**B — author actual NEW operators (not novel thresholds).** Test
upper bound of vocab-additions hierarchy. Predicts > 0.333 rank/pred.

**C — re-recalibrate has_high_edge_density.** Currently fires only
1/623 images at N=623; effectively dead. Lower threshold to bring
fire rate to 5-30% range.

**D — pivot to T6 MCP grounded-AI extensions.**

**E — multi-source corpus diversification.** Test if picsum's bias
limits rank growth.

**F — DSL extension to promote L4 compositions to canonical vocab.**

Lean **A then B**. B continues the architectural ceiling test —
authoring genuinely new measurement dimensions (e.g. fractal dimension,
color spatial autocorrelation, local entropy) and measuring per-pred
efficiency vs L4's 0.200 and op-level's 0.333. Predicts higher than
both, completing the hierarchy ceiling test.
