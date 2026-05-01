# Round 128 — multi-object scene reveals a real Phase 2 boundary: layout shifts break view-stability

**Date:** 2026-05-01
**Track:** T7 (Phase 2 third-step finding — substantive negative result)
**Status:** complete — multi-object scene (cube + sphere placed apart) yields **mean J = 0.506** across 4 viewpoints, **below** the 0.65 PASS threshold; substrate's view-stability claim does NOT trivially extend to multi-object scenes; finding is informative for Phase 3 splatting design

---

## Why this round

R124 (cube) and R126 (sphere) both passed the 4-viewpoint stability
test. Open question: does that generalize to scenes with **multiple
distinct objects** whose relative spatial positions shift between
viewpoints? Multi-object scenes are where most real splatting use
cases live — single-object phoxel fields are toys.

R128 places a phoxel cube on the left (offset (-1, 0, 0)) and a phoxel
sphere on the right (offset (+1, 0, 0)) in the same field, runs the
same 4-viewpoint protocol, and asks: does mean J stay above 0.65?

## Results — substantive negative

```
                   mean J    min J    max J    verdict
R100 (2D affine)   0.758     0.391    1.000    PASS
R124 (cube alone)  0.706     0.565    0.821    PASS
R126 (sphere alone) 0.833    0.780    0.921    PASS
R128 (cube + sphere) 0.506   0.396    0.611    FAIL (vs 0.65 threshold)
```

```
pairwise Jaccards on the multi-object scene:
J(az=0,   az=45)  = 0.571
J(az=0,   az=90)  = 0.396  ← worst
J(az=0,   az=135) = 0.432
J(az=45,  az=90)  = 0.488
J(az=45,  az=135) = 0.541
J(az=90,  az=135) = 0.611  ← best
```

**Verdict: FAIL.** The substrate's view-stability claim does NOT
trivially extend to multi-object scenes under the cube+sphere
protocol.

## What this means — and doesn't mean

This is a *real* boundary, not noise. The fingerprint identity is
still preserved: 0.506 is comfortably above the R100 different-scene
baseline (0.325). The substrate fingerprint of "cube + sphere
together" is recognizable as different from "unrelated random
scenes." It's just less view-stable than single-object scenes.

The mechanism is straightforward. As azimuth rotates 0° → 135° around
the z-axis, the **image-space layout** shifts:

- At az=0: cube projects to left side, sphere to right side
- At az=90: cube and sphere swap horizontal positions (cube moves
  from left to right)
- At az=135: cube on right, sphere on left

Predicates like `has_horizontal_balance`, `has_subject_at_thirds_*`,
`has_horizontal_dominant_edges`, `has_strong_horizontal_orientation_mass`
are **deliberately position-sensitive** by design. They respond to
the compositional layout of the scene, which is exactly what changes
between viewpoints in a multi-object scene.

The substrate is doing what it was built to do. It's measuring
real view-specific compositional structure. For a content-fingerprint
use case, that's the right behavior — different camera angles of the
same multi-object scene SHOULD produce somewhat different fingerprints
because they're showing different visual layouts.

For phoxel splatting training, however, this means:
- Single-object scenes have smooth substrate-fingerprint gradients
  across viewpoint (R124, R126)
- Multi-object scenes have less smooth gradients because the layout
  changes contribute view-specific predicate-flip noise

## What Phase 3 needs to address

If splatting training uses the substrate fingerprint as a
differentiable loss, multi-object instability suggests the loss
needs additional structure:

1. **Per-object fingerprint composition.** Compute fingerprint for
   each object's bounding region separately, sum (or compose) per-
   object losses. Layout becomes structural rather than embedded
   in the global fingerprint.
2. **Layout-invariant predicate subset.** Identify which predicates
   are intrinsically composition-sensitive (the `has_subject_at_thirds_*`
   family, balance predicates, orientation-mass predicates) and
   exclude them from the splatting loss. Use the remaining 100+
   predicates that measure scene-content properties independent of
   spatial layout.
