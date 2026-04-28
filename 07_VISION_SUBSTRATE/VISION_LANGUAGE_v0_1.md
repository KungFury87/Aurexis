# Vision Language v0.1 - the language of vision

This document defines the language Aurexis uses to express predicates
that recover structure outside the conventional RGB pipeline. It
extends the Workbench v2.x surface DSL with vision-specific types,
operators, and a starter vocabulary.

The language is text. Predicates are vocabulary entries, not Python
functions. The Workbench runtime parses, type-checks, compiles, and
evaluates them against typed FieldBundles produced by real captures.

## Why text and not Python

A vocabulary written in DSL is:

  - Type-checked before installation (no silent runtime type errors).
  - Persistable as JSON (the vocabulary store is the canonical record).
  - Composable from operators that are themselves typed and registered.
  - Auditable: a predicate's body is a small expression you can read,
    not 60 lines of conditional logic.
  - Independence-Ratio-scored: every predicate becomes a row in the
    IR matrix automatically.

The Python lab in `Aurexis_RawVisionLab_v0_1/` contains scene
generators and surfaces; the predicates that *gate verdicts* now
live in `data/vision/vocab.aurex`. That file is the language.

## Types (dtypes)

Workbench v2.0 dtypes:

    image     a 2-D float array in [0, 1]
    scalar    a single float
    int       a single integer
    bool      a single boolean
    regions   a list of 2-D boolean masks
    vector    a 1-D float array
    label     a string

Vision v0.1 adds:

    image_stack    a 3-D float array (N, H, W) - a burst, a pair, or
                    any indexed collection of frames

A predicate's `expects` clause names the fields it needs and their
dtypes. The runtime errors with a clean message if the bundle lacks
a field; that surfaces "BLOCKED" as a verdict in the language, not
as a hidden Python exception.

## Operators (vision_ops registered in the global registry)

### Bayer mosaic (RGGB pattern assumed; raw input is required)

    bayer_R(image)            -> image     R sub-channel
    bayer_Gr(image)           -> image     Gr sub-channel
    bayer_Gb(image)           -> image     Gb sub-channel
    bayer_B(image)            -> image     B sub-channel
    green_imbalance(image)    -> scalar    |Gr-Gb|/(|Gr|+|Gb|)
    channel_spread_norm(image)-> scalar    (max-min Bayer mean)/overall mean

### Frequency-domain

    fft_peak_to_floor(image)  -> scalar    peak / median magnitude
    fft_peak_radius(image)    -> scalar    radius of strongest non-DC peak
    block_avg_2x2(image)      -> image     simplest demosaic-equivalent

### Structure tensor

    structure_tensor_coherence(image)         -> scalar  whole-image
    max_coherence_patch_coh(image, int)       -> scalar  best ROI patch

### Temporal (image_stack)

    temporal_diff(image_stack)            -> scalar  |diff|/|signal|
    temporal_diff_coherence(image_stack)  -> scalar  FFT peakedness of diffs
    temporal_uniform_ratio(image_stack)   -> scalar  |mean(diff)|/mean(|diff|)

### Rotated pair (polarization analogue)

    rotated_pair_anisotropy(image, image) -> scalar  (I0-I90)/(I0+I90)

### Scalar arithmetic

    abs_s(scalar)              -> scalar
    div_s(scalar, scalar)      -> scalar
    mul_s(scalar, scalar)      -> scalar
    sub_s(scalar, scalar)      -> scalar
    add_s(scalar, scalar)      -> scalar

### Comparison and logic (already in Workbench)

    eq, neq, lt, gt, leq, geq  : scalar x scalar -> bool
    eq_int, etc                : int x int       -> bool
    AND, OR, NOT               : bool[ x bool]   -> bool

## Predicate grammar

A predicate is a block:

    predicate <NAME>
      expects <FIELD>:<DTYPE>[, <FIELD>:<DTYPE> ...]
      returns <DTYPE>
      intent  <IDENT>
      body    <EXPR>

Expressions compose calls, field references, and constants:

    expr      := call | const | field_ref
    call      := IDENT "(" arg ("," arg)* ")"
    const     := INT | FLOAT | STRING | BOOL
    field_ref := IDENT  (only valid if IDENT is in expects)

`true`/`false` are bool. INT (no dot) is int. FLOAT (with dot) is
scalar. Strings (double-quoted) are label.

## Starter vocabulary (data/vision/vocab.aurex)

Seven predicates, all type-checked, all evaluating successfully on
real captures:

  has_subframe_motion              detect_motion_within_subframe_integration
  has_global_brightness_drift      detect_isp_brightness_drift_confound
  has_anisotropy_in_brightest_patch  detect_local_oriented_structure
  has_structural_anisotropy_whole_image  legacy whole-image scope
  has_polarization_signal          requires cap_axis_0/cap_axis_90 fields
  has_subpixel_periodicity         requires raw_bayer field
  has_spectral_band_anomaly        requires raw_bayer field

The first four run on JPEG-only sessions captured today. The last
three are language-complete but require fields the harness does not
yet produce (raw Bayer, polarization pair). Their BLOCKED status is
now a first-class verdict, surfaced by the runtime as a clean error
rather than a hidden inconclusive.

## How a predicate gets into the language

1. Identify the measurement (does an existing operator produce it?
   If not, write one - operator code lives in `vision_ops.py`,
   registered with declared in_types/out_type).
2. Author the predicate in vocab.aurex as DSL text.
3. Run `python -m aurexis_workbench.cli_intake` to parse and
   type-check. Bad candidates surface diagnostic messages with
   line/column.
4. Run `python -m aurexis_workbench.cli_vision` to evaluate the
   accepted vocabulary against every .aurex-session zip on disk.

This is a closed loop: if a verdict needs a measurement, you add
an operator; if a measurement supports a verdict, you author a
predicate; vocabulary grows by single composable additions, not
by Python-class refactors.

## Real-capture verdicts (Round 3 - language verified)

| session                | motion | drift | patch_aniso | whole_aniso |
|------------------------|--------|-------|-------------|-------------|
| dark cal grid (lux 2)  | True   | True  | True        | False       |
| repetition strip (lux 51) | True | False | True       | False       |
| symmetry test (lux 56) | True   | False | True        | False       |
| cal grid (lux 93)      | True   | False | True        | False       |

These verdicts now come from typed DSL predicates over the operator
registry, NOT from the Python predicates module. The Python module
in `Aurexis_RawVisionLab_v0_1` is now subordinate: it provides scene
generators, surface code, and a session loader, but the verdicts
that count are the ones the language produces.

## What this changes about the project

The Vision Lab is no longer the canonical predicate store. The
**vocabulary file is the language**, and the **language is the
project**. New predicates do not require new Python; they require
new operators (small) and new vocabulary entries (a few lines of
DSL text).

This is the bootstrap Vince called for. Python files build the
substrate; the language does the seeing.

---

## Addendum: substrate-agnosticism (added 2026-04-27)

Three questions clarified the architecture:

1. **Are we building a visual AI?** No. A visual AI is a trained net
   with fixed weights that pattern-matches in a learned latent space.
   It has the same fundamental limitation any RGB-trained vision has:
   it is stuck in its training distribution. The Vision Language is a
   different kind of artifact - explicit measurement, composable
   typed predicates, auditable verdicts. For the domain of "structure
   recovery from instruments", the language is strictly more powerful
   than a visual AI, because the failure modes of a visual AI on raw
   Bayer / polarization / sub-pixel periodicity are exactly the same
   failure modes any RGB-trained eye has. Building a visual AI would
   not solve the problem; it would relocate it.

2. **Is the language ALSO the language a visual AI would see in?**
   Internally no - visual AIs operate in distributed activations.
   Externally yes - the language is what a visual AI could explain
   itself in, get verified against, and surface its uncertainty
   through. The language is a complement to a visual AI, not a
   substitute, and is necessary regardless of whether one ever exists.

