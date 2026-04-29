# Round 31 — Frame quality gate verification (synthetic test corpus)

**Date:** 2026-04-28
**Round 30 promised:** *"If the gate visibly distinguishes these correctly,
the Python side is done and the next round ports it to JavaScript."*
This round is the verification step — proves the gate distinguishes
correctly *before* we trust its scores on real captures.

## What this round does

Adds `aurexis_workbench/frame_quality_synthetics.py` — six
deterministic synthetic frames that exercise the gate's components
in isolation, plus a verification runner that asserts each frame
gets the expected score band and the expected predicate failures.

### Test cases

| name | generator description | must fail | expected score |
|---|---|---|---|
| `clean_reference` | mid-tone scene with structured rectangles + mild noise | (none) | 0.85 – 1.0 |
| `overexposed` | top 60% of frame clipped to near-max value | `has_overexposed_regions` | 0.0 – 0.30 |
| `underexposed` | top 60% of frame clipped to near-zero value | `has_underexposed_regions` | 0.0 – 0.30 |
| `glare` | mid-tone background + 6 sharp bright disks | `has_specular_highlights` | 0.0 – 0.30 |
| `motion_blur` | clean reference + 21-pixel horizontal box blur | (none enforced — see note) | accepted any |
| `multi_problem` | overexposed + glare combined | `has_overexposed_regions`, `has_specular_highlights` | 0.0 – 0.05 |

All cases are seeded — re-running the generator produces byte-exact
identical frames every time, so the verification is reproducible.

### Note on `motion_blur`

The motion-blur case doesn't have an enforced failure because a
uniformly-blurred frame can land in either of two configurations
the gate sees as fine: (a) uniformly-blurred = focus is uniform
across the frame (just uniformly-low rather than uniformly-sharp),
which keeps `has_uniform_focus` True; (b) the blur reduces high-
frequency content but doesn't introduce specular highlights or
clipped exposure. The gate's current components don't have a
"sharpness threshold" predicate — sharpness uniformity is what
they measure. Whether this is right depends on the downstream
use; for E/D decode, *any* sharpness loss across a critical region
hurts module classification, so a future round may want a
`has_sufficient_sharpness` predicate added. Logged as known
future work, not a Round 31 blocker.

## How the verification runs

```
python -m aurexis_workbench.frame_quality_synthetics
```

Prints a per-case table:

```
case                     score  expected        result
--------------------------------------------------------------------
clean_reference          0.XXX  pass-all        PASS
                               failed: (none)
overexposed              0.XXX  has_overex...   PASS
                               failed: has_overexposed_regions
underexposed             0.XXX  has_underex...  PASS
...
multi_problem            0.XXX  has_overex...   PASS
                               failed: has_overexposed_regions, has_specular_highlights
--------------------------------------------------------------------
verified: N/6
```

Exits 0 if all cases pass, 1 if any fail.

The push.bat runs this as a smoke test and commits the verification
log to push.log. With `--write-pngs <dir>` it also writes the six
synthetic frames as PNGs so you can visually confirm the generators
produce what their names claim.

## Why this matters

Round 30 shipped the gate based on logical composition of existing
predicates. The composition is correct in theory — failed component
multiplies score by `(1 − weight)`, etc. But the actual *predicate
verdicts* on a known-bad frame depend on:

1. The predicate's threshold being correct for the degradation type
2. The operator's measurement actually responding to the degradation
3. The image preprocessing (resize, luma conversion) not destroying
   the signal

Without a synthetic test corpus, we can't tell whether a real-world
frame that "looks bad" but scores high is the gate failing, or the
frame's degradation being subtle. The synthetic corpus pins down
the gate's behavior on unambiguous cases first.

If the verification passes, the gate is correctly wired. Real-world
scoring becomes interpretable: a frame that passes the gate but
visually looks bad means *the gate's design doesn't currently
catch that kind of badness* — actionable as a future component to
add. A frame that fails the gate but visually looks fine means
*one of the components has its threshold too tight* — actionable
as a tuning round.

This is the same Round-7-style verification discipline that broke
the vocabulary's saturating predicates (mean → min) and built up
the synthetic corpus pumps that retired the always-False set.
Applied here at the gate level rather than the predicate level.

## What this round does NOT do

* It does not run on any real captures. That's still Round 29's
  Plan A and B.
* It does not port the gate to JavaScript. That's Round 32+ once
  the Python side passes verification and we have a real-world
  threshold from running on the phone-photos corpus.
* It does not change the vocabulary. **103 predicates, 95 operators
  unchanged.**
* It does not modify the existing gate. The gate is the system
  under test, not the test code.

## Why the synthetic corpus is the right next step before JS port

Porting the Python gate to JavaScript means re-implementing five
predicate evaluators in JS, plus the score composition. Each port
introduces translation risk. Verifying the *Python* gate against a
known-correct test set first means: when the JS port runs against
the same known-correct test set, divergence between Python score
and JS score is a port bug, not a gate-design bug. Without the
synthetic verification, debugging a JS port that scores frames
"wrong" is ambiguous — is it the port, or did Python always score
them wrong?

Synthetic corpus first → port risk drops because the gate's
behavior is now pinned to specific numbers.

## Vocabulary and operator state after Round 31

Unchanged. **103 predicates, 95 operators, 38 synthetic scenes** plus
**6 frame-quality synthetic frames** added as a separate corpus
for verifying the gate composition (not the vocabulary itself).
