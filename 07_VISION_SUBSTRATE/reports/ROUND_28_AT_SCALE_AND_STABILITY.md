# Round 28 — Audit at scale (A) + capture-stability benchmark (B)

**Date:** 2026-04-28
**Both parts requested.** Round 28 ships the plumbing; Round 29 is the
runs themselves and the headline numbers they produce.

## Why these two together

Two questions Phoxelis hasn't yet answered with real numbers:

**(A)** Does the Independence Ratio audit actually hold up when the
corpus is 10–100× larger and genuinely heterogeneous? Round 27's IR
ran over 57 inputs that were mostly the user's own phone photos plus
synthetic pumps. A clean IR over 57 items is suggestive, not load-
bearing. The same audit over 1,000+ images spanning satellite
imagery, museum art, wildlife, astronomy, and street photography
either confirms the vocabulary is empirically clean across the
visual world or surfaces structural problems hidden by the small
corpus.

**(B)** Are the predicates' verdicts stable when you photograph
the same scene many times under varied conditions? The structural
claim Phoxelis makes — that meaning rides on perceptual structure
that survives capture noise — is empirically testable: predicate
states should agree with themselves across captures of the same
scene. A predicate that flaps between True and False on captures
of the same object is reading noise, not signal. No existing CV
system routinely runs this benchmark; Phoxelis is positioned to
because its predicates are designed to ride on perceptually-stable
structure.

## Three new modules (in `aurexis_workbench/`)

`sources.py` — live image source router covering 7 stages: synthetic
calibration, easy photos (Picsum), diverse photos (Wikimedia random,
Openverse), wildlife (iNaturalist by taxon), art (Met, Art Institute
Chicago), astronomy (NASA APOD, Mars rovers), and earth-from-above
(OpenStreetMap tiles). All defaults are no-API-key sources; the
pattern was modeled after Donald Pilger's `bigbugnowadaze/scry`
source router (separate research line, descended from Aurexis), but
this is a fresh and slimmer implementation. URL-level dedup via
`_seen_urls.txt`. Query rotation across nature / art / astronomy
keyword lists so re-runs pull genuinely different content.

`eval_split.py` — the hash-deterministic train/test splitter. Five
lines that take an image alias and return `"train"` or `"test"`
based on `MD5(seed:alias) mod 1.0 < test_fraction`. Re-ingesting
the same image always lands in the same bucket. Same idea Donald
shipped in his `scry` work; clean enough that I wrote it fresh
rather than lifting it.

(`vision_ops.py` and `vocab.aurex` unchanged this round — Round 28
is plumbing, not vocabulary work.)

## Two new runners (at workspace root)

`phoxelis_corpus_audit.py` — Plan A. Walks every source in the
registry, fetches `--per-source` images per source (default 20),
runs the full vocabulary, and emits `IR_AT_SCALE_<timestamp>.md`
plus a parallel `.json` with the raw rates / EQ-classes / always-
False / always-True / source-distribution / split-distribution.
Designed to run on a Windows host where the file system is intact;
checkpoints the URL-dedup file every 25 images so a long batch is
resumable.

`phoxelis_capture_stability.py` — Plan B. Takes a folder of
`>= 5` captures of the same scene, runs the full vocabulary on each
capture, and reports per-predicate stability — defined as the
fraction of captures where the verdict matches the modal verdict.
Emits `CAPTURE_STABILITY_<label>_<timestamp>.md` plus parallel
`.json`. Predicates are bucketed:

  * **rock-solid** — stability = 1.000 (always agrees with itself)
  * **high** — 0.85 ≤ stability < 1.000
  * **medium** — 0.65 ≤ stability < 0.85
  * **fragile** — < 0.65 (flapping; reading noise)

A vocabulary's mean stability across the buckets is the headline
number. The expected good result: rock-solid + high covers the
majority of the vocabulary, fragile is a small minority that
identifies predicates whose thresholds need widening or whose
operators are too pixel-fragile.

## How to run them