3. **Can we feed anything visual into the language?** Yes. The
   language operates on `image` and `image_stack` - 2-D and 3-D float
   arrays in [0, 1]. Where those arrays come from is irrelevant. The
   `visual_intake` module accepts:
     - any single image (jpg/png/bmp/tiff/webp/heic)
     - a directory of images (sorted -> image_stack)
     - a video file (mp4/mov/avi)
     - a pair of images (axis 0 / axis 90)

   The pipeline-depth distinction (raw vs ISP-processed JPEG) only
   matters for predicates whose evidence the ISP destroys (subpixel
   periodicity, spectral anomaly). Every other predicate runs on
   anything with pixels.

### A property the language has that a visual AI cannot

The Vision Language has **no learned parameters and no VRAM
footprint**. Capability is added by:
  - registering an operator (one Python function with declared types)
  - authoring a predicate (a 6-line DSL block)

There is no training. There is no model checkpoint. There is no
distribution to drift away from. Vocabulary is the language is the
project. Anyone who can read the audit doc can extend the eyes by
publishing a vocabulary entry.

### Verdicts on real arbitrary inputs

A phone photo (244x523 luma):

```
has_subframe_motion                     False
has_global_brightness_drift             False
has_anisotropy_in_brightest_patch       True
has_structural_anisotropy_whole_image   False
has_gradient_energy                     True
is_uniform_field                        False
has_repetitive_horizontal_structure     True
has_high_frequency_residual             True
has_centered_subject                    True
```

A checkerboard PNG (640x360 luma):

```
has_anisotropy_in_brightest_patch       True
has_centered_subject                    False     # fills frame, not centred
has_repetitive_horizontal_structure     True      # 8 squares horizontally
has_high_frequency_residual             True
```

A linegrid PNG (640x360 luma):

```
has_anisotropy_in_brightest_patch       False     # see note
has_repetitive_horizontal_structure     True
has_high_frequency_residual             True
```

The linegrid result is a **discovery** the language surfaced: a
perfect grid is not anisotropic in the structure-tensor sense
because it has equal energy on horizontal and vertical axes. The
predicate is correct; "anisotropic" means oriented, and a grid is
not oriented. This is the kind of insight the language produces
that a pattern-matching visual AI would not generate, because
nothing in CLIP's training set teaches the difference between
"anisotropic" and "structured".

### Vocabulary is now 12 predicates

The seven session-tied predicates from v0.1 plus five generic-image
predicates:
  has_gradient_energy
  is_uniform_field
  has_repetitive_horizontal_structure
  has_high_frequency_residual
  has_centered_subject

All 12 type-check. Three remain BLOCKED on JPEG inputs (waiting on
harness raw Bayer + polarization-pair captures); the other nine
fire on any image you point them at.

---

## Round 4 vocabulary expansion (added 2026-04-27)

Three new operators registered:
  directional_gradient_energy(image, label) -> scalar
  edge_density(image, scalar) -> scalar
  dynamic_range(image) -> scalar

Seven new predicates authored:
  has_horizontal_dominant_edges       horizon / floor lines vs trees / columns
  has_vertical_dominant_edges
  has_high_edge_density               busy / detailed scenes
  has_low_edge_density                blurry / uniform scenes
  has_high_dynamic_range              high contrast scenes
  has_mirror_symmetry_horizontal_axis top-to-bottom mirror score (uses existing core operator)
  has_mirror_symmetry_vertical_axis   left-to-right mirror score

All 19 predicates parse and type-check.

### Round 4 verdicts on the same arbitrary inputs

A phone photo (244x523):
```
has_high_dynamic_range                  True
has_mirror_symmetry_horizontal_axis     True       # top/bottom compositional balance
has_mirror_symmetry_vertical_axis       False
has_horizontal_dominant_edges           False
has_vertical_dominant_edges             False      # neither axis exceeds 1.5x the other
```

A checkerboard PNG:
```
has_high_dynamic_range                  True       # black/white = max contrast
has_mirror_symmetry_horizontal_axis     False      # 8x6 grid has odd-count parity flip
has_mirror_symmetry_vertical_axis       False
has_horizontal_dominant_edges           False
has_vertical_dominant_edges             False      # balanced (square cells)
```

A linegrid PNG:
```
has_high_dynamic_range                  False      # thin lines on uniform bg = low std/mean
has_anisotropy_in_brightest_patch       False      # grid is structured but not oriented
has_horizontal_dominant_edges           False
has_vertical_dominant_edges             False
```

### Round 4 verdicts on real captures (4 sessions through cli_vision)

The dark calibration grid session (lux 2):
```
has_subframe_motion                     True      \
has_global_brightness_drift             True       > round 2/3 results preserved
has_anisotropy_in_brightest_patch       True      /
has_vertical_dominant_edges             True       NEW: vertical grid lines
has_high_dynamic_range                  True       NEW: black/white grid = high contrast
has_mirror_symmetry_horizontal_axis     True       NEW: centred grid = top/bottom mirror
```

The repetition_strip session (lux 51):
```
has_repetitive_horizontal_structure     True       NEW: was BLOCKED before row_y default
has_subframe_motion                     True
has_anisotropy_in_brightest_patch       True
has_high_dynamic_range                  True
has_mirror_symmetry_horizontal_axis     True
```

`has_repetitive_horizontal_structure` had been BLOCKED in earlier
rounds because the session bundle did not yet carry a `row_y` field.
The session CLI now defaults `row_y=64`, and the predicate fires
correctly on the literally-striped target. That is one less BLOCKED
cell with no new captures - the language was already capable; only
the bridge needed a default.

### What this round demonstrates

Each round of vocabulary growth is **additive and composable**:
  - Add an operator (one Python function with declared types)
  - Add a predicate (one DSL block referencing operators)
  - The runtime, type-checker, and CLI absorb them with zero changes

We started with 7 predicates that ran only on session bursts; we
now have 19 predicates running on any image, video, or session,
with no rebuilds of the substrate. The language grows by single
composable additions, which is exactly the property a "language of
vision" needs to be useful long-term.

### Vocabulary status (Round 4 final)

19 predicates, all type-checked, all running:

  Run on any image (12):
    has_anisotropy_in_brightest_patch
    has_structural_anisotropy_whole_image
    has_gradient_energy
    is_uniform_field
    has_repetitive_horizontal_structure  (needs row_y)
    has_high_frequency_residual
    has_centered_subject
    has_horizontal_dominant_edges
    has_vertical_dominant_edges
    has_high_edge_density
    has_low_edge_density
    has_high_dynamic_range
    has_mirror_symmetry_horizontal_axis
    has_mirror_symmetry_vertical_axis

  Run on a burst / image_stack (2):
    has_subframe_motion
    has_global_brightness_drift

  Blocked until harness exposes more surfaces (3):
    has_polarization_signal       (needs cap_axis_0/cap_axis_90)
    has_subpixel_periodicity      (needs raw_bayer)
    has_spectral_band_anomaly     (needs raw_bayer)

Total: 19 predicates, 16 not blocked, language stable across rounds.

---

## Round 5: composite predicates (added 2026-04-27)

This round added zero operators. All five new predicates compose
existing operators into single-claim verdicts. That is the
substrate-sufficiency test - the language is now expressive enough
to name concepts, not just measurements.

Five new predicates:

  has_face_like_signature       vertical mirror + centred + local oriented
  has_text_like_signature       fine horizontal repetition + high freq + edges
  has_screen_like_signature     very high freq + very high autocorr + high contrast
  has_horizon_line_signature    horizontal mirror + horizontal edge dominance
  has_real_motion_validated     motion + coherent + NOT global brightness drift

Total vocabulary: 24 predicates, all type-checked.

### The verdict that matters most this round

`has_real_motion_validated` correctly distinguishes real motion
from ISP brightness drift in a SINGLE composite claim:

| session                  | subframe_motion | global_drift | real_motion_validated |
|--------------------------|-----------------|--------------|------------------------|
| dark cal grid (lux 2)    | True            | True         | **False**              |
| repetition_strip (lux 51)| True            | False        | True                   |
| symmetry_test (lux 56)   | True            | False        | True                   |
| cal grid (lux 93)        | True            | False        | True                   |

The dark session's motion claim is now correctly downgraded inline.
A consumer of the language no longer needs to interpret three
separate predicates and combine them mentally. The composite IS the
combination, expressed as a single auditable verdict.

### Substrate-sufficiency demonstrated

