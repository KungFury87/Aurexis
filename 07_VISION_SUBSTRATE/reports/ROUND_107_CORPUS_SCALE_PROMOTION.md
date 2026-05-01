# Round 107 — N=20 corpus-scale audit promotes 5 of 9 R103-R105 predicates; vocab.aurex 146 → 151

**Date:** 2026-05-01
**Track:** T1 vocabulary health × T8 phoxel-native capture
**Status:** complete — substrate is now genuinely multi-modal at the canonical-vocabulary level (depth + hyperspectral dtypes shipped); 4 candidate predicates retired with documented reasons (R63 small-N collapse confirmed)

---

## What changed in canonical files

| file | change |
|---|---|
| `aurexis_workbench/fields.py` | `VALID_DTYPES` adds `"depth"` and `"hyperspectral"` |
| `aurexis_workbench/vision_ops.py` | adds 4 operators: `mean_depth`, `foreground_fraction`, `narrow_peak_score`, `chlorophyll_red_edge` (in new `register_r107_ops()` called from `register_all()`) |
| `data/vision/vocab.aurex` | adds 5 promoted predicates, **146 → 151** |

The audit confirms 151 predicates parse, type-check, and install through the
runtime — substrate is end-to-end multi-modal in the canonical state, not
just in experimental round scripts.

## Method

Built a deliberately systematic 4×5 corpus: 4 depth structures
(`far`, `close`, `uniform`, `gradient`) × 5 spectral profiles
(`chlorophyll`, `narrow_green`, `narrow_red`, `broad_warm`, `broad_flat`) =
**20 scenes**, each carrying paired RGB + depth + hyperspectral fields.

For each of the 9 R103-R105 candidate predicates, run 4 tests:

1. **Fire rate in [10%, 70%]** — neither too rare to be useful nor too
   common to be discriminative.
2. **Equivalence-class clean** — no other predicate produces an
   identical fire pattern across all 20 scenes.
3. **Max Jaccard with existing 146 < 0.95** — no near-collision with an
   already-canonical predicate.
4. **(Cross-modal) selectivity at scale** — predicates whose body
   ANDs across modalities should fire on the right intersection of
   conditions, not on either single-modality match alone.

Predicates passing all checks → promoted to `vocab.aurex`. Predicates
failing → retired with documented reason in this report and not added to
canon.

## Results

```
predicate                          fire_rate  max_J  decision
has_shallow_depth_signal           0.25       0.27   RETIRE (eq-class collision)
has_dominant_foreground            0.25       0.27   RETIRE (eq-class collision)
has_far_field_dominance            0.50       0.50   PROMOTE
has_narrow_spectral_peak           0.40       0.50   PROMOTE
has_broad_spectral_distribution    0.20       1.00   RETIRE (J=1 with has_low_saturation)
has_red_shifted_centroid           0.40       1.00   RETIRE (J=1 with has_red_dominant)
is_distant_vegetation              0.10       0.25   PROMOTE
is_close_chromatic_object          0.10       0.20   PROMOTE
is_uniform_lit_far_field           0.20       0.50   PROMOTE
```

**5 PROMOTE / 4 RETIRE.**

## Retirements (with documented reasons)

### 1. `has_shallow_depth_signal` ↔ `has_dominant_foreground` collide

At N=5 (R103) these looked like distinct concepts. At N=20 their fire
patterns are **identical** across the corpus: any scene with a
foreground subject (≥25% pixels closer than 0.4) ALSO has high
depth-variance (std/mean > 0.4), and vice versa. They're aliases of
the same underlying "is there a near-camera subject?" signal.

This is **R63's small-N collapse hypothesis confirmed at N=20** —
predicates that look IR-clean at small corpus sizes can collapse into
equivalence classes when the corpus grows. Vincent's R85 audit
explicitly called for this kind of falsification work.

The cleaner of the two for a future redesign would be a single
`has_close_subject` predicate, but neither current candidate is
promoted.

