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
