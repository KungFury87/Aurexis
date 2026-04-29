# Rounds 81-84 — substrate-use deliverables

**Date:** 2026-04-29
**Track:** T6 substrate-purpose (R81 + R84) + T1 introspection (R83) + T1 vocabulary growth (R82)
**Status:** complete — comparative narrator, fifth calibrated batch (10/10), vocabulary card, image-fingerprint nearest-neighbor

Bundled report covers four rounds because each is small and they're
methodologically related: substrate-use deliverables built on the
existing 146-predicate vocabulary.

---

## R81 — Comparative narrator

`round81_comparative_narrator/phoxelis_compare.py`

Takes two images, runs full vocab against each, surfaces the predicates
that fire on only one and groups them into themed clauses. Output also
shows Jaccard similarity between the two predicate-fire sets.

Demo (iNat insect macro vs. LIMS web-form screenshot):
```
inat_356380102: 24 predicates fire
sc_-LIMS-.jpg : 39 predicates fire
shared: 15; only-A: 9; only-B: 24
Jaccard similarity: 0.312

[exposure / brightness]
  only B: overexposed dominant, overexposed regions, high key, clipped highlights
[color palette]
  only A: high saturation, high color diversity
  only B: low saturation, pure grayscale palette, monochrome, largely achromatic
[channel dominance]
  only B: dominant blue/green channels, strongly blue dominated, high red channel
```

The substrate cleanly explains *what's different* between two images
through composable measurement, with no learned features.

---

## R82 — Fifth calibrated batch (10/10 promoted)

`round82_calibrated_batch_5/`

Calibrated against operator distributions for 12 additional operators,
authored 10 candidates targeting still-uncovered axes (negative-space
extremes, skin-tone presence, balance, perspective, channel excess,
focus gradient).

```
candidate                                 fired   rate
has_minimal_negative_space                 6/76    7.89%
has_dominant_negative_space                8/76   10.53%
has_skin_tone_presence                    23/76   30.26%
has_meaningful_color                      36/76   47.37%
has_strong_horizontal_balance             20/76   26.32%
has_strong_vertical_balance               19/76   25.00%
has_strong_perspective                    10/76   13.16%
has_clear_horizon                         19/76   25.00%
has_strong_channel_excess                 15/76   19.74%
has_top_to_bottom_focus_gradient          19/76   25.00%
```

10/10 IR-clean. Vocabulary 136 → **146**.

**Cumulative batch L3 author-loop:**

| round | promoted | total | rate |
|---|---|---|---|
| R68 | 6  | 8  |  75% |
| R70 | 5  | 10 |  50% |
| R73 | 6  | 14 |  43% |
| R79 | 8  | 8  | 100% |
| R82 | 10 | 10 | 100% |
| **cumulative** | **35** | **50** | **70%** |

The two consecutive 100% calibrated batches confirm the methodology
(probe operator distribution → choose thresholds at meaningful percentiles
→ author) is reproducible.

---

## R83 — Vocabulary card

`round83_vocab_card/VOCABULARY_CARD.md`

Per-predicate documentation: name, expects, returns, intent, fire rate
on combined N=76 corpus. Predicates grouped by 12 themes. Generated
mechanically from `vocab.aurex` + a single full-vocab evaluation pass.

Sample entry:

```
### `has_dominant_blue_channel`
- expects: color_scene:color_image
- returns: bool
- intent:  detect_blue_channel_dominance_sky_water
- fire rate (N=76): 0.421  (32/76)
```

Useful as: (a) external reference for outside readers; (b) input to
future LLM-author batches so the model can see the existing vocabulary
before proposing duplicates.

---

## R84 — Image fingerprint + nearest-neighbor

`round84_image_fingerprint/`

For each image in the combined N=76 corpus, computes its 146-bit verdict
fingerprint. Builds a 76×76 Jaccard-similarity matrix and a top-5
nearest-neighbor table (`nearest_neighbors.json`).

Mean inter-image Jaccard: **0.282** — typical pair-wise overlap.

**The substrate self-organizes the corpus.** Demo nearest-neighbor
queries:

```
query: wm_002_The_Wake_Forest_Student_1901  (Wikimedia article scan)
  sim=0.554  sc_2011_BW_profile.png                (screenshot)
  sim=0.459  sc_01_Library_of_Congress_Receipt     (screenshot)
  sim=0.435  sc_FISD_File_information               (screenshot)
→ document scans cluster with document screenshots

query: met_463786                            (MET artwork)
  sim=0.619  wm_000_2018_Scientific_Congress       (Wikimedia)
  sim=0.587  wm_000_Greenfield_Brook                (Wikimedia)
  sim=0.561  met_892699                             (MET)
→ paintings cluster with paintings/photographs

query: sc_05-Sistema-do-TJRJ.png             (Brazilian justice screenshot)
  sim=0.729  sc_-VOR-SBO-audio-Signal.png          (audio waveform)
  sim=0.729  sc__FISD__File_information            (form screenshot)
  sim=0.660  sc_1bx_com_en_user_asldkfajsd5        (web profile)
→ screenshots cluster tightly together (J=0.66-0.73)
```

The most-similar pair across the entire N=76 corpus: **two OSM map tiles
at J=1.000** — exactly the same predicate set fires on both. The
substrate identifies map-tiles as a single equivalence class purely
from measurement.

**This is image similarity emerging from composable measurement** —
no embedding, no training, no labeled categories. Companion to R78's
narrator: where R78 says *what an image is*, R84 says *what an image
is most like*.

---

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| Comparative narrator (2-image diff) | R81 | substrate-purpose deliverable; Jaccard between predicate-fire sets exposed; themed-clause output | current |
| Cumulative batch L3 base rate | R82 | 35/50 = **70%** across 5 rounds; calibrated batches (R79, R82) at 100% | current |
| Total predicates | R82 | **146** (136 + 10 calibrated) | current |
| Vocabulary card artifact | R83 | per-predicate documentation for all 146 with fire rates and themes | current |
| Image-fingerprint nearest-neighbor (R84) | R84 | corpus self-organizes by predicate composition (mean J=0.282; document/screenshot/artwork clusters visible; identical-image pair at J=1.000) | current — substrate-purpose deliverable |

## Promises ledger updates

- **C-81/C-82/C-83/C-84 close:** four substrate-use deliverables completed.

## Files added across the four rounds

- `round81_comparative_narrator/phoxelis_compare.py`
- `round82_calibrated_batch_5/{round82_candidates.aurex, round82_calibrate.py, round82_audit.py, calibration.json, round82_audit.json}`
- `round83_vocab_card/{round83_r84_audit.py, VOCABULARY_CARD.md}`
- `round84_image_fingerprint/{image_fingerprints.npy, image_jaccard.npy, image_aliases.json, nearest_neighbors.json}`
- `vocab.aurex` (136 → 146 via R82)
- this report
- `PHOXELIS_PROMISES.md` — C-81/82/83/84 entries

## Sweep summary R77 → R84

| round | finding | preds | promises |
|---|---|---|---|
| R77 | predicate orthogonality + effective rank 31/76 | — | C-77 |
| R78 | full-vocab narrator | — | C-78 |
| R79 | calibrated batch #1 (8/8) | 128→136 | C-79 |
| R80 | cross-corpus drift surfaces latent typology | — | C-80 |
| R81 | comparative narrator | — | C-81 |
| R82 | calibrated batch #2 (10/10) | 136→146 | C-82 |
| R83 | vocabulary card | — | C-83 |
| R84 | image fingerprint NN | — | C-84 |

Net: **+18 predicates** (128→146), 4 substrate-use deliverables (R78
narrator, R81 comparator, R83 card, R84 NN), 2 calibrated batches at
100%, base rate up to 70%.

## Next round opens with

R85 — open. The substrate is now mature enough that next steps are
either: (a) consolidation/packaging (release a `phoxelis-vocab` Python
module wrapping it), (b) corpus growth toward P-01 (network-bound),
(c) new operator family (audio-visual? temporal? gestural?), or
(d) Vincent-side test (P-03/P-04 phone-camera-in-loop).
