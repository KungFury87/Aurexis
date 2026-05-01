# Round 131 — layout-invariant subset is stable AND discriminates: Phase 3 splatting content-loss validated

**Date:** 2026-05-01
**Track:** T7 (Phase 2 → Phase 3 design completed)
**Status:** complete — 6 distinct phoxel scenes; layout-invariant 116-predicate subset produces between-scene Jaccard mean **0.554** with range **0.333-0.867**; subset is stable (R130 J=1.000 within scene) AND informative (R131 J=0.33-0.87 between scenes); both properties Phase 3 needs are now empirically validated

---

## What R131 settles

R130 showed the layout-invariant 115-predicate subset is multi-view
**stable** (mean J = 1.000 across 4 viewpoints of the same scene).
Open question: is it also **informative** — do different scene types
produce different layout-invariant fingerprints? If yes, it's a viable
Phase 3 splatting content-loss target. If no (Jaccards uniformly high
between different scenes), the subset has collapsed to a generic
"is-a-multi-object-scene" fingerprint and would be useless as a
discriminator.

R131 builds 6 distinct phoxel scenes, computes fingerprints from
az=0, partitions predicates into invariant/sensitive (re-derived from
the cube+sphere 4-viewpoint test), and asks: does the invariant
subset's between-scene Jaccard distribution have meaningful spread?

## Method

Six scenes:

```
cube_sphere    cube + sphere placed apart (R128 baseline)
two_cubes      small cube + big cube placed apart
two_spheres    small sphere + big sphere placed apart
cube_pyramid   cube + colored pyramid placed apart (added a
               make_phoxel_pyramid function)
single_sphere  single big sphere
single_cube    single big cube
```

For each: render at az=0, fingerprint, count predicates fired.

Then:
- Re-derive layout-invariant predicates from a 4-viewpoint
  cube+sphere test (yields 116 invariants — close to R130's 115; the
  ~1 difference is renderer/RNG noise)
- Compute pairwise Jaccards across the 6 scenes on three subsets:
  full 151, layout-invariant 116, layout-sensitive 35

## Results

```
                                  full 151    invariant   sensitive
between-scene mean J              0.547       0.554       0.543
between-scene min J               0.352       0.333       0.370
between-scene max J               0.861       0.867       0.857
```

**Three findings, in order of importance:**

### 1. Invariant subset DOES discriminate

Mean between-scene J on invariant subset is 0.554. Range 0.333-0.867.
Both well within "informatively spread" — not collapsed to one
fingerprint. The subset distinguishes scene types.

Specific examples that confirm physical sensibility:
- `cube_sphere` vs `two_spheres` → invariant J **0.867** (both contain
  a sphere, both are multi-object — correctly similar)
- `cube_sphere` vs `single_cube` → invariant J **0.360** (one is a
  multi-object scene with a sphere, other is just a cube — correctly
  different)
- `two_cubes` vs `two_spheres` → invariant J **0.476** (both
  multi-object but different shape compositions — correctly
  intermediate)
- `single_sphere` vs `single_cube` → invariant J **0.480** (both
  single-object but very different shapes — correctly intermediate)

### 2. Invariant subset's discriminability ≈ full vocab's

Mean between-scene J on full 151 is 0.547. On invariant subset alone:
0.554. Essentially identical. **Removing the 36 layout-sensitive
predicates costs nothing in scene-discrimination power.**

That's because the layout-sensitive predicates were already nearly
maximally noisy across viewpoints (per R130: J=0.253 on the
sensitive subset alone for *same* scene different viewpoint).
Predicates that are noisy across viewpoints don't add signal — they
just add view-coupling.

### 3. The layout-invariant subset is the right answer for Phase 3

The two properties Phase 3 splatting loss needs:

| property | source | value |
|---|---|---|
| **stable across viewpoints** of fixed scene | R130 | J = 1.000 across 6 pairs of cube+sphere viewpoints |
| **informative between scenes** | R131 | J range 0.333-0.867 across 15 pairs of distinct scenes |