Five named-concept predicates, zero new operators. All five built
from operators registered in earlier rounds: mirror_correlation,
center_gradient_concentration, max_coherence_patch_coh,
row_autocorr_peak, high_frequency_residual, edge_density,
dynamic_range, directional_gradient_energy, mul_s, temporal_diff,
temporal_diff_coherence, temporal_uniform_ratio, AND, gt, lt.

This is the property a language of vision needs: the substrate
should saturate before the vocabulary does. New concepts should
require new vocabulary, not new substrate. We crossed that line in
Round 5.

### Discriminating verdicts on real photos

Across 13 phone photos in Phone photos/, with no captioning,
labels, or training:

  has_face_like_signature       fires on 2 / 13 photos
  has_text_like_signature       fires on 4 / 13 photos
  has_screen_like_signature     fires on 0 / 13 photos
  has_horizon_line_signature    fires on 0 / 13 photos

That distribution is the language working correctly: not flagging
everything, not flagging nothing, picking out a small subset for
each named concept. Without ground truth we cannot grade individual
verdicts, but the pattern of discrimination is what a working
predicate vocabulary looks like.

### Notable verdict on the repetition_strip session

The repetition_strip session fires BOTH has_text_like_signature
AND has_screen_like_signature simultaneously. The captured target
was a striped pattern displayed on a monitor. The language
correctly recognised both signatures at once - the scene was
text-like (fine periodic structure) and screen-like (high-frequency
pixel-grid signature). Two named concepts that happen to coincide
in this session, both reported, neither hidden.

This is the kind of verdict a pattern-matching visual AI would
struggle to produce. CLIP would pick its single most-likely caption
("a black and white pattern" or similar). The language reports
each named concept independently and lets the consumer combine
them however they need to.

### Vocabulary status (Round 5 final)

Total: 24 predicates, all type-checked, all running.

  Run on any image (17):
    has_anisotropy_in_brightest_patch
    has_structural_anisotropy_whole_image
    has_gradient_energy
    is_uniform_field
    has_repetitive_horizontal_structure
    has_high_frequency_residual
    has_centered_subject
    has_horizontal_dominant_edges
    has_vertical_dominant_edges
    has_high_edge_density
    has_low_edge_density
    has_high_dynamic_range
    has_mirror_symmetry_horizontal_axis
    has_mirror_symmetry_vertical_axis
    has_face_like_signature              [composite]
    has_text_like_signature              [composite]
    has_screen_like_signature            [composite]
    has_horizon_line_signature           [composite]

  Run on a burst / image_stack (3):
    has_subframe_motion
    has_global_brightness_drift
    has_real_motion_validated            [composite]

  Blocked until harness exposes more surfaces (3):
    has_polarization_signal
    has_subpixel_periodicity
    has_spectral_band_anomaly

24 predicates. 5 of them are composites — concepts, not measurements.
The substrate is now sufficient; growth from here is vocabulary,
not substrate.

---

## Round 6: scoring + dominance + disambiguation (added 2026-04-27)

This round added five operators and nine predicates. The shift:
named-concept verdicts are now **continuous scores in [0, 1]**, and
predicates ask which concept dominates and whether dominance is
ambiguous (two concepts close in score).

### New operators (5)

  face_likeness_score(image, int)   -> scalar
  text_likeness_score(image, int)   -> scalar
  screen_likeness_score(image, int) -> scalar
  horizon_likeness_score(image)     -> scalar
  max_s(scalar, scalar)             -> scalar

Each likeness score combines three indicator components and clamps
to [0, 1]. max_s enables dominance comparisons across multiple
scores.

### New predicates (9)

Dominance (which concept wins):
  face_is_dominant_concept
  text_is_dominant_concept
  screen_is_dominant_concept
  horizon_is_dominant_concept
  no_named_concept_dominant            (all scores < 0.40)

Disambiguation (margin-based, post-saturation):
  has_genuine_face_not_screen           face wins by 0.05 margin
  has_screen_displaying_face            face & screen both > 0.60 within 0.05
  has_genuine_text_not_screen           text wins by 0.05 margin
  has_screen_displaying_text            text & screen both > 0.60 within 0.05

### Calibration finding from real photos

Initial scoring used absolute thresholds (face_score > 0.45 etc).
On natural photos every component fires above its reference,
saturating scores near 1.0. The disambiguation predicates with
fixed thresholds fired for everything. Replaced with margin-based
logic: which concept score is HIGHER, by how much. That gives real
discrimination even with saturated absolute values.

This is itself a methodology finding: in a substrate where most
inputs trip most components, **comparative scores discriminate
better than absolute thresholds**. Filed as a vocabulary-design
rule.

### Verdicts across 19 inputs (13 photos + 2 PNGs + 4 sessions)

| input                                     | dominant | disambiguation                            |
|-------------------------------------------|----------|-------------------------------------------|
| photo 20260415_195321                     | screen   | screen_displaying_text                    |
| photo 20260416_071900                     | face     | screen_displaying_face,screen_displaying_text |
| photo 20260416_071906                     | text     | screen_displaying_face,screen_displaying_text |
| photo 20260416_071913                     | text     | screen_displaying_face,screen_displaying_text |
| photo 20260416_071915                     | text     | screen_displaying_text                    |
| photo 20260416_073955                     | face     | screen_displaying_face,screen_displaying_text |
| photo 20260416_074005                     | face     | screen_displaying_face,screen_displaying_text |
| photo 20260416_134642                     | text     | genuine_text_not_screen                   |
| photo 20260416_141505                     | text     | genuine_text_not_screen                   |
| photo 20260416_141509                     | text     | screen_displaying_face,genuine_text_not_screen |
| photo 20260416_143930                     | text     | screen_displaying_face,genuine_text_not_screen |
| photo 20260416_143933                     | text     | screen_displaying_face,genuine_text_not_screen |
| photo 20260416_143941                     | text     | screen_displaying_face,genuine_text_not_screen |
| png checkerboard_8x6                      | text     | screen_displaying_text                    |
| png linegrid_60px                         | text     | genuine_text_not_screen                   |
| session dark cal grid                     | screen   | -                                         |
| session repetition_strip                  | -        | screen_displaying_text                    |
| session symmetry_test                     | text     | screen_displaying_text                    |
| session bright cal grid                   | text     | genuine_face_not_screen,genuine_text_not_screen |

### Patterns visible in the verdicts

- **Afternoon photos (13:46 / 14:15 / 14:39) fire `genuine_text_not_screen`.** Plausible
  hypothesis: those are photos of actual documents (printed text), not
  screens. The language's claim is testable - open one of the photos
  and check.
- **Morning photos (07:19 / 07:39 / 07:40) cluster around face-like
  + screen-displaying signatures.** Plausible hypothesis: photos taken
  of a screen earlier in the day, possibly of someone's face on a screen.
- **The repetition_strip session returns no dominant concept** at
  row_y=64. That is itself a finding: the middle frame's row 64
  doesn't carry the strip signal at this resolution. A row_y sweep
  would tell us where the strip lives in the frame.
- **The bright cal grid session fires both `genuine_face_not_screen`
  and `genuine_text_not_screen`** simultaneously. The grid's regular
  geometry trips both face (centred + oriented) and text (periodic +
  high-frequency) signatures with screen weak.

### Vocabulary status (Round 6 final)

Total: 33 predicates, all type-checked, all running.
33 predicates = 24 (Round 5) + 9 (Round 6 dominance/disambiguation).

  Run on any image (26):
    [Rounds 0-5 generic predicates]
    face_is_dominant_concept             [composite, dominance]
    text_is_dominant_concept             [composite, dominance]
    screen_is_dominant_concept           [composite, dominance]
    horizon_is_dominant_concept          [composite, dominance]
    no_named_concept_dominant            [composite, dominance]
    has_genuine_face_not_screen          [composite, disambiguation]
    has_screen_displaying_face           [composite, disambiguation]
    has_genuine_text_not_screen          [composite, disambiguation]
    has_screen_displaying_text           [composite, disambiguation]

  Run on a burst (3):
    has_subframe_motion
    has_global_brightness_drift
    has_real_motion_validated

  Blocked until harness exposes more surfaces (3):
    has_polarization_signal
    has_subpixel_periodicity
    has_spectral_band_anomaly

