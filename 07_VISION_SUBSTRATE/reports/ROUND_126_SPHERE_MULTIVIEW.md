# Round 126 — sphere multi-view test: stability generalizes across primitive shapes

**Date:** 2026-05-01
**Track:** T7 (Phase 2 second-step risk-cap)
**Status:** complete — phoxel sphere mean J **0.833** across 4 viewpoints (cube was 0.706); R124's result generalizes; sphere is *more* stable than cube because rotationally symmetric primitives produce rotationally symmetric fingerprints

---

## Why this round

R124 demonstrated multi-view fingerprint stability on a phoxel cube
under real 3D pinhole projection. The risk: that result was
cube-specific — flat faces and hard edges might create a particular
fingerprint geometry that doesn't generalize to other shapes. R126
runs the same 4-viewpoint test on a phoxel **sphere** (Fibonacci-spiral
surface sampling, normal-colored) and checks whether the substrate
fingerprint stays multi-view stable.

If sphere fails, the cube was special; Phase 2's viability claim is
conditional on shape. If sphere passes, R124 generalizes.

## Method

- `make_phoxel_sphere(radius=1.0, density=28)` → 784 phoxels via
  Fibonacci-spiral surface sampling
- Color-by-normal: each phoxel colored as `0.5 * (normal + 1)` so
  every direction shows distinctly
- 4 viewpoints (azimuth 0°/45°/90°/135°, fixed elevation 0.6, distance 3.5)
- Same renderer + substrate eval pipeline as R124 (reuses
  `r124_phoxel_renderer.py` functions)

## Results

```
view             pixels rendered    n_fired (of 151)
az=0             ~21%               38
az=45            ~22%               37
az=90            ~22%               36
az=135           ~22%               35
```

Pairwise Jaccards on the same sphere across the 4 views:

```
J(az=0,   az=45)  = 0.829
J(az=0,   az=90)  = 0.850
J(az=0,   az=135) = 0.780
J(az=45,  az=90)  = 0.921
J(az=45,  az=135) = 0.800
J(az=90,  az=135) = 0.821
```

```
metric                          R100 (2D affine)    R124 (cube 3D)    R126 (sphere 3D)
mean J                          0.758               0.706             0.833
min J                           0.391               0.565             0.780
max J                           1.000               0.821             0.921
```

**Sphere is MORE multi-view stable than cube** by a substantial
margin (mean J 0.833 vs 0.706). This is structurally sensible: a
normal-colored sphere is rotationally symmetric around its z-axis —
silhouette + color-gradient distribution are isomorphic under
rotation. The cube has hard edges that produce viewpoint-specific
silhouettes (square at az=0, diamond at az=45, etc.) and complete
face occlusion between az=0 and az=135 (red+blue+magenta visible at
0; green+yellow+cyan visible at 135).

The substrate fingerprint correctly captures this: smooth-symmetric
shape produces smooth-similar fingerprints; angular-asymmetric shape
produces fingerprints with more viewpoint-specific structure. Both
pass the viability threshold (J ≥ 0.65 mean).

## What this round means for Phase 2

R124 claimed real-3D-projection viability; R126 confirms the claim
is **shape-independent** in the right way:

| primitive | viewpoint stability | physical interpretation |
|---|---|---|
| sphere (rotationally symmetric, color-by-normal) | very high (0.833) | substrate correctly sees rotational invariance |
| cube (axis-aligned, color-by-face) | viable (0.706) | substrate correctly sees viewpoint-specific occlusion |
| natural scene (R100, 2D affine proxy) | high (0.758) | proxy was between the two extremes |

Phase 2's "substrate fingerprint as differentiable rendering loss"
claim now has stability evidence on:
- **Symmetric primitives** (sphere) — gradient signal would be smooth
- **Asymmetric primitives** (cube) — gradient signal would have
  view-specific structure (the right shape for occlusion-sensitive
  training)
- **Real 2D images under affine viewpoint proxy** (R100)

That's a respectably broad evidence base. Phase 2 is on real ground.

## Honest caveats

- **Sphere is too easy** in some sense. Rotational symmetry means
  any rotation preserves the silhouette. A real Phase 2 test should
  include shapes that DON'T have this symmetry (a phoxel pyramid,
  asymmetric letter, etc.) to confirm intermediate-stability cases.
- **R126 reuses R124's renderer.** A more rigorous validation
  would use an independent renderer (e.g., 3D-Gaussian-style splat
  with proper alpha) to confirm the result isn't an artifact of
  the painter's-algorithm renderer.
- **No occlusion test of complex scenes.** Two phoxel objects
  partially occluding each other across viewpoints would be
  closer to real rendering use; that's a future round.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| **T7 Phase 2 generalization: sphere multi-view stability** | R126 | mean J **0.833** across 4 viewpoints (R124 cube was 0.706); min 0.780 (max-azimuth-gap), max 0.921 (adjacent) | current — substrate fingerprint stability is shape-independent in the right way; rotationally symmetric primitives produce more stable fingerprints, asymmetric ones produce view-specific structure |

## Promises ledger updates

- **C-126 closes:** R124 generalization confirmed. Sphere multi-view
  test PASSES with higher stability than cube (rotational symmetry
  → rotational fingerprint symmetry, as physics predicts).

## Files added this round

- `round126_sphere_test/r126_sphere_test.py`
- `round126_sphere_test/round126_audit.json`
- `round126_sphere_test/sphere_az{000,045,090,135}.png`
- this report
- `PHOXELIS_PROMISES.md` — C-126 entry
- `PHOXELIS_BENCHMARKS.md` — R126 row

## Next round opens with

R127 candidates:

**A — push R125 + R126.** Already have R125's push.bat staged
(covers R111-R124); extend to include R126.

**B — multi-object scene** (e.g., cube + sphere in same field, both
visible). Tests fingerprint stability under inter-object occlusion.

**C — start the differentiable variant.** This is Phase 3 — the actual
training loop where phoxel positions/colors get gradients from
substrate-fingerprint loss. Multi-round arc.

**D — asymmetric primitive test.** A phoxel pyramid or letter would
fall between sphere and cube on the symmetry axis; useful additional
data point.

Lean **A then B**. Multi-object is the natural next-easiest step.
Asymmetric primitive (D) and differentiable training (C) come after.
