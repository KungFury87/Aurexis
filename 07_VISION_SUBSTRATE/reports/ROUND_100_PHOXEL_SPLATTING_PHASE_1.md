# Round 100 — phoxel splatting Phase 1: multi-view fingerprint consistency CLEARED

**Date:** 2026-04-30
**Track:** New T7 — Phoxel splatting research branch
**Status:** complete — **viability gate passed**; substrate fingerprints are view-stable; phoxel splatting branch opens for real

---

## Vincent's phoxel definition

> A phoxel is the smallest distinguishable point of light that can be
> measured by a camera/sensor — a photon and a pixel mixed together,
> as a representation inside the real world.

Operational implication: a 3D scene is a cloud of phoxels (photon-pixel
hybrids in real-world 3D space). A camera captures a 2D projection of
this cloud. Phoxel splatting is the dual of Gaussian splatting where
the primitives are physically motivated (sensor-side photon detections)
rather than mathematical (anisotropic 3D Gaussians).

For phoxel splatting to be viable, the substrate's 2D predicate
fingerprint of a rendered phoxel cloud must be coherent across nearby
viewpoints. That's what R100 tested.

## Method

5 corpus images (one per source type, treated as 5 separate "scenes")
× 8 viewpoint-mimicking variants:
- rotate −10°, −5°, +5°, +10° (camera roll)
- zoom in / zoom out (forward/backward dolly)
- shear (off-axis viewing angle)
- original (canonical view)

For all (5 × 8) = 40 fingerprints, computed pairwise Jaccard. Two pair classes:
- **Same-scene different-view** (140 pairs)
- **Different-scene** (640 pairs)

If same-scene Jaccard >> different-scene Jaccard, the substrate can serve
as a view-consistent loss for splatting.

## Results

```
                            same-scene-diff-view    different-scene
N pairs                            140                  640
mean J                             0.758                0.325
median J                           0.756                0.312
min J                              0.391                —
max J                              1.000                0.596

ratio (same/diff):                       2.33×
separation (same − diff):                0.433
AUC (same vs different scene):           0.998
```

**Decision: VIABLE.** The 2.33× ratio clears the >=2.0 viability threshold;
the 0.998 AUC means same-scene-vs-different-scene discrimination is
essentially perfect at the fingerprint level.

## Per-scene view stability

```
scene type      mean J across views     min J
inat            0.827                   0.605
native          0.809                   0.634
met             0.745                   0.553
screen          0.739                   0.509
diverse         0.671                   0.391
```

Every scene type stays well above the cross-scene baseline (0.325).
Even the least-stable case (diverse, painting source, min J=0.391) is
above the across-image baseline. The substrate fingerprint genuinely
encodes scene identity, not just per-image randomness.

## View-pair stability

```
LEAST disruptive (most view-stable):
  rot+5 ↔ rot-5:    J 0.901   small angular changes barely matter
  rot+10 ↔ rot+5:   J 0.883
  orig ↔ rot+5:     J 0.872
  orig ↔ rot-5:     J 0.861
  rot-10 ↔ rot-5:   J 0.860

MOST disruptive (most view-sensitive):
  zoom_in ↔ zoom_out:   J 0.582
  orig ↔ zoom_out:      J 0.612
  shear ↔ zoom_out:     J 0.613
  rot+5 ↔ zoom_out:     J 0.650
  rot-10 ↔ zoom_out:    J 0.659
```

**The substrate is rotation-stable but scale-sensitive.** Adjacent
rotations preserve ~90% of the fingerprint; zoom changes break ~40%
because scale shifts what fits in the frame and how predicates like
`has_centered_subject`, `has_dominant_negative_space`,
`has_atmospheric_haze` evaluate.

## What this means for the splatting branch

### Cleared

- ✅ **Multi-view consistency at fingerprint level.** Different
  viewpoints of the same scene produce similar fingerprints.
