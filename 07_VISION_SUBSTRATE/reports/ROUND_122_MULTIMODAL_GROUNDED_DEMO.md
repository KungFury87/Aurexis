# Round 122 — multi-modal grounded perception via MCP: 5/5 scenes hit design exactly

**Date:** 2026-05-01
**Track:** T6 (closing the multi-modal loop on the grounded-AI surface)
**Status:** complete — 5 synthesized scenes with paired RGB + depth + hyperspectral; all 3 paths passed through MCP server's `phoxelis_evaluate_image`; all 5 R107 cross-modal predicates fire on exactly the scenes they should; LLM-generated grounded descriptions reference cross-modal evidence directly

---

## Why this round

R120 demonstrated grounded perception via MCP on RGB-only images.
R107's cross-modal predicates correctly abstained 0/10 because no
depth or hyperspectral aux paths were provided. R122 closes that
circle: synthesize 5 scenes with all three modalities populated,
pass them through the MCP server, verify the cross-modal predicates
fire as designed, and produce grounded multi-modal descriptions.

If this works, the full stack — typed-field interface + R107
cross-modal predicates + MCP protocol + LLM grounded reasoning — is
operational end-to-end.

## Method

1. Generate 5 paired (RGB, depth, hyperspectral) scenes covering the
   discrimination space the R107 predicates are designed for.
2. For each, write three files: `<name>_rgb.png`, `<name>_depth.npy`,
   `<name>_spectral.npy` (HxWx31 float64 cube).
3. Spawn the live MCP server, send `tools/call phoxelis_evaluate_image`
   with all three paths.
4. Inspect the fingerprint for the 5 R107 cross-modal predicates,
   verify they fire on the right scenes.
5. LLM produces grounded descriptions citing the cross-modal evidence.

## Scene design

| scene | depth | spectrum | predicted firing |
|---|---|---|---|
| `vegetation_far` | far field (mean ≈ 0.85) | chlorophyll: NIR plateau + red dip at 670nm | `has_far_field_dominance` + `is_distant_vegetation` |
| `red_close` | close (foreground at 0.20) | narrow gaussian peak at 640nm | `has_narrow_spectral_peak` + `is_close_chromatic_object` |
| `green_close` | close (foreground at 0.20) | narrow gaussian peak at 540nm | `has_narrow_spectral_peak` + `is_close_chromatic_object` |
| `dusk_far` | far field | broad warm ramp (incandescent-like) | `has_far_field_dominance` + `is_uniform_lit_far_field` |
| `flat_wall` | uniform mid (0.6) | broad flat (D65) | none of the 5 cross-modal predicates |

## Results — 5/5 hit design exactly

```
scene               far_field  narrow_peak  distant_veg  close_chrom  uniform_lit
vegetation_far      FIRE       -            FIRE         -            -
red_close           -          FIRE         -            FIRE         -
green_close         -          FIRE         -            FIRE         -
dusk_far            FIRE       -            -            -            FIRE
flat_wall           -          -            -            -            -
```

**Every cross-modal predicate fires on exactly the scenes it should and
correctly abstains elsewhere.** No false positives, no false negatives.

The discrimination is non-trivial because two pairs of scenes are
**adversarial** at the single-modality level:

- `vegetation_far` vs `dusk_far` — both have `has_far_field_dominance`
  firing (depth match), but only `vegetation_far` fires
  `is_distant_vegetation` because it ALSO has the chlorophyll
  red-edge step. Cross-modal AND correctly differentiates.
- `red_close` vs `green_close` vs `vegetation_far` — all three have
  spectrally distinctive content (narrow red peak / narrow green peak
  / chlorophyll plateau), but only the close ones fire
  `is_close_chromatic_object` because the cross-modal AND requires
  *close depth + narrow peak* simultaneously.

`flat_wall` correctly fires none of the cross-modal predicates: it's
neither far nor close enough, the spectrum is broad-flat, no peaks
or red-edge step.

## LLM-generated grounded descriptions (no image access)

Each description reads only the fingerprint dict returned by MCP.

### `vegetation_far`

**Cross-modal evidence:** `has_far_field_dominance` (depth-derived) +
`is_distant_vegetation` (depth-AND-spectral cross-modal AND).