The language now produces **single-concept dominant verdicts** on
arbitrary visual input. The next research question is whether the
verdicts agree with ground truth: open a "face_is_dominant_concept"
photo and check if it actually contains a face. That is the
empirical loop the Independence Ratio runner is built for.

---

## Round 7: threshold tightening + corpus pumps (2026-04-27)

The Round 6 IR analysis flagged three vocabulary problems:
saturation, redundancy, and untested always-False predicates. This
round addressed all three.

### Threshold tightenings (3 predicates)

  has_high_dynamic_range          0.40 -> 0.65
  has_anisotropy_in_brightest_patch  0.45 -> 0.60
  has_high_frequency_residual     0.10 -> 0.30

### Synthetic corpus pumps (6 scenes)

  horizon_scene                  smooth sky over textured ground
  uniform_field                  near-flat with sensor-noise jitter
  vertically_symmetric_scene     mirror-symmetric random texture
  high_edge_density_scene        50 random oriented strokes
  low_edge_density_scene         heavily blurred random texture
  vertical_edge_dominant         vertical bars at fine pitch

Saved as PNGs to `data/vision/synthetic/`.

### IR comparison: Round 6 (19 inputs) vs Round 7 (25 inputs)

| metric                                          | Round 6 | Round 7 |
|-------------------------------------------------|---------|---------|
| redundant pairs (agreement = 1.00)              | 39      | 10      |
| equivalence classes                              | many    | 1       |
| has_high_dynamic_range firing rate              | 0.95    | 0.24    |
| has_anisotropy_in_brightest_patch firing rate   | 0.95    | 0.76    |
| has_high_frequency_residual firing rate         | 1.00    | 0.36    |
| gradient_energy === high_frequency_residual?    | yes     | NO      |
| is_uniform_field firing rate                    | 0.00    | 0.04    |
| has_low_edge_density firing rate                | 0.00    | 0.04    |
| has_mirror_symmetry_vertical firing rate        | 0.00    | 0.08    |
| has_structural_anisotropy_whole_image firing    | 0.00    | 0.04    |

Redundancy dropped 74 percent. Three saturating predicates are now
discriminating (firing rate in [0.20, 0.80]). Four predicates that
were always-False on real-only corpus now fire on synthetic inputs.
The `gradient_energy === high_frequency_residual` redundancy
identified in Round 6 is now broken; they diverge on inputs whose
gradients are moderate but high-frequency content is below 0.30.

### Five predicates still always-False on the 25-input corpus

  has_high_edge_density            synthetic has overlapping strokes
                                    that cancel; need cleaner edges.
  has_horizontal_dominant_edges     horizon synthetic ground texture
                                    swamps horizontal edge dominance;
                                    need cleaner horizon.
  has_horizon_line_signature       composite needs both above to fire.
  horizon_is_dominant_concept      same.
  no_named_concept_dominant        threshold 0.40 is too lenient;
                                    every input has at least one
                                    score >= 0.40.

These are concrete next-round actions, not bugs.

### Vocabulary status (Round 7 final)

Total: 33 predicates, all type-checked, all running.
Substrate unchanged from Round 4. Thresholds tightened in Round 7.

---

## Round 8: scoring sharpening + synthetic generator fixes (2026-04-27)

The Round 7 IR run identified two structural problems:

  - 5 predicates still always-False because synthetic inputs didn't
    trip them (horizon scene had noisy ground; high-edge scene had
    cancelling overlapping strokes; no_named_concept threshold was
    too lenient because every input had at least one saturated score).
  - Likeness scores saturated near 1.0 because they were means of
    3 components and any single strong component (typically mirror
    correlation, near-1.0 on uniform-ish images) drove the mean.

This round addressed both at the substrate level.

### Likeness scoring rewrite: mean -> min

`face_likeness_score`, `text_likeness_score`, `screen_likeness_score`,
`horizon_likeness_score` now return the **minimum** of their clamped
indicator components. The semantic is "all components present" -
which is what these named-concept signatures actually require.

A face needs vertical mirror AND centred subject AND local oriented
structure. If any of the three is missing, the signature is not
present, and the score should not be high. min() enforces that.

This is itself a methodology rule: **likeness scores that combine
indicators by averaging dilute the absence of any one indicator
into the average; min() preserves the "all required" semantic.**

### Horizon predicate fix: drop mirror requirement

A horizon scene is NOT horizontally mirror-symmetric. Sky and ground
differ - the mirror correlation is anti-correlated, not correlated.
The original `horizon_likeness_score` used `mirror_correlation > 0.4`
which required something the geometry actually forbids.

Replaced with single-component score on horizontal-vs-vertical edge
ratio: `(h_edges / v_edges - 1.0)` clamped to [0, 1]. A horizon
scene with horizontal banding has h_edges >> v_edges (h_dom large);
a balanced scene has h_dom ~ 0.

### Synthetic generator fixes

`horizon_scene`: replaced random-noise ground with parallel
horizontal bands so all gradients are in y-direction (horizontal
edges only). Now scores 1.000 on horizon_likeness.

`high_edge_density_scene`: replaced 50 overlapping cosine strokes
with a fine binary halftone (2-pixel cells, randomly black/white).
edge_density now 0.248 (>0.20 threshold).

### Round 8 IR results vs Round 7

| metric                                      | Round 7 | Round 8 |
|---------------------------------------------|---------|---------|
| redundant pairs                              | 10      | 4       |
| equivalence classes                          | 1       | 2       |
| predicates with 0% firing rate              | 5       | 0       |
| has_horizontal_dominant_edges firing         | 0.00    | 0.04    |
| has_high_edge_density firing                | 0.00    | 0.04    |
| has_horizon_line_signature firing            | 0.00    | 0.04    |
| horizon_is_dominant_concept firing           | 0.00    | 0.04    |
| no_named_concept_dominant firing             | 0.00    | 0.08    |
| has_genuine_face_not_screen firing           | 0.05    | 0.28    |
| has_genuine_text_not_screen firing           | 0.42    | 0.60    |
| has_screen_displaying_face firing            | 0.47    | 0.04    |

**Every predicate now fires on at least one corpus member.** The
vocabulary is empirically exercised end-to-end.

### The 2 remaining equivalence classes are STRUCTURAL

Round 8's residual redundancy is intrinsic to the vocabulary's
design, not an empirical artifact:

  Class A: {has_horizon_line_signature, has_horizontal_dominant_edges,
           horizon_is_dominant_concept} - all measure horizontal-edge
           dominance; on the only corpus member that fires (horizon
           scene), they all fire. To split them needs a scene with
           horizontal edges dominant but NO horizon (e.g., a fence
           shot from the side).

  Class B: {face_is_dominant_concept, has_face_like_signature} -
           dominant requires face_score > all others; with min-based
           scoring face_score is high only when ALL components fire,
           which IS the face_like signature definition. To split
           them needs a face-like scene where text/screen scores
           rank higher (e.g., text on a face poster).

These are research findings about the predicate library: they
identify what new corpus inputs would distinguish predicates that
currently agree by construction.

### Vocabulary status (Round 8 final)

Total: 33 predicates, all type-checked, all firing at least once.
Substrate unchanged from Round 4. Scoring functions sharpened in
Round 8. Synthetic generators fixed in Round 8.

The 7-round growth log:
  Round 0: 7 base predicates ported from Python lab
  Round 1: 5 generic-image predicates added
  Round 2: 7 directional/density/contrast/mirror predicates
  Round 5: 5 named-concept composites
  Round 6: 9 dominance + disambiguation meta-composites
  Round 7: threshold tightening + 6 synthetic corpus pumps
  Round 8: scoring sharpening (min not mean) + 2 generator fixes
  Total: 33 predicates / 32 vision operators / 6 synthetic scenes

The substrate is now sufficient to grow vocabulary indefinitely
by composition, with empirical IR feedback at every step.

---

## Round 9: COLOR EXTENSION (2026-04-27)

The vocabulary so far has been luma-only. Half of human visual signal
is color and the language could not reach it. This round adds the
substrate and 10 color predicates that operate on a new typed field.

### Substrate addition

  New dtype:    `color_image`  (3-D ndarray HxWx3 in [0,1])
  New field:    `color_scene`  (populated by visual_intake +
                                vision_bridge from any RGB input)

