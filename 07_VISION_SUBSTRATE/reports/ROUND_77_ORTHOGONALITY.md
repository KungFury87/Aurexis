# Round 77 — predicate orthogonality / Jaccard similarity

**Date:** 2026-04-29
**Track:** T1 vocabulary health (deeper than IR — measures *near*-collisions)
**Status:** complete — substrate is broadly orthogonal at N=76; effective rank ~31

---

## What R77 measured

For all 125 non-erroring predicates × N=76 combined corpus:

1. Verdict matrix (125×76 boolean)
2. Pairwise Jaccard similarity J(A,B) = |A∩B| / |A∪B|
3. Singular value decomposition for effective dimensionality

R74 found IR collisions (J=1.0). R77 surfaces *near*-collisions (J ≥ 0.95)
that R74's exact-match check missed.

## Near-collision pairs (Jaccard ≥ 0.95)

| pair | jaccard | fire | notes |
|---|---|---|---|
| `has_text_like_signature` ~~ `is_text_dominant_subject` | 1.000 | 40/40 | known L1↔L4 redundancy from R74 |
| `has_gradient_energy` ~~ `has_many_corners`            | 0.986 | 71/72 | both fire on ~95% of corpus |
| `has_gradient_energy` ~~ `has_circular_signature`      | 0.972 | 71/69 | near-saturated cluster |
| `has_gradient_energy` ~~ `has_chroma_subsampled_signature` | 0.958 | 71/70 | both very high firing |
| `has_circular_signature` ~~ `has_many_corners`         | 0.958 | 69/72 | natural-image structure cluster |

The four "always-fires" predicates (`has_gradient_energy`,
`has_many_corners`, `has_circular_signature`,
`has_chroma_subsampled_signature`) form a cluster: any natural image with
*any* structure or *any* JPEG history triggers all of them. They're
**near-saturated** (HIGH bucket would have been the right name in R74,
which counted them as HEALTHY because rate was 0.91-0.95).

## Most-redundant active predicates (highest median Jaccard to vocab)

```
0.194  has_many_corners
0.192  has_anisotropy_in_brightest_patch
0.191  has_gradient_energy
0.187  has_circular_signature
0.184  has_chroma_subsampled_signature
0.181  has_significant_negative_space
0.171  has_specular_highlights
```

**Even the most-redundant predicate has median similarity only 0.194.**
A predicate is on average 19% similar to its most-similar half-of-the-vocab.
The substrate is broadly orthogonal — no predicate is a near-clone of
many others.

## Most-orthogonal active predicates (lowest median Jaccard)

15 predicates with median Jaccard ≈ 0.000 to the rest of the vocab —
they fire so rarely (R74 LOW bucket) that they overlap with almost
nothing. The substrate is more orthogonal *because* the rare-firing
predicates discriminate by absence.

## Effective dimensionality

SVD of the (mean-centered) verdict matrix (active predicates × 76):

| metric | value |
|---|---|
| Top 5 singular values | ~varied |
| 90% energy contained in | **31 components** |
| 99% energy contained in | **57 components** |
| Maximum possible (= N corpus) | 76 |

**Interpretation:** at N=76, the corpus exercises ~31 distinct "shapes
of meaning." The remaining 94 active predicates are correlated
combinations of those 31. This isn't a bug — it's the rate at which a
finite corpus excites a vocabulary. P-01 (10k+ corpus) would presumably
push effective dimensionality up substantially.

## What R77 changes

Three architectural notes:

1. **Near-saturation is its own bucket.** R74's HEALTHY range (0.05 ≤
   rate ≤ 0.95) included predicates at 0.93+ that R77 surfaces as
   near-redundant. Future coverage maps should use a tighter HEALTHY
   range (say 0.10–0.85) and add a NEAR-SATURATED bucket.
2. **Effective dimensionality > corpus diversity.** 31/76 = 41% of corpus
   slots carry independent signal. Worth tracking across corpus growth
   — if N=200 corpus also gives ~30 effective dims, that's a vocabulary
   ceiling not a corpus limit.
3. **No retirement is required.** The 4 near-saturated predicates
   (gradient_energy, many_corners, circular_signature,
   chroma_subsampled) stay in the vocab — they're correct individually
   and the redundancy is corpus-driven (most natural images DO have
   gradient energy, corners, etc.). At a screenshot-only or pure-color
   corpus their patterns would diverge.

## Honest caveats

- **Jaccard threshold 0.95 is somewhat arbitrary.** A few more pairs
  show up at 0.90 (not enumerated here).
- **SVD energy thresholds are sensitive to predicate-rate distribution.**
  90% energy at 31 components is partly driven by the always-fires
  cluster contributing one big eigenvector early.
- **3 raw_bayer-field predicates dropped** (always error on this
  corpus). Same situation as R74 ERRORED bucket.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| Near-collision pairs (J ≥ 0.95) | R77 | 5 (1 L1↔L4, 4 in always-fires cluster) | current — first deep-redundancy measurement |
| Median Jaccard, most-redundant predicate | R77 | 0.194 (`has_many_corners`) | current — substrate broadly orthogonal |
| Effective dimensionality (90% energy) | R77 | 31 of 76 components | current — first SVD measurement of substrate rank |

## Promises ledger updates

- **C-77 closes:** first orthogonality / effective-dimensionality measurement of the substrate.

## Files added this round

- `round77_orthogonality/round77_audit.py`
- `round77_orthogonality/round77_audit.json` — 5 high-similarity pairs + top-15 each side
- `round77_orthogonality/verdict_matrix.npy` — 128×76 int8 (cached for R78–R80)
- `round77_orthogonality/jaccard.npy` — 125×125 float64
- `PHOXELIS_PROMISES.md` — C-77 entry
- this report

## Next round opens with

R78 — Phoxelis narrator at full vocabulary scale: feed an image, return human-readable description from predicate fire pattern.
