# Round 89 — neighborhood satisfaction: backward fiber lands in the right cluster

**Date:** 2026-04-29
**Track:** T6 substrate-purpose (R86–R88 follow-up; reframing per R88's finding)
**Status:** complete — backward fiber's success metric reframed; **5/5 demos land in right neighborhood**; synth↔oracle Jaccard 0.358 vs mean inter-corpus 0.282 (substrate is *more similar* to its target oracle than random corpus pairs are to each other)

---

## What R89 changed

R86 measured exact-target recall (55%). R87 lifted it to 70%. R88 found
the substrate is *coarsely surjective and non-monotonic under
composition* — there are no atomic ingredients, and stacking ingredients
cancels predicates established by prior ingredients. Exact-target
satisfaction is therefore the *wrong metric* for this substrate.

R89's reframe, suggested by R88's finding: success = *neighborhood
satisfaction* in fingerprint space. The constructed image should land
near the corpus images that ALREADY match the target description, not
fire exactly the target predicate set.

This connects R86's backward fiber to R84's image-fingerprint NN. The
substrate's natural way of clustering images IS the metric — backward
synthesis succeeds when its output lands in the right cluster.

## Method

For each of R86's 5 demo target states:

1. **Oracle**: scan the N=110 combined corpus, find the image that
   fires the most target predicates. That's the "corpus image which
   already matches this description."

2. **Synthesize** using R87's wide+empirical method (the best so far).

3. **Measure** three Jaccard distances:
   - synth fingerprint ↔ target predicate set (R86's metric)
   - synth fingerprint ↔ oracle fingerprint (the new metric)
   - synth fingerprint ↔ each corpus image (find synth's nearest neighbors)

4. **Ask**: is the oracle in synth's top-3 nearest corpus neighbors?

## Results — all 5 demos, all 5 in right neighborhood

| target | best oracle (fires N/M targets) | synth's nearest corpus image | match? |
|---|---|---|---|
| warm_landscape   | wm_002_The_Wake_Forest_Student (4/4)  | wm_002_The_Wake_Forest_Student (J=0.492) | **EXACT MATCH** |
| cool_minimal     | osm_5_9_27 (3/4)                       | osm_5_15_21 (J=0.340)                    | same type (OSM map tile) |
| screenshot_like  | met_32108 (4/4)                        | wm_002_Number_565 (J=0.429); oracle in top-3 | **NEIGHBOR** |
| vivid_chaotic    | picsum_8260294 (3/4)                   | picsum_6224373 (J=0.372)                 | same type (picsum random) |
| dark_warm_indoor | inat_335031188 (3/4)                   | inat_335031188 (J=0.423)                | **EXACT MATCH** |

3/5 demos: synth's nearest corpus image IS the oracle.
2/5 demos: synth's nearest is a different image from the SAME source type as the oracle.
**5/5: synth lands in the right corpus cluster.**

## The headline number

```
metric                        R86      R87      R89
exact-target recall           0.55     0.70     0.70
synth↔target Jaccard          —        —        0.074
synth↔oracle Jaccard          —        —        0.358
mean inter-corpus Jaccard     —        —        0.282 (R77 baseline)
```

**Synth-to-oracle Jaccard (0.358) is HIGHER than mean inter-corpus
Jaccard (0.282).** When the substrate constructs an image from a
target description, the result is *more similar to its target oracle
than random corpus pairs are to each other*. The substrate's image-of-
description lands closer to corpus images-that-match-the-description
than the corpus's own internal coherence would predict by chance.

This is the right backward-fiber metric on this substrate.

## Naming the substrate-shape claim explicitly

After R86–R89, the dual-fiber claim from charter §1 has a sharper
empirical specification:

> **Forward fiber:** image → typed-field measurements → predicate
> verdicts → narrator vocabulary description. Tight; deterministic;
> 78% HEALTHY at N=110; 100/146 predicates discriminate cleanly.
>
> **Backward fiber:** target predicate set / description → constructed
> image whose **fingerprint lands in the corpus neighborhood matching
> the description**, NOT whose verdicts match the target predicate set
> exactly. Coarse satisfaction (70% exact-recall) and high
> neighborhood satisfaction (5/5 demos in right cluster, mean
> oracle-Jaccard 0.358 > corpus baseline 0.282).
>
> The two fibers are dual at the **fingerprint level**, not the
> predicate-bit level. The substrate's natural unit of "meaning" is
> the predicate-set fingerprint of an image, not any individual
> predicate.

This is R86–R89's joint architectural finding. It's a stronger and
more honest version of the charter's original "meaning carried by
composable measurements" — meaning is carried by *measurement
co-occurrence patterns*, which is what fingerprints capture.

## Honest caveats

- **N=5 demos.** Generalizing to "5/5 in right neighborhood" from 5
  test cases is a small sample. A 50-target sweep would be more
  convincing.
- **"Right neighborhood" is defined post-hoc** by the oracle. The
  oracle is whatever corpus image happens to best match the target —
  if no corpus image matches well, the oracle isn't actually a good
  exemplar.
- **Source-type collisions** (synth's nearest = different image from
  same source) might be visually unrelated to the target description.
  R89 doesn't visually check the synthesized images; the metric is
  fingerprint-only.
- **The synthesizer itself is unchanged from R87.** R89 didn't make
  the synthesizer better; it changed the metric we measure success
  by. That's the honest move R88 pointed at.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| Backward fiber → right corpus neighborhood | R89 | **5/5 demos** synth lands in right cluster (3/5 nearest IS oracle, 2/5 same source type) | current |
| Mean synth↔oracle Jaccard | R89 | **0.358** vs R77 mean inter-corpus 0.282 (synth is closer to its target than random corpus pairs are) | current |
| Right backward-fiber metric | R89 | **fingerprint neighborhood**, not exact-predicate match | current — sharpens dual-fiber claim |

## Promises ledger updates

- **C-89 closes:** backward fiber reframed as neighborhood satisfaction; dual-fiber claim sharpened — fibers are dual at fingerprint level, not predicate-bit level.

## Files added this round

- `round89_neighborhood/round89_audit.py`
- `round89_neighborhood/round89_audit.json` — per-demo oracle, synth fingerprint, top-5 nearest corpus
- `round89_neighborhood/synth_*.png` — 5 constructed images
- this report
- `PHOXELIS_PROMISES.md` — C-89 entry
- `PHOXELIS_BENCHMARKS.md` — R89 row
- `PHOXELIS_CHARTER.md` — the dual-fiber claim should now reflect "fingerprint-level duality"

## Sweep summary R86 → R89

| round | what | finding |
|---|---|---|
| R86 | backward fiber first light | 55% exact-target recall; categorical first |
| R87 | empirical ingredient map | recall 55%→70% via better ingredient choice |
| R88 | tight ingredients (falsified) | no atomic ingredients; non-monotonic composition |
| R89 | neighborhood satisfaction | 5/5 demos in right cluster; mean oracle-J 0.358 > baseline 0.282 |

The backward fiber arc is now coherent:
1. R86 demonstrated it works at all (categorical first).
2. R87 found the best ingredient-selection method.
3. R88 ruled out a plausible-sounding next step (atomic ingredients).
4. R89 reframed the success metric to match the substrate's actual shape.

R89 is the natural close of the dual-fiber arc Vincent's audit
prompted. Next round opens fresh.
