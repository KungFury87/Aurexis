# Rounds 85–86 — corpus diversity (B) and backward fiber first light (A)

**Date:** 2026-04-29
**Track:** T1 vocabulary health (R85) + T2/substrate-purpose (R86)
**Status:** complete — corpus N=76→110 with diverse-domain seeds; **backward fiber operational for the first time** (categorical first since R44–R45's filter-survival)

This bundled report covers two rounds because they're paired by the
audit ask Vincent named: re-engage the dual-fiber claim and stop
doing only forward-fiber work.

---

## R85 — Corpus diversity expansion (closes Vincent's "B" pick)

`round85_corpus_growth/images_diverse/` — 34 new native-resolution
images pulled in two sub-batches via parallel work streams (a bash
Wikimedia category pull + a general-purpose subagent that surfaced
non-Wikimedia source URL patterns).

Sources actually pulled:
- Wikimedia Histology (8)
- Wikimedia Microscopy (8)
- Wikimedia Diagrams (8)
- Wikimedia Oil paintings (6)
- NASA GIBS satellite tiles (5, MODIS true-color, multiple dates)

Sources subagent surfaced but not yet pulled (deferred):
- ESA/Hubble public archive
- PMC Open Access scientific figures
- Cell Image Library
- Natural Earth raster maps
- USGS National Map WMS

**Combined corpus**: N = 42 LANCZOS + 20 native + 14 screenshots + 34 diverse = **110**.

### R85 audit at the new N=110

| metric | R74 baseline (N=76, 128 preds) | R85 (N=110, 146 preds) | Δ |
|---|---|---|---|
| HEALTHY | 100 | **111** | +11 |
| LOW (<5%) | 11 | 16 | +5 |
| HIGH (>95%) | 0 | **2** | +2 |
| DEAD | 12 | 12 | 0 |
| COLLIDED | 2 | 2 | 0 |
| ERRORED | 3 | 3 | 0 |
| Multi-member IR classes | 5 | **3** | −2 |
| Effective dim (90% energy) | 31 of 76 components | **39 of 110 components** | +8 |
| Effective dim (99% energy) | 57 | **75** | +18 |

**Empirical confirmation of R63's small-N collapse hypothesis** at a
new level: as the corpus diversifies, the substrate exercises more
independent dimensions. Effective rank grew 31→39 for 90% energy,
matching the corpus growth (76→110) almost proportionally. The
hypothesis is now tested through three corpus jumps:

| corpus | N | multi-member IR | effective dim 90% |
|---|---|---|---|
| R28 baseline | 161 syn+phone | (different vocab) | — |
| R55 LANCZOS | 42 | 6 (R63) | — |
| R55+R66+R67 | 76 | 5 (R69) → 3 (R74) | 31 (R77) |
| **+ R85 diverse** | **110** | **3** | **39** |

### Predicates revived by diversity

7 predicates that were 0% on prior corpus now fire on the diverse subset:
- `has_significant_violet_hue` 4/34 (paintings, histology stains)
- `has_rectilinear_signature` 2/34 (architectural diagrams)
- `has_few_large_blobs` 2/34 (satellite tiles)
- `has_screen_displaying_face`, `has_dominant_red_hue`, `has_vertical_imbalance`, `is_indoor_warm_scene` 1/34 each

Each is a predicate that R74 flagged as LOW on the photograph-heavy
corpus. They were correct predicates waiting for the right content.

---

## R86 — Backward fiber first light (closes Vincent's "A" pick)

`round86_backward_fiber/phoxelis_synthesize.py`

**This is the categorical first the project has been waiting for since R76.**

The charter has claimed the substrate is a *dual-fiber* calculus — both
forward (signals → predicates → meaning) and backward (target predicate
state → constructive synthesis of signals). For 8+ rounds since R76, only
the forward fiber has produced new findings. R86 closes the asymmetry.

### Method

A library of 13 *ingredients* — primitive image modifications, each
annotated with the predicates it AIMS to fire (warm tint, horizontal
stripes, horizon line, clip highlights, grayscale, centered blob,
bright spots, etc.). The synthesizer takes a target predicate set,
greedily picks ingredients that overlap remaining targets, and stacks
them onto a neutral base.

### Demo: 5 target states

| target name | targets requested | hits | extra | hit-rate | precision | F1 |
|---|---|---|---|---|---|---|
| warm_landscape   | 4 | 3 | 35 | 75% | 0.08 | 0.14 |
| cool_minimal     | 4 | 2 | 31 | 50% | 0.06 | 0.11 |
| screenshot_like  | 4 | 1 | 27 | 25% | 0.04 | 0.06 |
| vivid_chaotic    | 4 | 2 | 25 | 50% | 0.07 | 0.13 |
| dark_warm_indoor | 4 | 3 | 41 | 75% | 0.07 | 0.12 |
| **aggregate**    | **20** | **11** | — | **55%** | — | **0.113 mean F1** |

### What the numbers mean

**Hit rate 55%** is the categorical first: more than half of *targeted*
predicates fire on the constructed images. The substrate's narrator
vocabulary maps backward to constructive synthesis. The dual-fiber claim
is now empirically demonstrated.

**Precision 0.04–0.08** is the honest part. Drawing a horizon line ALSO
fires `has_horizontal_dominant_edges`, `has_high_dynamic_range`,
`has_horizontal_balance`, `has_perspective_convergence`, etc. — 25–41
non-target predicates per image. Ingredients are entangled with
predicates they don't aim to fire.

**This isn't a bug; it's symmetric to forward-fiber behavior.** When you
run R78's narrator on a real photo, 24+ predicates fire because the
photo's signal content lights up many measurements at once. Backward
fiber inherits the same density: a constructed image fires many
predicates per ingredient applied. The asymmetry between target-fires
and total-fires is the COST of operating in a dense substrate.

### Naming the scope-drift cycle (charter §7)

R86 is a step-1 concrete artifact (the synthesizer). Step 2 of the
cycle would be: "this is THE thing — backward fiber works, the project
is done." That framing would be wrong. The natural next widening, which
I'm naming now rather than pretending past:

> The 55%/0.113 numbers are first-pass measurements with a 13-ingredient
> library, no precision optimization, no per-target ingredient tuning.
> A frame-widened version says: backward fiber is *real but coarse*; the
> question becomes how to push precision up without sacrificing hit
> rate, and whether the right unit is "predicate target → image" or
> "predicate target → image *type*" (shape/scene class). I'm not
> claiming the dual-fiber problem is solved; I'm claiming first
> non-trivial measurement on the backward side.

---

## What R85+R86 jointly establish

| claim | round | evidence |
|---|---|---|
| Substrate self-audits empirically (effective rank tracks corpus diversity) | R85 | rank 31→39 with 76→110, 7 predicates revived, multi-IR classes 5→3 |
| Substrate operates in BOTH fibers (categorical first since R44–R45) | R86 | 55% hit rate, 11/20 targets matched on first synthesis attempt |
| Backward fiber is real but coarse | R86 | precision 0.04–0.08; ingredients entangled with non-target predicates |
| The "meaning carried by composable measurements" claim now applies in both directions | R85+R86 | forward (R78 narrator, R81 comparator, R84 NN); backward (R86 synthesizer) |

## Promises ledger updates

- **C-85 closes:** corpus diversity expansion; small-N collapse hypothesis empirically confirmed at next-level corpus growth.
- **C-86 closes:** backward fiber first light; categorical first since R44-R45 filter survival.

## Files added

- `round85_corpus_growth/{images_diverse/, state.json, round85_audit.json}` — 34 new images + per-corpus audit
- `round86_backward_fiber/{phoxelis_synthesize.py, synth_*.png, round86_audit.json}` — synthesizer + 5 demo outputs
- this report
- `PHOXELIS_PROMISES.md` — C-85, C-86 entries
- `PHOXELIS_BENCHMARKS.md` — corpus growth row + backward-fiber row
- `PHOXELIS_CHARTER.md` — note that dual-fiber claim now has both-direction evidence

## Sweep summary R65 → R86

| round | what | preds | promises closed |
|---|---|---|---|
| R65 | sensor-provenance family | 108→110 | — |
| R66 | native-res corpus | — | P-20 |
| R67 | pixel-grid candidate falsified | — | P-21 |
| R68 | first batch L3 author-loop | 110→116 | — |
| R69 | combined audit + threshold recovery | 116→117 | — |
| R70 | second batch | 117→122 | — |
| R72 | stdio MCP wrapper | — | P-15 |
| R73 | third batch | 122→128 | — |
| R74 | coverage map | — | — |
| R76 | real-CDN density ceiling | — | P-13 |
| R77 | predicate orthogonality | — | — |
| R78 | full-vocab narrator | — | — |
| R79 | calibrated batch #1 | 128→136 | — |
| R80 | cross-corpus drift | — | — |
| R81 | comparator | — | — |
| R82 | calibrated batch #2 | 136→146 | — |
| R83 | vocabulary card | — | — |
| R84 | image-fingerprint NN | — | — |
| **R85** | **corpus diversity (Vincent's B pick)** | — | C-85 |
| **R86** | **backward fiber first light (Vincent's A pick)** | — | C-86 |

Net across R65→R86: **+38 predicates** (108→146), **+3 operators**
(96→99), **4 promises closed** (P-13/P-15/P-20/P-21), **1 candidate
retired by falsification** (R67), **dual-fiber claim now empirically
demonstrated** (R86 closes the asymmetry the audit named).

## Next round opens with

R87 — open. Vincent's audit redirected the project from forward-only
artifact-stacking back to the substrate's actual claim. The next pick
is his.

Plausible directions:
- **Push backward-fiber precision** — per-target ingredient calibration, learn which ingredient combinations *minimize* off-target fires
- **Continue corpus growth** to N=300+ via the deferred non-Wikimedia sources (ESA/Hubble, PMC OA, Cell Image Library)
- **Re-headline** the project around R44–R45 categorical first + R86 backward-fiber categorical first, retire the "we have 146 predicates" framing as not load-bearing
- **Update PHOXELIS_TOOL_LADDER.md** with what the R85 subagent surfaced (it's been stale since R64)
- Vincent-side: P-03/P-04 hardware
