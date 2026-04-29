# Phoxelis Project Charter v1.0

**Last updated:** 2026-04-28 (Round 47)
**This is the load-bearing document.** I (the assistant) re-read this at the
start of every conversation and every round. If anything here turns out to be
wrong, this document is updated explicitly — not silently superseded.

---

## 1. What Phoxelis is

Phoxelis is a **dual-fiber typed predicate calculus** over typed sensor fields.

- **Fiber A — the predicate language.** Compositional, type-checked,
  runtime-verified expressions over a finite set of operators. Each predicate
  is a function from typed signal fields to a boolean (or scalar). Predicates
  compose; the type system enforces correctness; the runtime evaluates them
  against any input that supplies the required fields.
- **Fiber B — the measurement substrate.** Typed fields populated by sensor
  signal — image, image_stack, color_image, scalar, label, int. Each field is
  the output of an actual physical measurement, not a learned representation.

The calculus is **bidirectional**:
- **Forward:** signals → predicates → meaning. Phone photo → field bundle →
  predicate evaluation → semantic verdicts.
- **Backward:** target predicate state → constructive synthesis of signals
  satisfying it. Bit pattern → cell verdicts → pixel content → rendered image.

Both directions use the same vocabulary, the same runtime, the same type
system. The encoder is fiber-B-from-fiber-A. The decoder is fiber-A-from-fiber-B.

## 2. What Phoxelis is for

A perceptual substrate that any computational system can plug into. Meaning
produced through composable measurement rather than learned pattern matching.
Multi-modal by design — every sensor stream is a typed field. The vocabulary
grows by use, audits itself, retires what fails.

The philosophical claim being tested:
> *Meaning can be carried by composable measurements rather than by symbols
> correlated to signal during training.*
> — `on_composable_measurement.md`

The Independence Ratio (IR) is the experimental measurement.

## 3. What Phoxelis is NOT

- A product to ship.
- A QR code competitor on QR's home turf (printed-in-ink camera-decode).
- A learned vision model.
- An LLM (Phoxelis is what an LLM might *use* to make perceptual contact).
- Bound to any specific sensor modality.
- Required to beat any specific capacity benchmark; capacity is one axis
  among several.

If the project starts looking like one of the above, that's drift.

## 4. Architectural layers

Each layer plugs into the same typed-field interface. Predicates can compose
across layers because verdicts at one layer are inputs at the next.

| layer | what | status as of R47 |
|---|---|---|
| **L1 — Sensory invariants** | Predicates over composed measurements on raw signal. Color means, edge density, focus uniformity, exposure, hue presences. Empirically clean over heterogeneous corpora. | Built and audited (103 predicates over 95 operators, IR-clean across 161 images) |
| **L2 — Recognition by feature** | External classifiers (face detection, object detection, OCR, segmentation) plugged into the typed-field interface as `external_classifier(image, key, label)` operators. | **Designed (R21C `IDENTITY_LAYER_DESIGN.md`); not built.** |
| **L3 — World knowledge** | LLM substrate. Composes with L1–L2; doesn't compete. The LLM authors predicates in fiber A, evaluates fiber A's verdicts as context. | Available (LLM is me); not yet wired as a tool I can call during conversations |
| **L4 — Compositional inference** | Predicates whose arguments are predicate verdicts. Reasoning over recognized entities. e.g. `is_wedding_scene(human_subjects, formal_attire, cake_signature)`. | Architecturally trivial extension of existing runtime; not yet built |

The whole project is the layered substrate, not just L1. Treating L1 as the
whole project is drift.

## 5. Tracks (parallel workstreams)