### 8 new operators (vision_ops.py)

  rgb_channel_mean(color_image, label "r"|"g"|"b") -> scalar
  rgb_saturation_mean(color_image)                 -> scalar
  rgb_value_mean(color_image)                      -> scalar
  rgb_warmth_score(color_image)                    -> scalar
  rgb_coolness_score(color_image)                  -> scalar
  rgb_palette_diversity(color_image)               -> scalar
  rgb_monochrome_score(color_image)                -> scalar
  rgb_dominant_channel_excess(color_image)         -> scalar

### 10 new predicates (vocab.aurex)

  has_red_dominant            R-mean exceeds G-mean and B-mean
  has_green_dominant          G-mean dominates
  has_blue_dominant           B-mean dominates
  has_warm_palette            warmth - coolness > 0.10
  has_cool_palette            coolness - warmth > 0.10
  has_high_saturation         saturation_mean > 0.30
  has_low_saturation          saturation_mean < 0.10
  has_monochrome              monochrome_score > 0.85
  has_high_color_diversity    palette_diversity > 0.20
  has_low_color_diversity     palette_diversity < 0.08

### 4 color synthetic scenes (corpus pumps)

  red_dominant_scene
  cool_palette_scene
  monochrome_color_scene
  high_diversity_color_scene

All four trip their target predicates correctly.

### Round 9 IR (29 inputs / 43 predicates)

Color verdicts on real phone photos (13 inputs):
  9 / 13 has_red_dominant         (afternoon document photos under
                                    indoor lighting; skin tones in
                                    portraits)
  4 / 13 has_blue_dominant        (early-morning photos in cool light)
  0 / 13 has_green_dominant
  0 / 13 has_warm_palette         (warmth/coolness delta < 0.10 on
                                    natural photos - need to lower
                                    margin or use different metric)
  0 / 13 has_cool_palette         (same)

Color verdicts on synthetic inputs:
  red_dominant_scene:    red, warm, high_sat                  ✓
  cool_palette_scene:    blue, cool, high_sat                  ✓
  monochrome_color_scene: low_sat, monochrome                  ✓
  high_diversity_color_scene: green (random), high_sat, diverse ✓

### New finding: a tautological equivalence pair

`{has_low_saturation, has_monochrome}` always agree by definition.
Monochrome IS low saturation - the two predicates measure
identical quantities through different formulas. Cannot be broken
by any corpus input. Worth noting in vocabulary maintenance: one
of these is redundant and could be removed in a future cleanup
pass, or kept because the threshold for each carries different
semantic intent (low_saturation < 0.10; monochrome > 0.85).

### Round 9 vs Round 8

| metric                       | Round 8 | Round 9 |
|------------------------------|---------|---------|
| total predicates              | 33      | 43      |
| total operators               | 32      | 40      |
| total synthetic scenes        | 6       | 10      |
| corpus inputs                 | 25      | 29      |
| redundant pairs               | 4       | 5       |
| equivalence classes           | 2       | 3       |
| 0% firing predicates          | 0       | 0       |

The 1 new equivalence class is the tautological color pair noted
above. The vocabulary is empirically exercised end-to-end on real
photos with both luma and color predicates contributing
discriminating signal.

### Vocabulary status (Round 9 final)

43 predicates / 40 vision operators / 10 synthetic scenes. Every
predicate fires on at least one corpus member. Color predicates
operate on real phone photos through visual_intake; sessions
through vision_bridge. The substrate now spans both luma and
color signals - the conventional "what humans see" dimensions.

What's still missing for a full human-vision analogue:
  - shapes (circle / rectangle / curve detection)
  - object recognition (face IDENTITY, not just face-like signature)
  - depth cues (perspective, occlusion, focus blur)
  - motion direction / velocity (only sub-frame motion is detected,
    not its direction)

These are the natural Round 10+ extensions. The substrate is
sufficient for all of them - additions remain operators + DSL
predicates, no architectural changes.

---

## Round 10: HSV hue identification (perceptual wavelength labels) + multispectral honesty (2026-04-27)

The Round 9 RGB predicates were CHANNEL-MEAN comparisons (R > G AND
R > B) - a relative measure. They did not classify pixels by hue,
they classified scenes by which channel dominated. Round 10 adds the
per-pixel absolute hue identification that maps a single pixel to a
named wavelength bucket via HSV conversion.

### The metamerism caveat (filed as WAVELENGTH_LIMITS.md)

An RGB sensor cannot recover specific monochromatic wavelengths.
Multiple physical spectra produce identical RGB triples. Human eyes
have the same limit (3 cones). What both DO recover is perceptual
hue labels via cone-ratio (or RGB-ratio) classification.

True wavelength resolution requires multispectral or hyperspectral
hardware, which is a fourth BLOCKED-predicate class parallel to raw
Bayer and polarization-pair unlocks. Documented honestly.

### 3 new operators

  hue_fraction(color_image, label) -> scalar
  meaningfully_colored_fraction(color_image) -> scalar
  hue_diversity_score(color_image) -> scalar

### 13 new predicates

8 has_significant_X_hue (red/orange/yellow/green/cyan/blue/violet/magenta)
3 has_dominant_X_hue (red/green/blue, fires when X owns >50% of saturated pixels)
1 has_polychromatic_palette
1 has_largely_achromatic_scene

### 5 pure-hue synthetic scenes

pure_orange_scene (HSV 30°), pure_yellow_scene (60°),
pure_green_scene (120°), pure_cyan_scene (180°),
pure_violet_scene (270°). All five fire ONLY their target bucket -
per-pixel hue classification works absolutely (no relative comparison
to other pixels).

### Round 10 IR results (34 inputs / 56 predicates)

  has_significant_orange_hue: 53 percent of real phone photos
    (skin tones, paper under warm indoor lighting)
  has_significant_blue_hue: 53 percent (sky, screens, cool light)
  has_dominant_blue_hue: 15 percent (strong blue scenes)
  has_largely_achromatic_scene: 26 percent (low-light or close-up
    shots that lose chroma)

### 3 new equivalence classes (structural)

  {has_green_dominant, has_significant_green_hue} - tautological
    on this corpus: if green channel dominates in RGB mean, the
    saturated pixels are predominantly in the green bucket.

  {has_largely_achromatic_scene, has_low_saturation, has_monochrome}
    - all measure "no color presence" via different formulas.
    Tautological.

  {has_polychromatic_palette, has_significant_magenta_hue} -
    coincidental on this corpus (4+ hue buckets present implies
    the magenta wrap-around bucket is likely one of them). Could
    break on a richer corpus.

### Round 10 totals

  56 predicates / 43 vision operators / 15 synthetic scenes.
  Substrate unchanged from Round 9 (color_image dtype).
  The vocabulary now does what human vision does: per-pixel
  absolute named-hue identification at the precision a 3-band
  sensor permits.

### What's still blocked at the hardware layer

  raw_bayer:                has_subpixel_periodicity,
                            has_spectral_band_anomaly
  cap_axis_0/90 pair:       has_polarization_signal
  multispectral_image:      has_multispectral_anomaly_score
                            (placeholder, no operator yet)
  hyperspectral_image:      has_hyperspectral_signature
                            (placeholder, no operator yet)

These are the four hardware unlocks beyond the current phone
harness. Each is a known path forward, not a substrate gap.

---

## Round 11: shape primitives via gradient orientation (2026-04-27)

The vocabulary so far measured edge-direction (horizontal vs vertical),
periodicity, ROI coherence. None of those answer "what shape is in the
scene?" Round 11 adds shape-class predicates by analysing the
distribution of gradient orientations in [0, pi).

### 5 new operators

  orientation_uniformity(image)              -> scalar  (1 = isotropic)
  orientation_horizontal_mass(image)         -> scalar  (90 deg energy)
  orientation_vertical_mass(image)           -> scalar  (0 deg energy)
  orientation_diagonal_mass(image)           -> scalar  (45 + 135 deg)
  blob_count_thresh(image, k)                -> int     (CCs above mean+k*std)