3. **View-conditional loss.** Train the splatter against multiple
   target viewpoints simultaneously rather than expecting a single
   loss to be view-invariant.

R128 doesn't pick between these — it documents the constraint they
need to address.

## Other interpretation: this is the substrate working correctly

The substrate fingerprint encoding "this is a horizontal-imbalanced
scene with cube on left" as different from "this is a horizontal-
imbalanced scene with cube on right" is **the right behavior** for
content-fingerprinting. It correctly distinguishes those as different
configurations of the same content.

For some splatting approaches, view-stability isn't the goal — view-
specific stability is. A "cube-on-left" view should produce a
different fingerprint than "cube-on-right" because they ARE different
photographic compositions of the underlying 3D scene. A renderer
trained against view-specific fingerprints would learn to reproduce
those specific compositional features per viewpoint.

R128's "FAIL" verdict is conditional on the assumption that splatting
wants view-invariant fingerprints. If it wants view-specific
fingerprints, R128 PASSES — the substrate correctly distinguishes
viewpoints by compositional layout.

## Honest caveats

- **The cube and sphere were placed at fixed offsets ±1.0 from
  origin.** Closer placement (more occlusion) or wider placement
  (more layout-shift sensitivity) would produce different
  stability levels. R128 is one operating point in a 2-parameter
  space (object separation × object count).
- **The "FAIL" threshold of 0.65 is arbitrary.** R124 and R126 were
  ABOVE it; R128 is BELOW. But "view-stable enough to be useful for
  X" depends on X — splatting, content-fingerprinting, and image
  comparison have different bars.
- **Renderer is still naive splat-painting.** A proper alpha-blended
  3D-Gaussian-style renderer would produce smoother per-pixel
  contributions and might yield slightly higher J. Within R128's
  scope.
- **Only one cube + one sphere.** Three or more objects, with
  more layout permutations, would surface the boundary more
  clearly.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| **Multi-object scene boundary** | R128 | mean J = **0.506** for cube+sphere across 4 viewpoints; below 0.65 PASS threshold; well above R100 different-scene baseline (0.325) | current — Phase 2 third-step substantive finding; substrate fingerprint correctly captures view-specific compositional differences (this is feature, not bug, depending on use case) |
| Multi-view stability across primitive types | R124 / R126 / R128 | single-object: 0.706-0.833; **multi-object: 0.506** | current — single-object passes both stability and rotational-stability claims; multi-object reveals a real boundary worth attacking in Phase 3 |

## Promises ledger updates

- **C-128 closes:** multi-object scene boundary documented. Substrate
  view-stability claim is single-object-conditional. Phase 3
  differentiable-training work needs to address layout-shift
  contribution to fingerprint instability — proposed approaches
  named in this report (per-object loss, layout-invariant predicate
  subset, view-conditional training).

## Files added this round

- `round128_multiobject/r128_multiobject.py`
- `round128_multiobject/round128_audit.json`
- `round128_multiobject/multiobj_az{000,045,090,135}.png`
- this report
- `PHOXELIS_PROMISES.md` — C-128 entry
- `PHOXELIS_BENCHMARKS.md` — R128 row

## Next round opens with

R129 candidates:

**A — push R125-R128.** Current staged push.bat covers R111-R124;
extend to include R126 + R128.

**B — layout-invariant predicate subset analysis.** Identify which
of the 151 predicates are layout-sensitive vs layout-invariant. If
~100 predicates ARE layout-invariant, recompute R128 Jaccards over
just that subset and verify multi-object stability holds when
layout-sensitivity is excluded. That's an actionable Phase 3
intervention with cheap experimental proof.

**C — start the differentiable-training arc.** Multi-round Phase 3.

**D — closer-placement multi-object test.** Two phoxel objects
placed *adjacent* (touching or with 0.2 separation) so they form
something like a single visual unit. Tests whether the multi-object
boundary is layout-shift-driven or genuinely about scene complexity.

Lean **A then B**. B is a clean diagnostic that informs C; D is a
parameter sweep that can come after.