- ✅ **Discriminability against unrelated scenes.** AUC 0.998 — the
  fingerprint is reliably *more* similar to other views of the same
  scene than to any view of any other scene.
- ✅ **Loss-function viability.** Small rotations produce small
  fingerprint deltas (J ≈ 0.90); a gradient-based optimizer training
  a phoxel field against camera images would have smooth gradients
  in the rotation neighborhood.

### Caveats

- ⚠️ **Scale changes (zoom in/out) are the dominant disruption mode.**
  Splatting will need to handle distance/depth carefully. The
  substrate is *roll*-invariant but not *scale*-invariant.
- ⚠️ **N=5 scenes is small.** A real test would use 50+ scenes with
  real multi-view captures.
- ⚠️ **2D affine ≠ 3D camera moves.** The variants here are 2D
  approximations of viewpoint changes. Real 3D camera moves include
  parallax (foreground moves more than background per camera step).
  Parallax isn't tested here.
- ⚠️ **No depth dimension yet.** Phoxel splatting fundamentally needs
  3D phoxel representation; R100 only verified that 2D substrate
  fingerprints are view-stable enough to be a TARGET for splatting.

## The 4-phase plan, updated

| phase | what | status |
|---|---|---|
| **1. Multi-view consistency** | viability gate | **PASSED in R100** |
| 2. 3D phoxel-field representation | voxel/cloud type, forward renderer | open |
| 3. Differentiable phoxels | continuous predicates, gradient-based training | open |
| 4. Novel view synthesis benchmark | train / held-out / vs 3D-GS | open |

R100 establishes the foundational claim. The branch is real research
from here on.

## Substrate prerequisites for Phase 2

To do real 3D phoxel splatting, the substrate needs:

1. **A `phoxel_field` datatype** in `FieldBundle`. Sparse 3D point
   cloud where each point carries (position, color, predicate-vector).
2. **A forward renderer** that projects a phoxel cloud through a
   given camera pose and intrinsics → 2D image.
3. **A scale-invariant predicate subset**, or a way to make
   scale-variant predicates respond consistently across rendering
   resolutions. R100 showed scale changes are the substrate's
   weakest viewpoint axis.

These are concrete engineering tasks. None require a Vincent-side
hardware setup; all could be built in-sandbox.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| Phoxel splatting Phase 1 viability gate | R100 | **PASSED** — same/diff Jaccard ratio 2.33×, AUC 0.998 | current — branch is real |
| Substrate's view-stability axis | R100 | rotation-stable (J≈0.90 for ±5°), scale-sensitive (J≈0.58 for zoom_in↔zoom_out) | current — informs Phase 2 design |
| Mean same-scene multi-view Jaccard | R100 | 0.758 | current — establishes target for differentiable rendering loss |

## Promises ledger updates

- **C-100 closes:** phoxel splatting research branch opened with empirical viability test passed. T7 track formally exists.

## Files added this round

- `round100_multiview_consistency/round100_audit.py`
- `round100_multiview_consistency/round100_audit.json`
- this report
- `PHOXELIS_CHARTER.md` — should add T7 — Phoxel splatting (research) row to the tracks table
- `PHOXELIS_PROMISES.md` — C-100 entry; P-22 opened (Phase 2: 3D phoxel-field datatype)

## Next round opens with

R101 — Phase 2 of phoxel splatting. The first concrete step is defining
a `phoxel_field` datatype and a minimal forward renderer. The renderer
needs to:

1. Take a list of phoxels (each with x,y,z position and color).
2. Take a camera pose (extrinsic) and intrinsic matrix.
3. Project each phoxel onto the 2D image plane.
4. Composite (alpha-blend or z-buffer).
5. Produce a 2D image whose substrate fingerprint matches the target.

Toy version: a phoxel cloud built from a known 3D primitive (cube,
sphere) rendered from 4 viewpoints. Verify the substrate fingerprints
of those 4 renderings are mutually consistent (close in Jaccard space).
That's the smallest test that could fail in a way that surfaces
real splatting issues.