**Plan A — IR at scale.** From the workspace root:

```
python phoxelis_corpus_audit.py
```

Defaults: 20 images per source × 13 sources × 7 stages = ~260 images
per run, ~6–10 minutes depending on bandwidth. To go bigger:

```
python phoxelis_corpus_audit.py --per-source 50 --resize 320
```

That's ~650 images per run. The dedup file means a second run with
the same args adds new fetches without re-fetching old ones, so
you can stack runs to grow the corpus over time.

**Plan B — capture stability.** Take 10–30 photos of the *same
scene* — same object or location — under varied conditions: shift
your angle, change distance, alter exposure if the camera lets you,
photograph at different times of day, with and without flash, hold
steady or hand-shake intentionally. Drop them all in one folder.
Then:

```
python phoxelis_capture_stability.py /path/to/folder --label "kitchen-table"
```

Best practice: run this benchmark on three different scenes (an
indoor scene, an outdoor scene, a phone-screen photograph) so the
stability matrix has cross-scene comparison. A predicate that's
rock-solid on every scene is genuinely robust; one that's rock-solid
on indoor but fragile on outdoor is reading something scene-specific.

## What the runs will produce (Round 29)

`IR_AT_SCALE_<timestamp>.md` should report something like:

```
PHOXELIS CORPUS AUDIT AT SCALE — <date>
corpus: 260 images from 13 live sources
vocabulary: 103 predicates, 380.2s total (1.46s/image)
...
ALWAYS-FALSE PREDICATES: <N>
EQUIVALENCE CLASSES: <N>
INDEPENDENCE RATIO HEADLINE
  predicates fully blocked: 2
  predicates that did real work: 101
  always-False rate: 0.029
  EQ-class rate:    0.038
```

The headline numbers are what matters. We compare them to the
Round 27 small-corpus baseline (1 always-False, 0 always-True,
3 EQ classes on 57 inputs) and learn whether the picture stays
clean at scale.

`CAPTURE_STABILITY_<label>_<timestamp>.md` should report:

```
mean stability across vocabulary: 0.8XX
ROCK-SOLID (stability == 1.0): <N>  predicates
HIGH (0.85-1.0): <N>
MEDIUM (0.65-0.85): <N>
FRAGILE (< 0.65): <N>
```

The fragile list is the actionable output. Predicates that flap
on the same scene are either over-tight thresholds or operators
reading pixel noise. Each one is a Round-29-or-later cleanup target.

## Why neither runner runs in the analysis sandbox

The Linux FUSE mount under the analysis sandbox returns stale views
of recently-edited Python sources, and the existing `__pycache__`
.pyc files are locked from deletion. Round 27 hit this and shipped
the IR runner as a Windows-side script for the same reason. Both
of these new runners are designed to run on the Windows host where
the source files are intact and Python's module cache works
correctly. That's how `push_round28_at_scale_and_stability.bat`
exercises them.

## Output file conventions

* `IR_AT_SCALE_<YYYY-MM-DD_HHMMSS>.md` and `.json` — Plan A output
* `CAPTURE_STABILITY_<label>_<YYYY-MM-DD_HHMMSS>.md` and `.json`
* All land in `Aurexis_Core_WORKING_20260414-1339/07_VISION_SUBSTRATE/reports/`
* The push.bat does NOT auto-run a Plan B stability benchmark
  because it requires user-staged capture data; it runs Plan A only.

## Vocabulary state after Round 28

Unchanged. **103 predicates, 95 operators, 38 synthetic scenes.**
Round 28 adds 2 utility modules (`sources.py`, `eval_split.py`) and
2 runners. No predicate or operator changes.

## What this round does NOT do

* It does not run a 10,000-image audit. The runner is shipped;
  the long batch executes in Round 29.
* It does not stage any capture-stability scenes. That's user work
  between Round 28 and Round 29.
* It does not change the vocabulary. The next vocabulary changes
  are the cleanup driven by what the Round 29 runs surface.