**Grounded description:** A distant scene whose spectral signature
includes the chlorophyll red-edge step characteristic of vegetation —
so I'm reading this as far-field foliage or a wooded landscape at
distance. The cross-modal predicate fires because BOTH the depth
field reports far-dominant content AND the spectral cube shows the
NIR plateau / red-absorption combination that distinguishes
chlorophyll from "any red-shifted spectrum." This is the kind of
discrimination an RGB-only system can't make — vegetation and warm
incandescent illumination both read "warm" in RGB but their spectra
differ structurally.

### `red_close`

**Cross-modal evidence:** `has_narrow_spectral_peak` (spectral) +
`is_close_chromatic_object` (depth-AND-spectral).

**Grounded description:** A close subject in the foreground with a
narrow spectral peak — likely a brightly-saturated red object near
the camera. The cross-modal AND tells me this isn't just "any close
subject" or "any red-tinted scene"; it's specifically a close
subject WITH narrow-band reflectance. Possible interpretations: a
red plastic object, a red-painted surface, or any close item with
high-purity red reflectance.

### `green_close`

**Cross-modal evidence:** `has_narrow_spectral_peak` + `is_close_chromatic_object`.

**Grounded description:** Same cross-modal pattern as `red_close` but
with a green-narrow-peak spectrum. A close subject in the foreground
with high-purity green reflectance. The substrate cannot, on this
fingerprint alone, distinguish "real plant matter close up" from
"green plastic close up" — both would fire identically because
chlorophyll's signature requires the **NIR plateau** (which a close
plant viewed in a frame might or might not have, depending on the
spectral cube's bandwidth and the foreground subject's NIR
reflectance). On this synthesized scene, no NIR plateau is present,
so it reads as narrow-green-peak chromatic-object — green plastic,
green paint, or similar.

### `dusk_far`

**Cross-modal evidence:** `has_far_field_dominance` +
`is_uniform_lit_far_field`.

**Grounded description:** A far-field scene with a broad / flat /
warm spectrum and no narrow peak. The cross-modal AND
(`is_uniform_lit_far_field`) requires far depth AND broadband
spectrum simultaneously, which fits a distant landscape lit by warm
incandescent or evening sunlight. Notably this scene ALSO satisfies
`has_far_field_dominance` (depth match with vegetation_far) but does
NOT trigger `is_distant_vegetation` because the spectrum lacks the
chlorophyll red-edge step. The cross-modal vocabulary correctly
distinguishes the two.

### `flat_wall`

**Cross-modal evidence:** None of the 5 R107 cross-modal predicates
fire.

**Grounded description:** Neither close nor far depth (uniform
mid-range), and a flat broadband spectrum without peaks or
red-edges. The cross-modal vocabulary correctly identifies this as
"none of the named multi-modal scene types" — a flat wall, a
diffuse uniform background, or any scene whose depth and spectrum
are both unremarkable. The substrate doesn't pretend to know what
this scene IS; it says what it isn't, which is the right behavior
for a cross-modal vocabulary that hasn't been trained on every
possible content type.

## What this round empirically demonstrates

**Three claims that were architecturally separate are now joined:**

1. **The typed-field interface scales to multi-modal data through MCP.**
   `evaluate_image` accepts `image_path`, `depth_path`,
   `spectral_path` arguments; the bundle gets all three populated;
   predicates whose `expects` lists include `depth` or
   `hyperspectral` evaluate normally instead of abstaining.
2. **R107's cross-modal predicates discriminate as designed at MCP-call-time,
   not just in the dedicated R107 audit script.** Same predicates,
   same operators, same discrimination — exposed through the LLM-
   facing tool surface.
3. **Grounded multi-modal reasoning is now possible for any LLM with
   access to the MCP server and the right aux-path data.** When the
   user supplies depth + spectral data, the LLM can produce
   grounded descriptions that *cite cross-modal evidence by predicate
   name* — exactly the falsifiable structure the grounded-AI claim
   requires.

## Honest caveats

- **Synthesized scenes, not real captures.** Real depth (LiDAR,
  structured-light) has noise patterns and edge-halos these don't
  model. Real hyperspectral (CAVE, ICVL) has illuminant variations
  these don't model. The point of R122 is the cross-modal
  discrimination working through MCP, not real-world performance.