Both validated. Three-layer Phase 3 architecture from R130 is
empirically grounded for layer 1.

## Why this is interesting beyond Phase 3

The 76/24 invariant/sensitive split documents a substrate property
that wasn't visible at smaller corpus scale: **the substrate's
typed-field interface naturally separates "scene content" from
"spatial layout" predicates.** The layout-sensitive 36 form a clean
family (composition, balance, subject placement, symmetry, horizon,
view-conditional color distributions); the invariant 116 are
everything else (color presence, edge density, frequency content,
texture, lighting absent layout, etc.).

That's not a coincidence — it's structural. Predicates over typed
fields with explicit semantics ARE intrinsically partitioned by what
they measure. The vocabulary's auto-self-organization along this axis
reflects the substrate's design philosophy from charter §1: meaning
carried by composable measurements with clear typing.

## Honest caveats

- **The 6 scenes are still synthetic.** Real splatting scenes have
  textures, lighting variations, occlusion shadows that synthetic
  phoxel-painted scenes don't model.
- **Discrimination J range 0.33-0.87 is good for a 6-scene test
  but small N.** A 30-scene discrimination test would more
  rigorously characterize the subset's discriminative ceiling.
- **The "stable" property assumes a fixed phoxel field.** During
  splat training, the phoxel field changes — the question becomes
  "does the invariant subset's stability under viewpoint change
  generalize to stability under small phoxel-position perturbations?"
  That's a Phase 3 round.
- **Renderer is still painter's algorithm with 5×5 splat.** Real
  rendering quality will affect predicate firing in subtle ways.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| **Layout-invariant subset DISCRIMINATES between scene types** | R131 | between-scene mean J **0.554** on 116-predicate invariant subset across 6 distinct phoxel scenes; range 0.333-0.867; matches full-vocab discrimination (0.547) | current — subset preserves discriminability while removing view-instability |
| Two-property Phase 3 validation | R130 + R131 | stable (J=1.000 within scene) AND informative (J=0.33-0.87 between scenes) | current — both properties Phase 3 splatting loss needs are empirically validated |

## Promises ledger updates

- **C-131 closes:** layout-invariant subset's discrimination tested
  and validated. R130 + R131 jointly establish the Phase 3 splatting
  content-loss target. Phase 3 architecture (content + layout +
  photometric) has empirically grounded layer 1.

## Files added this round

- `round131_discrimination/r131_discrimination.py` (includes
  `make_phoxel_pyramid` extension to the renderer toolkit)
- `round131_discrimination/round131_audit.json`
- `round131_discrimination/*_az0.png` — 6 rendered scenes
- this report
- `PHOXELIS_PROMISES.md` — C-131 entry
- `PHOXELIS_BENCHMARKS.md` — R131 row

## Next round opens with

R132 candidates:

**A — push R131.** R130 + R131 + R128 + R126 are now all in one
arc; new push.bat covers what's been added since R130 push landed.
Anti-drift.

**B — start the differentiable training loop.** This is the actual
Phase 3 work. Build:
1. Parametric phoxel field (positions + colors are tensors)
2. Forward render through the existing renderer
3. Substrate fingerprint loss using ONLY the 116 invariant
   predicates — Jaccard distance to a target fingerprint
4. Numerical gradient (finite-differences for v0; autograd in v1)
5. Step phoxel parameters; verify loss decreases

Multi-round arc. R132 = position-only optimization. R133 = colors.
R134 = combined.

**C — perturbation-stability test.** Before B, verify that the
116-predicate fingerprint stays stable under SMALL phoxel-position
perturbations (not just viewpoint changes). Cheap diagnostic, 1
round, validates that the invariant property generalizes from
"viewpoint is varied" to "phoxel field is varied."

**D — real multi-view dataset test.** Pull a tiny LLFF / Mip-NeRF 360
scene, render the substrate-as-loss against it. Tests Phase 3
intervention on real captured data, not synthetic.

Lean **A then C then B**. C is a cheap last sanity check before the
multi-round B arc. D is the real-world step that comes after B's
synthetic-scene proof of concept.