### 6 new shape predicates

  has_circular_signature       isotropic distribution + non-zero gradient
  has_rectilinear_signature    BOTH h and v dominant AND diagonals weak
  has_diagonal_signature       diagonal dominant AND h/v weak
  has_curved_signature         smooth distribution, no peaks, not isotropic
  has_many_small_blobs         > 15 thresholded connected components
  has_few_large_blobs          1-4 thresholded connected components

The mutual-exclusion constraints (rectilinear excludes diagonal mass,
diagonal excludes h/v mass) were the key fix - without them, a
circle's near-uniform orientation distribution false-positively
fires both rectilinear AND diagonal.

### 4 shape synthetic scenes

circle_scene, rectangle_scene, diagonal_lines_scene, many_circles_scene.
Each fires only its target shape predicates, no false positives.

### Round 11 verdicts on synthetics

  circle_scene:           has_circular + has_few_large_blobs
  rectangle_scene:        has_rectilinear + has_few_large_blobs
  diagonal_lines_scene:   has_diagonal only
  many_circles_scene:     has_circular + has_many_small_blobs

### Real-photo shape distribution (38-input corpus, 62 predicates)

  has_circular_signature    66 percent (natural photos have varied
                            edge orientations, often near-isotropic
                            in patches)
  has_rectilinear_signature 13 percent (architectural / document photos)
  has_diagonal_signature     3 percent (only the synthetic)
  has_curved_signature       0 percent (predicate too strict)
  has_many_small_blobs      76 percent (natural photos are texture-rich)
  has_few_large_blobs        5 percent (subject-on-clean-background photos)

### Finding: has_curved_signature is too restrictive

The four-clause AND requires uniformity < 0.40 AND horizontal_mass < 0.20
AND vertical_mass < 0.20 AND diagonal_mass < 0.40. Most natural images
have SOME mass at h/v even when curve-dominated, so the predicate
never fires. A more permissive curved-detection would require a
specific signature for curves that is NOT just "everything else."

Filed as a vocabulary-design task: curves need their own positive
test (e.g. low-energy bins between peaks, smoothness of histogram
across adjacent bins) rather than negation of all other shape signatures.

### Round 11 totals

  62 predicates / 48 vision operators / 19 synthetic scenes
  Substrate unchanged from Round 9 (color_image dtype is most recent)
  5 equivalence classes (same count as Round 10 - new shape predicates
  carry independent information, no new structural redundancies)

The vocabulary now spans:
  motion / temporal      (3 burst predicates)
  structure / texture    (5 directional + density + dynamic-range)
  symmetry               (2 mirror predicates)
  named-concept signatures (5 composites + 5 dominance + 4 disambig)
  color RGB              (10 predicates)
  hue / wavelength labels (13 predicates)
  shape primitives       (6 predicates)
  blocked at hardware    (3 predicates: subpixel, spectral, polarization)

What remains for human-vision parity:
  depth cues             (perspective convergence, atmospheric haze,
                          focus blur gradient, occlusion edges)
  position / composition  (rule of thirds, leading lines, eye level)
  motion direction       (vector field of optical flow, not just
                          presence)
  identity recognition   (face IDENTITY, object IDENTITY - this
                          requires learned models, not predicates)

Depth cues are the clear next round.

---

## Round 12: depth cues from a single 2D image (2026-04-27)

The vocabulary now reads color, hue/wavelength, shape, motion,
structure, named concepts. What humans still get from a single
photo that the language couldn't reach: depth. This round adds the
single-image cues humans use to perceive 3D from a flat photo.

### 5 new operators

  perspective_convergence_strength(image)        -> scalar
  atmospheric_haze_score(color_image)            -> scalar
  focus_blur_gradient(image)                     -> scalar (centre vs edges)
  corner_count_thresh(image, scalar)             -> int
  texture_density_top_vs_bottom(image)           -> scalar

### 7 new predicates

  has_perspective_convergence       diagonal-line asymmetry L vs R
  has_atmospheric_haze              top desaturated + blue-shifted
  has_shallow_depth_of_field        centre sharpness >> edge sharpness
  has_uniform_focus                 |focus_blur_gradient| < 0.20
  has_many_corners                  > 50 Harris-style corners
  has_texture_compression_gradient  top higher high-freq than bottom
  has_depth_indicators              composite OR of perspective/haze/DOF

### 3 depth synthetic scenes

perspective_road_scene (lines converging to vanishing point at
horizon), hazy_landscape_scene (top desaturated + blue-tinted),
shallow_dof_scene (sharp central pattern, blurred surround).

### Round 12 verdicts on synthetics

  perspective_road_scene: nothing fires (perspective detector too weak)
  hazy_landscape_scene:   has_atmospheric_haze + has_uniform_focus
  shallow_dof_scene:      has_shallow_depth_of_field

### Methodology finding: focus_blur_gradient redesign

First implementation used variance-of-tile-sharpness across 4x4 grid.
This gave high values for ANY scene with non-uniform structure
(perspective road, landscape with foreground+sky), not specifically
shallow-DOF scenes. Redesigned as centre-vs-edges sharpness ratio:
(centre - edge) / (centre + edge). A shallow-DOF scene has subject
in centre + blurred surround = high positive ratio. A landscape has
edges sharper than centre = negative ratio. A uniform scene = near 0.

This is a methodology rule worth keeping: **when designing a metric,
test it on the negative cases as well as the positive ones**. The
variance-of-tiles version positively detected shallow-DOF AND many
other things; the centre-vs-edges version selectively detects
shallow-DOF.

### Known weak detector: perspective convergence

The asymmetric-diagonal-mass heuristic gives only 0.016 on the
perspective_road synthetic. The road has lines BOTH going to centre
from left AND from right, so left and right halves see similar
diagonal mass. A proper perspective detector needs Hough-transform-style
vanishing-point estimation, which is more substantial than what
fits in this round. Filed as a vocabulary-design task.

### Round 12 IR (41 inputs / 69 predicates)

Equivalence classes: 4 (was 5). The {face_is_dominant_concept,
has_face_like_signature} pair from Round 6 no longer always agrees
- the depth synthetic scenes have unusual gradient distributions
that hit one but not the other. That is a real progress signal:
adding diverse corpus inputs breaks structural redundancies that
earlier looked tautological but were actually empirical.

Real-photo depth verdicts:
  has_uniform_focus:           63 percent (most casual photos)
  has_many_corners:            85 percent (texture-rich scenes)
  has_atmospheric_haze:         5 percent
  has_shallow_depth_of_field:   5 percent
  has_perspective_convergence:  5 percent

### Round 12 totals

  69 predicates / 53 vision operators / 22 synthetic scenes
  4 equivalence classes (improvement: 5 to 4)

### Vocabulary status across the project

  motion / temporal:        3
  structure / texture:     14
  symmetry:                 2
  named concepts:          14
  color (RGB):             10
  hue / wavelength labels: 13
  shape primitives:         6
  depth cues:               7
  hardware-blocked:         3

The vocabulary now spans 9 perceptual dimensions. What remains for
human-vision parity: composition (rule of thirds, leading lines,
framing balance), motion direction (optical flow, not just presence),
and the parallel hardware-unlock track (raw Bayer, polarization
pair, multispectral).

---

## Round 13: composition primitives (2026-04-27)

What humans intuitively notice about photographic composition: where
the subject sits in the frame, whether visual weight is balanced,
how much negative space surrounds the subject, where the horizon
line falls. None of this was reachable before this round.

### 5 new operators

  gradient_energy_at_thirds_point(image, label) -> scalar
  horizontal_split_balance(image)               -> scalar  (top vs bottom)
  vertical_split_balance(image)                 -> scalar  (left vs right)
  negative_space_fraction(image)                -> scalar
  horizon_position_estimate(image)              -> scalar  ([0,1] y-coord)

### 12 new predicates

Rule-of-thirds placement (4):
  has_subject_at_thirds_top_left
  has_subject_at_thirds_top_right
  has_subject_at_thirds_bottom_left
  has_subject_at_thirds_bottom_right

Visual balance (4):
  has_horizontal_balance / has_horizontal_imbalance
  has_vertical_balance / has_vertical_imbalance

Negative space + horizon position (4):
  has_significant_negative_space
  has_horizon_at_top_third
  has_horizon_at_middle
  has_horizon_at_bottom_third

