# Round 32 — Frame quality gate ported to JavaScript (V2.1 inlining ready)

**Date:** 2026-04-28
**Closes:** the YELLOW "blind averaging bakes in errors from bad frames"
status item from the Donald handoff. The gate now exists in both
Python (Round 30, for empirical scoring of phone-photo corpora)
and JavaScript (this round, for inlining in `aurexis_ed_v2_unified.html`
as a pre-fusion filter in the V2.1 decode pipeline).

## What shipped

`Aurexis_ED/frame_quality_gate.js` — pure JS, no DOM, Node-compatible,
matches the V2 decode engine style. ~280 lines. Exports both
`module.exports` (Node) and `window.PhoxelisFrameQuality` (browser).

API:

```js
const FQ = require("./frame_quality_gate");

// imgData: Uint8ClampedArray | Uint8Array of RGBA, length W*H*4
// Returns { score, passed, failed, blocked, reasoning }
const result = FQ.scoreFrame(imgData, W, H, { resize: 320 });

if (result.score >= 0.5) {
    // frame passes — feed to Bayesian occupancy fusion
} else {
    // frame fails — skip it; log result.failed for diagnostics
}
```

### Operators ported

| operator | what it computes |
|---|---|
| `rgbaToLuma(imgData, W, H)` | RGBA Uint8 → normalised Float64 luma in [0, 1] |
| `resampleLuma(luma, W, H, maxLong)` | nearest-neighbor downsample (matches Python's step slicing) |
| `brightPixelFraction(luma, threshold)` | fraction of luma values > threshold |
| `darkPixelFraction(luma, threshold)` | fraction of luma values < threshold |
| `gradientsAbs(luma, W, H)` | per-pixel sqrt(gx² + gy²) using forward differences |
| `focusBlurGradient(luma, W, H)` | (centerMean − edgeMean) / (centerMean + edgeMean) over gradient magnitudes; range ≈ [-1, 1] |
| `brightSpotCount(luma, W, H, threshold)` | 4-connected union-find labeling, filter components in [1, max(20, N/1000)] pixels |

Constants pinned to the same values as `vocab.aurex` and the Python
`frame_quality.py`:

```js
OVEREXPOSED_LUMA_THRESH    = 0.97;   // bright_pixel_fraction(>0.97)
OVEREXPOSED_FRAC_THRESH    = 0.05;   // > 5% of pixels => fail
UNDEREXPOSED_LUMA_THRESH   = 0.03;
UNDEREXPOSED_FRAC_THRESH   = 0.05;
FOCUS_GRADIENT_THRESH      = 0.20;   // |grad| < this => uniform
SPECULAR_LUMA_THRESH       = 0.92;
SPECULAR_SPOT_COUNT_THRESH = 3;       // > 3 spots => specular present
```

### Score composition — identical to Python

Components (must match the Python `COMPONENTS` table):

```js
{ name: "has_overexposed_regions",  badWhen: true,  weight: 0.85 }
{ name: "has_underexposed_regions", badWhen: true,  weight: 0.85 }
{ name: "has_uniform_focus",        badWhen: false, weight: 0.70 }
{ name: "has_specular_highlights",  badWhen: true,  weight: 0.85 }
```

`has_subframe_motion` is **omitted in single-frame JS** — the V2.1
pipeline operates on individual capture frames at the gate's
insertion point, and burst-temporal variance isn't available there.
The four-component subset still catches the four largest classes of
bad-frame failures.

Score formula: start at 1.0; for each predicate verdict that matches
its `badWhen`, multiply score by `(1 − weight)`. Any 0.85-weight
failure drops the score to 0.15; two stack to 0.022; three stack to
0.0034. The 0.5 default threshold trips on any single full-weight
failure or any two medium-weight ones.

## Verification

`Aurexis_ED/test_frame_quality_gate.js` — Node test, runs:

```
node test_frame_quality_gate.js
```

Six synthetic frames generated in pure JS using a deterministic LCG
seed (so re-runs reproduce exactly), matching Round 31's Python test
cases conceptually:

| case | generator | must fail | score band |
|---|---|---|---|
| `clean_reference` | mid-tone with structured rectangles + mild noise | (none) | 0.85 – 1.0 |
| `overexposed` | top 60% near-max | `has_overexposed_regions` | 0.0 – 0.30 |
| `underexposed` | top 60% near-zero | `has_underexposed_regions` | 0.0 – 0.30 |
| `glare` | mid-tone bg + 6 sharp bright disks | `has_specular_highlights` | 0.0 – 0.30 |
| `motion_blur` | clean + 21px horizontal box blur | (not enforced — see Round 31) | accepted any |
| `multi_problem` | overexposed + 8 glare disks | both overexposed AND specular | 0.0 – 0.05 |

Pixel values won't be byte-identical to Python's because numpy's
PCG64 RNG and JS LCG produce different bytes. The structural
assertions — *which predicates fire* and *what bucket the score
lands in* — must match. That's what the test verifies.

Test exits 0 on all-pass, 1 on any-fail. The push.bat runs it as a
smoke test and commits the verification log.

## Inlining into aurexis_ed_v2_unified.html — Round 33

Not done in this round. The Python and JS gates are now both verified
in isolation; what remains is splicing the JS into the V2.1 client.
The inlining recipe (for Round 33):

1. Copy the entire body of `frame_quality_gate.js` into a `<script>`
   block inside `aurexis_ed_v2_unified.html` near the other inlined
   modules (search for `// V2 engine bundle` or similar).
2. Find the place in the V2.1 frame-handling loop where a captured
   `ImageData` is about to enter `accumulateFrame()` (or whatever
   the Bayesian-fusion entrypoint is called) and insert before that
   call:
   ```js
   const fq = PhoxelisFrameQuality.scoreFrame(
       imgData.data, imgData.width, imgData.height);
   if (fq.score < FRAME_QUALITY_THRESHOLD) {
       gateRejects++;
       gateRejectReasons.push(fq.failed.join(","));
       return; // skip fusion for this frame
   }
   ```
3. Add `FRAME_QUALITY_THRESHOLD = 0.5` near the existing fusion
   parameters (`SOFT_SIGMA`, `CONF_DECAY`, etc.).
4. Surface the reject count in the existing stats line:
   `v2.1, occ:Nf XX%cov YY%conf, gated XX/YY` so the live UI shows
   how many frames the gate is rejecting in real time.
5. Test on a captured artifact: with the gate enabled, decode time
   and reliability should be at least as good as without; ideally
   better when the camera is moving or the artifact has glare.

The Round 33 push.bat will run the existing V2 decode tests
(`node test_decode_engine.js`, 8 roundtrip tests) plus the new
Node test for the gate, plus the V2.1 client smoke test, before
committing.

## Why both Python and JS

The Python side is for **empirical work**: scoring large folders
of phone photos, building intuition about real-world thresholds,
running the gate against the existing 13-photo corpus, and being
the reference implementation when the JS port's behavior is
ambiguous. The JS side is for **production**: inlining into the
V2.1 client so the gate runs on every camera frame before fusion,
on the user's phone, with no Python dependency.

Having both means we can answer "is the gate calibrated correctly"
on Python (where the 103-predicate vocabulary is available and
tunable) and "does the gate run fast enough in browser" on JS
(where the V2.1 decode loop already runs).

## Constraint compliance check (Donald handoff §2)

The gate sits inside the existing constraint set:

* **NEVER apply blind frame averaging** — the gate is the *opposite*
  of blind averaging.
* **NEVER trust parallelogram BR estimate** — the gate doesn't do
  corner detection.
* **NEVER bicubic interpolation** — the gate's resample is integer-
  step nearest-neighbor downsampling, not bicubic.
* **NEVER single-pixel sampling** — the gate's measurements are all
  whole-frame fractions / patch means / connected-component labels;
  no single-pixel decisions anywhere.
* All other MUST-NOT rules are about decode-side classification and
  finder detection, which the gate doesn't touch.

Net: zero conflicts with the constraint set.

## Vocabulary state after Round 32

Unchanged. **103 predicates, 95 operators, 38 synthetic scenes plus
6 frame-quality synthetics.** Round 32 ports existing logic to a
new language; it doesn't add or remove substrate.

## What Round 33 unlocks (after this lands)

Once the gate is inlined in the V2.1 client and Vincent does a
new live capture pass with it enabled, we get the first piece of
evidence that the Phoxelis Vision Language has practical impact
on the optical-encoding side of the project. Specifically: decode
reliability with vs without the gate, on the same captured
artifact, under the same conditions. That's the headline number
for the Round 30 → 33 arc.
