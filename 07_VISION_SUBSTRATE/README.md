# Core 07 - Vision Substrate (V2 language extended for vision)

This directory is the canonical home for the vision substrate inside
Aurexis Core. The same files exist as a working development copy in
`Aurexis_Workbench_v2_0/` at the workspace root; that copy is the
edit/iterate environment, this copy is the Core reference.

## What this is

The Workbench v2.x typed-substrate (fields, operators, predicate
AST, type-checker, runtime, vocabulary, surface DSL, Independence
Ratio, candidate intake) extended with:

  - 1 new field dtype: `image_stack`
  - 32 new vision operators in `aurexis_workbench/vision_ops.py`
  - 33-predicate vocabulary in `data/vision/vocab.aurex`
  - Generic visual intake (any image / video / dir / pair) in
    `aurexis_workbench/visual_intake.py`
  - Session bridge for `.aurex-session` zips in
    `aurexis_workbench/vision_bridge.py`
  - Two CLIs: `cli_vision` (sessions) and `cli_visual` (anything)

The vision substrate is **substrate-agnostic**: predicates compose
operators over typed fields; they do not care whether the field
came from a phone burst, a JPEG, a PNG, a video, or a synthetic
generator.

## Where this came from

The Vision Lab in `Aurexis_RawVisionLab_v0_1/` was originally a
parallel Python module reinventing what this substrate already
provides (typed fields, operator registry, predicate AST,
vocabulary store). The substrate audit
(`VISION_LANGUAGE_AUDIT.md`) confirmed it; the lift across
Rounds 0..6 of `VISION_LANGUAGE_v0_1.md` ported every Vision Lab
predicate into DSL text. Vision Lab is now subordinate - it
provides scene generators and a session loader; the verdicts
that count are produced by this substrate.

## Why it lives in Core

Core's V1 substrate is `05_ACTIVE_DEV/aurexis_lang/`. That tree
is V1-frozen. The V2 substrate is the Workbench, and the vision
extension is V2 work. Landing it in Core under `07_VISION_SUBSTRATE/`
makes Core the canonical reference for the V2 vision language.
The Workbench top-level directory remains the dev environment but
is no longer the home of record.

When V2 is unified into Core proper (the working/core-v2 branch
on GitHub), this directory becomes the merge target. Until then it
is a snapshot of the Workbench at the date in
`reports/IR_RUN_2026-04-27.md`.

## Files

```
07_VISION_SUBSTRATE/
  README.md                         this file
  VISION_LANGUAGE_AUDIT.md          what Workbench already provided
  VISION_LANGUAGE_v0_1.md           the language definition + 6 rounds of growth
  pyproject.toml                    pytest config
  aurexis_workbench/                full V2 substrate package
    fields.py                       typed field model (image_stack added)
    operators.py                    Workbench operator registry
    vision_ops.py                   32 vision operators
    predicates.py                   AST + compiler + type-checker
    runtime.py                      predicate runtime
    dsl.py                          surface DSL parser
    vocabulary.py                   vocabulary store
    independence.py                 IR runner (task-oriented)
    visual_intake.py                generic visual input -> FieldBundle
    vision_bridge.py                .aurex-session zip -> FieldBundle
    cli_vision.py                   run vocab against sessions
    cli_visual.py                   run vocab against ANY visual
    intake.py                       candidate intake (DSL parse + type-check)
    starter.py                      starter vocabulary (V1 baseline)
    scenarios.py                    scenario seeds for IR
  data/vision/
    vocab.aurex                     33-predicate vision vocabulary
  reports/
    IR_RUN_2026-04-27.md            cross-predicate independence analysis
```

## Findings the IR run produced (2026-04-27 corpus = 19 inputs)

The IR analysis is the language self-auditing. Real findings:

  - 9 predicates fire 0 percent on this corpus (always FALSE).
    They are not broken - they have not encountered a positive
    instance yet. has_horizon_line_signature, is_uniform_field,
    has_low_edge_density, etc.
  - has_gradient_energy and has_high_frequency_residual fire
    100 percent and have agreement 1.00 - they are statistically
    redundant on natural images.
  - has_anisotropy_in_brightest_patch and has_high_dynamic_range
    saturate at 95 percent. Thresholds too lenient for this corpus.
  - The actual discriminators (firing rate 30-70 percent):
    text_is_dominant_concept, has_screen_displaying_text,
    has_centered_subject, has_screen_displaying_face,
    has_mirror_symmetry_horizontal_axis, has_genuine_text_not_screen,
    has_text_like_signature.
  - Rare-event detectors (5-21 percent) are working correctly:
    has_subframe_motion, has_global_brightness_drift,
    has_real_motion_validated, has_face_like_signature,
    has_screen_like_signature.

The next round of vocabulary work should:
  1. Tighten thresholds on the saturating predicates.
  2. Consolidate gradient_energy + high_frequency_residual or
     redefine them so they actually disagree on edge cases.
  3. Add inputs to the corpus that exercise the always-False
     predicates (a horizon-line photo, a uniform sky photo, etc.)
     so the IR can grade them.

This is the empirical loop the Independence Ratio runner was built
for, and it is now operating on real-corpus, real-substrate data.