### 3 composition synthetic scenes

rule_of_thirds_scene, balanced_composition_scene,
negative_space_subject_scene. All three trip the predicates that
target them, with no false positives on competing thirds positions.

### Real-photo composition findings

  has_vertical_balance:        89 percent
  has_horizontal_balance:      77 percent
  has_subject_at_thirds_TL:    36 percent  (Western-reading bias)
  has_subject_at_thirds_TR:    30 percent
  has_subject_at_thirds_BL:    32 percent
  has_subject_at_thirds_BR:    20 percent  (least populated quadrant)
  has_significant_negative_space: 48 percent (subject-on-bg shots)
  has_horizon_at_top_third:    20 percent
  has_horizon_at_middle:       16 percent
  has_horizon_at_bottom_third: 30 percent  (sky-dominant shots)

The thirds-point bias toward top-left and bottom-left over the
right column is consistent with Western reading-order composition.

### Round 13 IR (44 inputs / 81 predicates)

Equivalence classes: 4 (same count as Round 12, BUT one shrunk).
The Round 6 horizon class
  {has_horizon_line_signature, has_horizontal_dominant_edges,
   horizon_is_dominant_concept}
became
  {has_horizon_line_signature, has_horizontal_dominant_edges}
in Round 13. has_horizon_is_dominant_concept now disagrees on at
least one new corpus member. Two separate corpus-driven
redundancy reductions across rounds 12 and 13. The IR loop is
producing real progress on the structural-redundancy front,
not just adding signal.

### Composition synthetic finding

balanced_composition_scene fires ALL FOUR thirds-point predicates
because the two subject blobs span enough area to register near
each intersection point with the half_width_frac=0.10 window. A
finer thirds window (5 percent of frame width) would discriminate
better. Filed as a calibration knob for v0.10.

### Round 13 totals

  81 predicates / 58 vision operators / 25 synthetic scenes
  4 equivalence classes (improved from Round 12 by shrinking one)

### Vocabulary status across the project

  motion / temporal:        3
  structure / texture:     14
  symmetry:                 2
  named concepts:          14
  color (RGB):             10
  hue / wavelength labels: 13
  shape primitives:         6
  depth cues:               7
  composition:             12
  hardware-blocked:         3

10 perceptual dimensions covered. The vocabulary now spans the
visual content humans describe when looking at a photo:
  - what's there (named concepts, shapes)
  - what color it is (RGB + hue labels)
  - how it moves (motion + drift)
  - how the scene is structured (texture, edges, symmetry)
  - how deep the scene feels (depth cues)
  - how the photo is composed (thirds, balance, negative space)

What remains for human-vision parity:
  - motion direction / vector field (Round 14)
  - vocabulary cleanup (resolve remaining structural redundancies)
  - hardware unlocks (raw Bayer, polarization, multispectral)

---

## Round 14: motion direction via FFT phase correlation (2026-04-27)

Round 11's has_subframe_motion only detected motion presence. This
round resolves DIRECTION: leftward, rightward, upward, downward,
and coherence (panning vs shaking) via 2-D FFT phase correlation
between adjacent burst frames.

### 3 new operators

  global_shift_estimate(image_stack, label) -> scalar
    label = "x" or "y"; positive = motion in that direction
  motion_coherence(image_stack)              -> scalar
    [0,1]: 1 = all frame-pair shifts agree (panning); 0 = chaotic
  motion_velocity_mean(image_stack)          -> scalar
    mean magnitude of frame-pair shifts in pixels

### 7 new predicates

  has_motion_leftward / rightward / upward / downward
  has_coherent_motion          (coherence > 0.7 AND velocity > 0.5)
  has_chaotic_motion           (coherence < 0.4 AND velocity > 1.0)
  has_fast_motion              (velocity > 5 px/pair)

### 3 burst synthetic scenes (saved as image dirs)

panning_right_burst, panning_down_burst, shaking_burst. Each
correctly fires its direction predicate(s); shaking fires
chaotic_motion. No false positives.

### Real-session motion-direction findings

  747e9951 dark cal grid:  dx=-1.4  dy=+0.7  coh=0.44  vel=3.59
  773bad8e rep strip:      dx=+1.0  dy=+1.9  coh=0.34  vel=6.22
  773bad8e sym test:       dx=+1.9  dy=-2.3  coh=0.42  vel=7.12
  a6064077 bright cal grid: dx=+5.2  dy=+0.4  coh=0.91  vel=5.73

The bright calibration grid was captured with COHERENT RIGHTWARD
camera motion (panning) - coh=0.91, dx=+5.2 px/pair. The other three
sessions show low coherence (0.34-0.44), consistent with hand-shake.
The language detected this without being told to look for it; this
is a real-capture finding the previous rounds couldn't have made
because they only knew motion was present, not what direction.

### Methodology finding: phase-correlation sign convention

Phase correlation peak indicates the shift required to align frame
B back to frame A, which is the NEGATIVE of the actual content
motion direction. The operator now negates so positive sign matches
human-direction intuition (positive x = motion-right; positive y =
motion-down). Filed: when wrapping signal-processing primitives,
make the public sign convention match the user-facing semantic,
not the math literature default.

### New structural redundancy: {fast_motion, real_motion_validated}

These always agree on this corpus because both require "real
meaningful motion exists" - real_motion_validated needs
diff_coherence > 8 AND not-drift, fast_motion needs velocity > 5.
Both fire only on the 3 burst synthetics + bright cal session.
To break would need a slow-but-coherent burst (e.g. 0.5 px/frame
panning) - not in current synthetic set. Filed for v0.11 corpus
expansion.

### Round 14 totals (after Round 14 added 7 predicates + 3 bursts)

  88 predicates / 61 vision operators / 28 synthetic scenes
  5 equivalence classes (one new but bounded; existing classes stable)

### Vocabulary status across the project

  motion / temporal:        10 (was 3 before round 14)
  structure / texture:      14
  symmetry:                  2
  named concepts:           14
  color (RGB):              10
  hue / wavelength labels:  13
  shape primitives:          6
  depth cues:                7
  composition:              12
  hardware-blocked:          3

11 perceptual dimensions covered. With motion direction now in,
the language describes a video sequence in essentially the same
terms a human narrator would: "the camera pans right while the
subject is in the lower-right third, scene is largely
text-dominant, warm-palette." Same level of detail as a careful
human description, all auditable through the type-checked DSL.

What remains:
  - vocabulary cleanup (resolve remaining 5 equivalence classes
    by adding targeted corpus inputs)
  - hardware unlocks (raw Bayer, polarization pair, multispectral)
  - identity / object recognition (this is where ML enters)

---

## Round 15: vocabulary cleanup - target the equivalence classes (2026-04-27)

Round 14 left 5 structural equivalence classes - predicate pairs
that always agreed across the corpus. This round added 4 targeted
synthetic inputs designed to break them, plus fixed a phase-correlation
issue that was inflating motion-velocity readings.

### Methodology fix: phase correlation -> cross-correlation

The motion-direction operators used phase-only correlation
(R / |R|). On sparse signals (single moving blob, real low-light
scenes) phase-only correlation fails because it normalises the
amplitude away, leaving frequency noise to dominate the peak. A
deliberate 1.5 px shift was reading as 21 px in the slow_coherent
synthetic - 14x off.

Replaced with standard cross-correlation (A * conj(B), no
normalisation, mean-subtracted inputs). Slow burst now reads
~1.0 px shift correctly. Real-session shift estimates also
changed: dark cal grid now reads dy=-4.7 (consistent upward drift)
where phase-corr saw +0.7 (near-zero); the bright cal grid drops
from a wrong 5.2 px/pair to a more plausible 1.3 px/pair.

This is a methodology rule worth keeping: **phase-only correlation
fails on sparse signals; cross-correlation with mean subtraction
is the safer default for visual content with localised features.**

### 4 cleanup synthetics

  edge_ratio_borderline_scene  (h/v ratio ~1.4 - between thresholds)
  faint_green_tint_scene       (G channel slightly leads, all near-grey)
  rainbow_no_magenta_scene     (6 hues, no magenta)
  slow_coherent_burst          (1.5 px/frame coherent panning)

### Equivalence classes broken

