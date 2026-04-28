# Round 30 — Frame quality gate v0.1 (the first concrete Phoxelis ↔ E/D integration)

**Date:** 2026-04-28
**Status:** Python-side implementation shipped. JS port + V2.1 client
inlining is a future round once the Python prototype's threshold is
empirically grounded against real captures.

## Why this earns its keep

The Donald handoff's System Status Dashboard flags one specific
problem in the live decode pipeline as YELLOW:

> **Frame quality gating** — *Current blind averaging bakes in errors
> from bad frames. Need quality-weighted fusion, reject low timing
> scores.*

The Phoxelis vocabulary already has the predicates that detect bad
frames: `has_overexposed_regions`, `has_underexposed_regions`,
`has_uniform_focus`, `has_subframe_motion`, `has_specular_highlights`.
Composing them into a per-frame quality score and using that score
to gate which frames feed Bayesian occupancy fusion is a direct fix
for the blind-averaging issue, using existing language work.

This is the first concrete intersection point between the language
substrate (Rounds 1–28 of vocabulary work) and the optical-encoding
side (Aurexis E/D V2.1 decode pipeline). It's also the smallest
correct first-step PVS integration — it doesn't require new encoding
theory, doesn't depend on the 10 MB / business-card aspirational
target, doesn't require any vocabulary extension. Five existing
predicates composed transparently.

## What shipped this round

`aurexis_workbench/frame_quality.py` — the gate module.

* `score_bundle(bundle) -> Quality` evaluates the five components
  against a typed `FieldBundle` and returns a deterministic score
  in `[0, 1]` plus the per-component breakdown.
* Score formula: start at 1.0, multiply by `(1 - weight)` for each
  failed predicate. A single full-weight (1.0) failure drops the
  score to 0; a 0.85 weight failure drops it to 0.15; two 0.85
  failures stack multiplicatively to 0.022.
* Component table:

  | predicate                  | bad when    | weight | reason |
  |---|---|---|---|
  | `has_overexposed_regions`  | True        | 0.85   | clipped highlights = bad classification reliability |
  | `has_underexposed_regions` | True        | 0.85   | clipped shadows = bad classification reliability |
  | `has_uniform_focus`        | False       | 0.70   | non-uniform focus = motion or DOF blur somewhere |
  | `has_subframe_motion`      | True        | 0.70   | handshake / target moved during burst |
  | `has_specular_highlights`  | True        | 0.85   | glare / mirror highlights confuse classification |

* `bundle_from_image_path(path) -> FieldBundle` is a convenience
  loader: one image file → bundle the gate can score, no harness
  session needed.

`phoxelis_frame_quality_demo.py` (workspace root) — the runner.

* Takes a folder of images.
* Scores every image.
* Emits `FRAME_QUALITY_<label>_<timestamp>.md` plus parallel `.json`
  with: per-frame scores, sorted ranking, bucket distribution
  (rock-solid / good / marginal / reject), failure breakdown across
  the corpus (which predicate is the most common culprit), and a
  details section for the reject bucket explaining each rejection.

## How to run it

```
python phoxelis_frame_quality_demo.py "Phone photos"
python phoxelis_frame_quality_demo.py /path/to/captures --threshold 0.5
```

The default threshold is 0.5 — frames that score at or above pass,
below reject. The threshold is exposed as a parameter because the
empirically-correct value depends on the corpus and the downstream
use. For a noisy phone-burst, 0.3 might be the right threshold (let
in everything that isn't catastrophically bad). For a calibration
artifact under controlled lighting, 0.7 might be right (only
high-quality frames feed fusion).

## What the report tells us

Three things, in order of importance:

**Bucket distribution.** If most of the corpus lands in rock-solid /
good and only a handful in reject, the gate is conservative and most
captures will pass through to fusion. If many land in marginal or
reject, the gate is strict — useful for tuning down to a sane
threshold. The "right" distribution depends on the application.

**Failure breakdown.** Which predicate fails most often across the
corpus? If `has_specular_highlights` fails on 80% of frames, either
your captures have a lot of glare (real signal — the gate is
catching it correctly) or the predicate's threshold is too tight
(a false-positive cleanup target for Round 31).

**Reject bucket details.** For each rejected frame, the specific
predicates that failed and the resulting score. This is the
actionable list — visually inspect the rejected frames, confirm
they actually look bad, and either accept the gate's verdict or
identify which predicate over-rejected.

## How this slots into the V2.1 decode pipeline

The current pipeline, per the Donald handoff Section 3.2:

```
camera frame → finder detection → format estimation → homography warp
            → module sampling → color classification
            → occupancy grid fusion (multi-frame Bayesian)
            → soft-decision RS (Chase-2)
            → decompress → SHA-256 verify → data
```

The gate inserts after `camera frame` and before `occupancy grid
fusion`:

```
camera frame
  ↓
[FRAME QUALITY GATE]
  ↓ score < threshold? skip this frame
  ↓ score ≥ threshold? continue
  ↓
finder detection → format estimation → homography warp
            → module sampling → color classification
            → occupancy grid fusion
```

This implementation is Python. The V2.1 client (`aurexis_ed_v2_unified.html`)
is JavaScript. Porting is a Round 31+ task: re-express the five
component predicates in JS using the V2 decode engine's existing
image utilities, compose them with the same multiplicative score
formula, and inline the result in the V2.1 client as a pre-fusion
filter.

The empirically-grounded threshold from the Python demo is what the
JS port uses as its default. That's why the Python side ships first.

## Why this is safe vs Donald's MUST-NOT rules

The handoff has eight MUST-NOT rules in Section 2.2. Six are about
how decode classification and finder detection should work — the
gate doesn't touch any of those. Two could plausibly intersect:

* **NEVER apply blind frame averaging.** The gate is the *opposite*
  of blind averaging — it's what enables quality-weighted fusion
  by rejecting frames that would have averaged badly.
* **NEVER trust parallelogram estimate for BR corner.** The gate
  doesn't do corner detection at all.

Net: the gate fits cleanly inside the constraint set. It addresses
the blind-averaging problem rather than perpetuating it.

## What this round does NOT do

* It does not port to JavaScript. That's a Round 31+ task.
* It does not modify the V2.1 client. That's a Round 31+ task.
* It does not require running on Vincent's phone. The gate runs on
  any image folder; phone captures are one valid input but not the
  only one.
* It does not change the vocabulary. **103 predicates, 95 operators,
  unchanged.** The gate is a composition over existing predicates,
  not a new predicate.
* It does not auto-tune the threshold. Threshold selection is
  empirical and corpus-specific; the demo runner's bucket
  distribution surfaces what threshold separates good from bad.

## Vocabulary and operator state after Round 30

Unchanged. **103 predicates, 95 operators, 38 synthetic scenes.**
Round 30 ships the gate composition module + a demo runner + this
doc, all without altering the vocabulary itself.

## What I want next

Two empirical numbers from running the demo on real corpora:

1. Run on the existing 13-image phone-photos folder. Expected: most
   pass (those photos were taken deliberately, not blindly). Any
   that don't are the cleanup-target subset.
2. Run on a folder of deliberately-degraded captures (some shaky,
   some glare-heavy, some over/underexposed). The gate should
   route the bad ones to `reject` and the good ones to `rock-solid`
   or `good`.

If the gate visibly distinguishes these correctly, the Python side
is done and the next round ports it to JavaScript.