| track | description | current state |
|---|---|---|
| **T1 — Vocabulary Health** | IR audit at scale, predicate retirement, growth | 103 predicates, IR-clean on 161-image corpus; needs scale-up to 10k+ images |
| **T2 — Phoxelis as Medium** | .phox format, encoding, capacity, filter survival | Categorical first (filter survival) verified R44–45; capacity behind QR on camera transit |
| **T3 — Multi-modal extension** | Sensor types beyond visual (accel, gyro, audio, lux) | Harness collects sensor data; vocabulary doesn't yet use it |
| **T4 — Tool Ladder** | External tools as scaffolding, replacement tracking | Ad-hoc; needs explicit ledger (this round) |
| **T5 — Hardware Substrate** | Neuromorphic deployment (Loihi, Akida) | Theoretical alignment understood; no compiler yet |
| **T6 — Phoxelis as MCP Tool** | Wrapped runtime so the LLM can call it during conversation | Not built; clear next step |

A round contributes to one or more tracks. Rounds that don't is drift.

## 6. Anti-drift contracts

**Hard contracts** — violation = the round didn't happen, not "the round was
weird."

1. **Every round produces a measurement.** A number, a comparison, an
   empirical finding, a documented retirement. Not a description of a thing
   that might exist; an empirical thing that does. "Designed but not
   measured" doesn't count.

2. **Capacity claims state transit conditions.** Always: "X bytes through
   transit Y at canvas Z." Never: "X bytes." If transit isn't named, the
   claim is malformed.

3. **Architectural firsts and capacity firsts don't blur.** If the round
   demonstrates a property no other system has, that's a categorical first.
   If the round produces a higher number on a benchmark, that's a capacity
   first. Categorical firsts don't quietly become capacity firsts in
   subsequent rounds; capacity firsts don't quietly inflate to "we beat X."

4. **Promised future rounds are tracked.** Every "Round N+1 will do Y" gets
   logged in `PHOXELIS_PROMISES.md`. Promises that age without being
   fulfilled get explicitly *abandoned* with a reason, not silently dropped.

5. **External tools used are named.** Every external tool (LLM call,
   ML model, library) used as scaffolding is logged in
   `PHOXELIS_TOOL_LADDER.md` with its replacement target. A tool that's been
   in use for 5+ rounds without a replacement plan is drift.

6. **Failed predicates are retired with documented reason.** Round 25's
   `has_local_polarization_signal` retirement is the template. Don't quietly
   stop using a predicate; retire it explicitly in vocab.aurex with a
   comment.

7. **The categorical first (R44–45) is the headline, not the capacity story.**
   When asked "what is Phoxelis," lead with the filter-survival result.
   Capacity is a secondary benchmark. Confusing this is drift.

**Soft contracts** — these are good practice; violations get noted but not
fatal.

8. Rounds that take >2 hours of conversation effort should produce something
   reusable, not just one-off scripts.
9. Code I run in the sandbox should also be packaged for the user to run on
   their own machine.
10. When the bash mount cache lies to me about file contents, I notice and
    work around it rather than rebuilding the same code six times.

## 7. The scope-drift cycle (from `aurexis_scry_field_notes.md`)

The cycle the user has documented:
1. Concrete artifact (button you can click)
2. Mid-build, frame widens
3. New frame feels like *the* answer
4. Try to articulate; description doesn't hold
5. Back to step 1, one layer deeper

This pattern is *expected*, not a failure. But I should *name* the cycle when
I'm in it, not pretend each widening is permanent. The charter is the
provisional naming. When the next widening comes, the charter gets *updated*,
not silently violated.

## 8. The user expects me to:

- Engage at the level of vision, not just implementation.
- Use external tools (web fetch, LLM subagents, Chrome MCP) more
  autonomously between rounds, less hand-holding required.
- Pull from web corpora at scale, not just synthetic + 13 phone photos.
- Not flatten the conversation back to product-manager voice.
- Branch from where they left off and land somewhere past it.
- Hold all conclusions provisionally; expect the frame to widen.

## 9. The single sentence to hang understanding on

> Phoxelis is the substrate that makes "meaning carried by composable
> measurements" empirically testable, in both directions of the calculus,
> with the vocabulary auditing itself.

If a round doesn't make that more true, it's drift.