### 2. `has_broad_spectral_distribution` Jaccard 1.0 with `has_low_saturation`

The "narrow_peak_score < 0.045" condition fires on the same scenes
that have `has_low_saturation` already firing. This is physically
sensible: a flat broadband spectrum integrated through RGB
sensitivity curves yields near-equal R/G/B values → low chroma → low
saturation. The 146-predicate vocabulary already encodes this
information through the color predicates.

Adding a hyperspectral version doesn't add discrimination — just
duplicates an existing axis. Retired as redundant.

### 3. `has_red_shifted_centroid` Jaccard 1.0 with `has_red_dominant`

Same shape of finding as #2: `band_centroid > 0.6` fires on exactly
the scenes that have `has_red_dominant`, `has_warm_palette`, and
`is_indoor_warm_scene` already firing. The hyperspectral centroid
captures the same "energy biased toward longer wavelengths" signal
that the existing RGB-channel-imbalance predicates already encode.

Retired as redundant.

## Promotions (with confirmed properties)

### `has_far_field_dominance` — fires on 10/20 (50%), max J 0.50

The simplest depth predicate. Fires on every scene whose mean depth >
0.7. With 4 depth structures × 5 spectra, this is the 2 "far"
configurations × 5 spectra = 10/20 — exactly the fire rate the body
predicts. Clean discrimination.

### `has_narrow_spectral_peak` — fires on 8/20 (40%), max J 0.50

Fires on every scene whose dominant single band carries > 7.5% of
total band energy (narrow gaussian peak). This is the 2 narrow-peak
spectra × 4 depth structures = 8/20. The predicate is doing exactly
what its body says.

### `is_distant_vegetation` — fires on 2/20 (10%), max J 0.25

Cross-modal: AND(far depth, chlorophyll red-edge step). Fires on
`far_chloro` AND `grad_chloro` (gradient depth averages 0.80, also
"far"). The R105 N=5 specificity test predicted only `far_chloro`,
but at N=20 `grad_chloro` correctly also passes (gradient mean depth
≥ 0.7). The predicate's behavior at scale is more permissive than
N=5 made it look — but in a way the body's literal logic correctly
admits.

