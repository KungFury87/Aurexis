# Vision Language Audit - what Core/Workbench already provides

Date: 2026-04-27

This document was written before extending the Workbench with vision
operators. It records what I found in the existing tree so the
extension is additive and does not duplicate substrate.

## Substrate already shipping in Workbench v2.0/2.1

### Typed field model (`fields.py`)

`VALID_DTYPES = {"image", "scalar", "int", "bool", "regions", "vector", "label"}`

A `FieldSpec(name, dtype, description)` declares a typed slot. A
`FieldValue` carries a concrete value. A `FieldBundle` is a named
dict of FieldValue. Bundles are the input substrate predicates run on.

### Primitive operator registry (`operators.py`)

13 operators registered, each with declared `in_types` / `out_type`:

  image-level: mean, std, threshold, count_components, autocorr_period,
                mirror_correlation, structure_tensor_angle
  comparison:  eq_int, neq_int, lt_int, gt_int, leq_int, geq_int,
                eq, neq, lt, gt, leq, geq
  logic:       AND, OR, NOT
  tolerance:   within, within_int

`register(name, in_types, out_type, fn, doc)` adds a new operator
in one call. The compiler resolves operator names against the
registry and type-checks at compile time.

### Predicate AST + compiler (`predicates.py`)

Three node kinds: `FieldRef(name)`, `Const(value, dtype)`, `Call(op, args)`.
`type_check(pred)` walks the AST against the registry. `compile_predicate`
returns a Python callable `(bundle) -> value`.

### Runtime (`runtime.py`)

Caches compiled predicates, evaluates against bundles, records
EvalRecord objects for downstream Independence-Ratio reporting.

### Surface DSL (`dsl.py`)

```
predicate NAME
  expects FIELD:DTYPE[, FIELD:DTYPE ...]
  returns DTYPE
  intent  IDENT
  body    EXPR
```

Parses to the same AST the substrate type-checks. Failing parses /
type-checks return readable diagnostics with location info.

### Vocabulary store (`vocabulary.py`)

JSON-persisted named set of predicates. `add()` runs type-check
before accepting. Loading a vocabulary into a runtime installs all.

### Starter vocabulary (`starter.py`)

Already-shipped vocabulary derived from the simulator findings:
cardinality (count_eq_N), repetition (period_within_P), symmetry
(mirror_corr_above), orientation (angle_within). These are the
proven baseline.

### Independence Ratio runner (`independence.py`)

The empirical baseline for whether predicates carry independent
information.

## Where the Vision Lab built parallel infrastructure

The Vision Lab's six "surfaces" and seven predicates are functionally
equivalent to Workbench fields and predicates, but they are written
as Python classes and functions rather than DSL text. That is a
structural mistake: the Workbench substrate already provides the
type-checking, compilation, vocabulary, and Independence Ratio
infrastructure that vision needs.

| Vision Lab (Python)                 | Equivalent in Workbench substrate         |
|-------------------------------------|--------------------------------------------|
| BayerSurface(raw)                   | image field plus bayer_R/Gr/Gb/B operators |
| SpectrumSurface.peak_to_floor       | fft_peak_to_floor operator                 |
| GradientSurface                     | gradient operators (do not yet exist)      |
| StructureTensorSurface.coherence    | structure_tensor_coherence operator        |
| TemporalDifferenceSurface           | temporal_diff_* operators on image_stack   |
| RotatedPairSurface                  | rotated_pair_anisotropy operator           |
| has_subframe_motion (Python)        | DSL predicate over temporal ops            |
| has_polarization_signal (Python)    | DSL predicate over rotated_pair op         |
| has_subpixel_periodicity (Python)   | DSL predicate over fft + bayer + block_avg |

## Gaps (additive work needed)

1. **One new dtype**: `image_stack` (a sequence of frames, e.g. a burst).
2. **Vision operators**: bayer_R/Gr/Gb/B, green_imbalance, channel_spread_norm,
   fft_peak_to_floor, fft_peak_radius, block_avg_2x2, temporal_diff,
   temporal_diff_coherence, temporal_uniform_ratio, structure_tensor_coherence,
   max_coherence_patch_coh, rotated_pair_anisotropy, abs_s, div_s.
3. **A vision vocabulary file** (`data/vision/vocab.aurex`) - the 7
   predicates re-expressed as DSL text.
4. **A session bridge** that loads a `.aurex-session` zip into a
   FieldBundle so the Workbench runtime can evaluate vision
   predicates on real captures.

## What this means in practice

The "new language of vision" is NOT a new language. It is the
existing Workbench DSL with vision operators added to its registry.
Predicates are vocabulary entries, not Python functions. The
Independence Ratio runner already knows how to score them. The
type-checker already enforces types. The vocabulary already
persists.

Bootstrapping Core for vision = registering vision operators +
authoring the vocabulary file + plumbing real captures into the
runtime.