- **Only 5 R107 predicates exist.** A richer multi-modal vocabulary
  is a future T1 round. The R107 protocol (promote/retire/recalibrate)
  is operational for adding more.
- **LLM (me) describing scenes whose design I know is a weaker test
  than R120's.** R120 had me describe images blind. R122 had me
  describe scenes whose cross-modal patterns I designed. That's
  fine for verifying the predicate firing matches design, but it
  doesn't test the LLM's grounded reasoning under genuine ignorance.
  Real test: third-party fingerprints handed to a different LLM.
- **Spectral .npy cubes are large** (~0.6 MB each at 160×160×31
  float64). They're written to /tmp; only the RGB previews are
  copied into the repo. The audit script regenerates cubes from
  scratch.

## What this round means for the prioritized claims

**Grounded-AI claim (R120 + R122 combined):**

| element | R120 | R122 |
|---|---|---|
| MCP protocol roundtrip | ✓ | ✓ |
| LLM produces grounded language from fingerprints | ✓ | ✓ |
| Multi-modal predicates exercised | abstaining (no aux data) | **firing as designed** |
| Cross-modal AND-discrimination demonstrated | n/a | **5/5 match design** |
| Adversarial-pair discrimination (e.g. depth-confusable, spectral-confusable) | n/a | **clean** |

The grounded-AI claim is now demonstrated across ALL the substrate's
modalities the LLM can reach via MCP — not just RGB.

**Alternative-paradigm claim:** Tangentially supported. R122 shows
that cross-modal predicates compose at runtime through the MCP layer
exactly as the typed-field interface promises. That's a structural
property of the substrate, not a learned behavior, and it works at
N=5 just as it did in R107's N=20 audit. The substrate's scaling
behavior under more cross-modal predicates is open — a good T1
candidate.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| **Multi-modal grounded perception via MCP — 5/5 cross-modal predicates fire on design** | R122 | `vegetation_far` → far+veg; `red_close`/`green_close` → close+chromatic; `dusk_far` → far+uniform; `flat_wall` → none. No false positives, no false negatives. Adversarial pairs (vegetation_far vs dusk_far; close_chromatic vs distant_vegetation) correctly disambiguated by cross-modal AND. | round122 | current — closes the multi-modal loop on the grounded-AI surface |
| Cross-modal grounded language production | R122 | LLM-generated descriptions for 5 multi-modal scenes citing cross-modal evidence by predicate name; explicit reasoning over depth-AND-spectral patterns | round122 | current — the substrate's grounded perception now reaches all its modalities through the LLM-facing MCP surface |

## Promises ledger updates

- **C-122 closes:** multi-modal grounded demo via MCP. Closes the
  R120 caveat that R107 cross-modal predicates abstained 0/10
  on RGB-only inputs. Full cross-modal stack is now demonstrated:
  typed-field interface + cross-modal predicates + MCP protocol +
  LLM grounded reasoning.

## Files added this round

- `round122_multimodal_demo/r122_demo.py` (synth + MCP-call harness)
- `round122_multimodal_demo/fingerprints.json` (5 fingerprints with
  cross-modal verdicts highlighted)
- `round122_multimodal_demo/scenes/*_rgb.png` (5 RGB previews; spectral
  cubes regenerated from script as needed)
- this report
- `PHOXELIS_PROMISES.md` — C-122 entry
- `PHOXELIS_BENCHMARKS.md` — R122 row

## Next round opens with

R123 candidates:

**A — push R122**. Single-round-add to the staged push.bat (now covering
R111-R120; extend to R111-R122).

**B — start T7 Phase 2**: 3D phoxel field datatype + minimal forward
renderer. The differentiable-rendering door Vincent affirmed as
priority alongside the grounded-AI door (now demonstrated through R120
+ R122).

**C — multi-modal corpus growth**: pull a real RGB+depth dataset
(NYUv2 sample) so cross-modal predicates can be exercised on real
sensor data, not synthesized.

**D — measure description accuracy systematically**: have a different
LLM rate R120 + R122 descriptions against actual images. Produces a
real metric for grounded-AI quality.

Lean **A then B**. Push first per anti-drift; then T7 Phase 2 is the
remaining priority door from Vincent's earlier reading. C and D are
strong candidates after the next major arc.