Crucially, it correctly rejects:
- `close_chloro` (chlorophyll spectrum but close depth)
- `far_n_green` (narrow green peak, would fool any RGB-only "looks
  green" predicate)
- `far_warm` (warm spectrum, no chlorophyll red-edge step)

### `is_close_chromatic_object` — fires on 2/20 (10%), max J 0.20

Fires on `close_n_green` and `close_n_red` — the two scenes with
both close foreground and a narrow spectral peak. Matches design at
scale exactly.

### `is_uniform_lit_far_field` — fires on 4/20 (20%), max J 0.50

Fires on `far_warm`, `far_flat`, `grad_warm`, `grad_flat` — the four
combinations of far-field depth × broad/flat spectrum. The R105 N=5
list expected only `distant_dusk` (warm + far_grad). The N=20 corpus
correctly admits all 4 design-matching scenes.

## Why this round matters

This is the FIRST time the substrate's canonical vocabulary has been
extended with multi-modal predicates that have passed corpus-scale
validation, not just first-light demonstration. The promotion
protocol from Vincent's R85 audit is:

1. Author predicate experimentally (R103-R105)
2. Validate on small corpus (N=5)
3. Hold experimental, do NOT promote
4. Run corpus-scale audit (N≥20)
5. Promote only those that pass IR-clean, fire-rate, collision tests

R107 is step 4-5 done correctly. The 4 retires are not failures —
they are the protocol working: predicates that look fine at N=5 but
collapse under scrutiny get caught BEFORE they pollute the canonical
vocabulary.

## Substrate state after R107

| metric | before R107 | after R107 |
|---|---|---|
| `vocab.aurex` predicate count | 146 | **151** |
| operators registered | 99 | **103** |
| `VALID_DTYPES` entries | 9 | **11** |
| modalities supported | 4 (image, color_image, image_stack, scalar) | **6** (+ depth + hyperspectral) |
| canonical multi-modal predicates | 0 | **3** (cross-modal) |
| canonical depth-only predicates | 0 | **1** |
| canonical hyperspectral-only predicates | 0 | **1** |

Every R-round through R85 had been growing the vocabulary monotonically
along the photometric/color/temporal axes. R107 is the first time the
vocabulary has grown along a structurally new axis (geometric depth +
spectral) AND retired predicates that didn't pass scale.

## Honest caveats

- **Synthetic corpus, not real-world captures.** The N=20 audit uses
  hand-crafted depth maps and gaussian-summed spectra. A real-world
  audit needs LiDAR / structured-light / hyperspectral-instrument
  data. T8 next rounds (R108+) should pull from KITTI/CAVE if access
  becomes feasible.
- **N=20 is the floor, not the ceiling.** Real IR audit at scale
  per the charter's P-01 promise targets N≥10,000. R107 confirms 5
  predicates clean at N=20; future rounds should re-audit at N≥100.
- **3 of 4 cross-modal predicates' "expected" sets in R105 were
  too narrow.** This wasn't a predicate bug — the predicates fire
  on what their bodies say. R105's specificity test under-predicted
  the legitimate fire set. R107's corpus correctly exposed this.
- **The 3 retires for redundancy (broad_spectral, red_shifted_centroid)
  show the substrate's hyperspectral predicates can duplicate
  existing RGB-derived signals.** Future hyperspectral predicates
  should be designed to capture features that RGB CANNOT — like the
  chlorophyll red-edge step — not features that RGB indirectly
  encodes.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| Vocabulary growth via corpus-scale promotion | R107 | 146 → 151 (5 PROMOTE / 4 RETIRE from R103-R105 candidates at N=20) | current — first multi-modal canonical vocabulary |
| R63 small-N collapse confirmed at N=20 | R107 | `has_shallow_depth_signal` ↔ `has_dominant_foreground` Jaccard 1.0 (eq-class collision); both retired | current — protocol catches it BEFORE canonical pollution |
| Operator + dtype additions | R107 | +4 operators (`mean_depth`, `foreground_fraction`, `narrow_peak_score`, `chlorophyll_red_edge`); +2 dtypes (`depth`, `hyperspectral`) | current — substrate canonical state is multi-modal |

## Promises ledger updates

- **C-107 closes:** corpus-scale validation of R103-R105 candidate
  predicates. 5 promoted to `vocab.aurex`; 4 retired with documented
  reason. P-22/P-23 progressed (T7 + T8 tracks now have canonical
  vocabulary support).

## Files added/changed this round

- `aurexis_workbench/fields.py` (+ "depth", "hyperspectral" to VALID_DTYPES)
- `aurexis_workbench/vision_ops.py` (+ 4 operator defs + register_r107_ops)
- `data/vision/vocab.aurex` (+ 5 predicate blocks, 146 → 151)
- `round107_validation/round107_audit.py`
- `round107_validation/round107_audit.json`
- this report
- `PHOXELIS_PROMISES.md` — C-107 entry + 4 X-107-* abandonment rows
- `PHOXELIS_BENCHMARKS.md` — R107 row
- `PHOXELIS_CHARTER.md` — Section 4 layer table updated to 151/103

## Next round opens with

R108 candidate options:

**A — push R107 changes**: vocab.aurex + fields.py + vision_ops.py
changes need a new push.bat. Anti-drift contract from Vincent's audit.

**B — multi-view modality (R105-original)**: add multi-view
image_stack handling with view-pose metadata; feeds T7 phoxel splatting
branch. Same dtype-plus-operators pattern would extend the substrate
to a 7th modality.

**C — close stale promise P-01**: run IR audit on a 100+ image corpus
to start moving toward the charter's 10,000+ target. Stale since R47.

Lean toward **A then C**. Push first per anti-drift; then start
moving the long-stale corpus-scale promise.