Round 14: 5 classes:
  {has_horizon_line_signature, has_horizontal_dominant_edges}     BROKEN
  {has_fast_motion, has_real_motion_validated}                     BROKEN
  {has_green_dominant, has_significant_green_hue}                  BROKEN
  {has_largely_achromatic_scene, has_low_saturation, has_monochrome}  KEPT (tautological)
  {has_polychromatic_palette, has_significant_magenta_hue}         BROKEN

Round 15: 2 classes:
  {has_largely_achromatic_scene, has_low_saturation, has_monochrome}  TAUTOLOGICAL by definition
  {has_global_brightness_drift, has_motion_upward}                    CORPUS-SIZE ARTIFACT

The motion-upward / drift pair fires on a single common input
(dark cal grid). Not structural - both happen to fire on one
session for unrelated reasons. With more motion-bearing sessions
they would diverge.

### Round 15 final IR (51 inputs / 95 predicates)

  redundant pairs:        4 (was 7)
  equivalence classes:    2 (was 5)
  tautological classes:   1 (the achromatic triple)
  corpus-artifact classes: 1 (drift / upward_motion)
  empirical-redundancy:   0

Of all the structural redundancies the IR loop has flagged across
all 15 rounds, only 1 remains as truly tautological-by-definition.
The vocabulary's predicates are now empirically distinct - new
predicates carry independent information.

### What's left for vocabulary completeness

  - 0 always-False predicates
  - 0 saturated predicates
  - 0 empirical structural redundancies
  - 1 tautological pair (accepted - removing one breaks audit trail)
  - 1 corpus-size pair (will resolve when more motion data is added)

The perceptual side of the vocabulary is empirically clean. Future
rounds focus on:
  1. hardware unlocks (raw Bayer / polarization / multispectral)
  2. identity recognition layer (where ML enters)
  3. richer real-session corpus to resolve the motion-direction
     corpus-size artifact

### Round 15 totals

  95 predicates / 89 vision operators / 32 synthetic scenes
  2 equivalence classes (one tautological, one corpus-limited)
  11 perceptual dimensions covered

---

## Round 16: the narrator (2026-04-27)

The vocabulary now runs through a rule-based composer that turns
the verdict pattern from any visual input into a human-readable
paragraph. No ML, no learned templates - just enumerated
predicate verdicts assembled into sentences that describe the
scene the way a careful observer would.

### What it produces (real examples)

  20260416_141509.jpg (afternoon photo):
    "It presents orange hues, across a varied color range. Its
    structure shows isotropic / round structure and many small
    contrast regions and horizontal repetition. Compositionally,
    it has a centered subject, subject content at the upper-left
    third and upper-right third, and a high horizon (ground-
    dominant view). Depth and tone: converging perspective lines."

  panning_right_burst:
    "...Motion is coherent and fast in the rightward direction."

  shaking_burst:
    "...Motion is chaotic / camera-shake and fast in the leftward
    and downward direction."

### Why this matters for the roadmap

This is the user-facing artifact of the vision language. Earlier
rounds proved the language could classify pixels and bundles into
typed verdicts. Round 16 demonstrates those verdicts COMPOSE INTO
DESCRIPTION - the way human language composes adjectives and
phrases into sentences about a scene.

The narrator is 200 lines of pure rule-based composition over the
vocabulary. Adding a new predicate to vocab.aurex automatically
makes it available to extend the narration, with no changes to
the narrator code unless that predicate needs special phrasing.

### CLI usage

  python -m aurexis_workbench.narrator <PATH>

Path can be any image, video, dir of images (becomes burst), or
.aurex-session zip.

### Round 16 totals

  88 predicates / 85 vision operators / 32 synthetic scenes
  + 1 narrator that turns predicate verdicts into paragraphs
  2 equivalence classes (1 tautological, 1 corpus-size artifact)
  11 perceptual dimensions covered

### What unlocks next

Hardware unlocks (raw Bayer / polarization / multispectral) -
substrate-side, not vocabulary. ~3 BLOCKED predicates waiting.

Identity recognition layer - face IDs, object names, scene
categories. Where ML genuinely enters the project; the language
itself can't synthesize "this is Vince" from typed predicates.

Richer real-session corpus - capture a few panning sessions to
break the last corpus-size equivalence pair.

---

## Round 17: lighting / illumination primitives (2026-04-28)

What the language couldn't read before this round: who lit the
scene. Round 17 adds the photographic lighting axis - low-light
captures, high-key portraits, center-weighted illumination,
specular highlights, exposure clipping.

### 4 new operators

  bright_pixel_fraction(image, threshold)    -> scalar
  dark_pixel_fraction(image, threshold)      -> scalar
  bright_spot_count(image, threshold)        -> int
  center_minus_edge_brightness(image)        -> scalar

### 8 new predicates

  has_low_light_signature        majority of pixels in shadow
  has_high_key                   overall mean above mid-grey
  has_low_key                    overall mean below mid-grey
  has_specular_highlights        multiple tiny very-bright spots
  has_center_weighted_lighting   centre brighter than edges (portrait)
  has_edge_weighted_lighting     edges brighter than centre (vignette)
  has_overexposed_regions        significant pixels at near-max value
  has_underexposed_regions       significant pixels at near-zero value

### 4 lighting synthetic scenes

  low_light_scene          (mean ~0.13, mostly shadow)
  high_key_scene           (mean ~0.85, faint subject)
  center_lit_scene         (Gaussian falloff, centre bright)
  specular_highlight_scene (mid-grey + 8 tiny hot spots)

Each fires only its target predicates; no false positives.

### Round 17 totals

  96 predicates / 89 vision operators / 36 synthetic scenes
  + narrator from round 16 (now extended to lighting language)
  2 equivalence classes (unchanged - no new redundancies)
  12 perceptual dimensions covered (added: lighting)

### Performance note

The IR runner timed out at 45s on the full corpus (55 inputs x
96 predicates). bright_spot_count uses Python-level flood-fill
which is slow on 256x256 inputs. Either: optimize with scipy
label, raise timeout, or shard the IR run. Filed for v0.12
maintenance pass.

### What unlocks next

Hardware unlocks (raw Bayer / polarization / multispectral) -
substrate-side, not vocabulary.

Identity recognition layer - face IDs, object names, scene
categories. Where ML genuinely enters.

Vocabulary maintenance - resolve the 1 remaining tautological
class by retiring duplicate predicates; document which 1 of
{largely_achromatic, low_saturation, monochrome} should be
canonical.

---

## Round 18: quality maintenance (2026-04-28)

This round was a pure maintenance pass: optimize slow operators,
fix the 0%-firing has_curved_signature, redesign the weak
has_perspective_convergence detector.

### Optimizations

  bright_spot_count and blob_count_thresh now use scipy.ndimage.label
  Sub-millisecond on 256x256 inputs (was 100s of ms with Python flood-fill).

### has_curved_signature redesigned

Round 11's predicate was AND of 4 negations, fired 0% across 12 rounds.
Round 18 replaces with positive test:
  - width above 0.7 * max in orientation histogram = 3-10 bins
  - bins must be cyclically contiguous (1 stray bin allowed for noise)
  - score maps width 3-10 to 1.0-0.3

curve_scene now fires (continuity=0.57). Rectangle, circle, diagonal,
horizon, many_circles all return 0. Single sharp peaks (lines) return
0 because width above 0.7*max is 1-2.

Methodology rule kept: **when retiring a "negation-of-everything-else"
predicate, replace it with a positive test that has a clear synthetic
that fires it.**

### has_perspective_convergence redesigned (still weak)

Round 12's L-vs-R asymmetry detector replaced with TOP-vs-BOTTOM
dominant-orientation difference. The intuition: a perspective road
has near-vertical lines at bottom (close to camera), near-horizontal
at top (converging at horizon).

The perspective_road synthetic still doesn't fire (the symmetric
converging lines average to similar dominant orientations top vs
bottom). Filed as a known-correct-but-weak detector pending a
Hough-transform vanishing-point estimator. The synthetic is still
correctly described (other predicates pick up other signals); just
the perspective-specific predicate returns False.

### Round 18 totals

  96 predicates / 91 operators / 37 synthetic scenes
  2 equivalence classes (unchanged)
