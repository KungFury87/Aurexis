# Round 27 — Full IR re-run with Round 26 vocabulary

**Date:** 2026-04-28
**Vocabulary state going in:** 103 predicates, 95 operators (after
Round 26 added 4 narrow-band-hue-ratio predicates and Round 25 retired
`has_local_polarization_signal`).

## What this round does

Re-runs the Independence Ratio analysis across the full corpus —
synthetic scenes from `data/vision/synthetic/`, synthetic bursts from
`data/vision/synthetic_bursts/`, the 13 phone photos in
`~/Desktop/Aurexis evolved/Phone photos/`, and any `.aurex-session.zip`
present at the workspace root (currently the polarization-pair
session from Round 24 + the matte-control session from Round 25).

The four Round-26 predicates are folded in:

* `has_vegetation_signature`
* `has_skin_tone_signature`
* `has_warm_color_temperature`
* `has_cool_color_temperature`

## Why this lands as a Windows-side runner

The analysis sandbox in this session has been hitting two related
issues that make in-sandbox IR runs unreliable for this round:

1. **Mount-cache staleness.** The Linux FUSE mount of the Windows
   workspace returns a stale snapshot of `vision_ops.py` to the
   bash sandbox. The Read tool sees the actual file (1450+ lines);
   `wc -l` from bash sees a truncated 1418-line view that ends mid-
   string at `_hue_diversity_score`'s docstring.
2. **Locked `__pycache__`.** Even after the mount eventually shows
   the right bytes, the existing `.pyc` files cannot be deleted
   from the sandbox (`Operation not permitted`), so Python keeps
   loading the cached compiled module — which lacks the Round 26
   operators.

Net effect: from the analysis sandbox, `register_all()` returns 91
operators when the actual file defines 95, and any predicate that
references a Round 26 operator gets type-rejected.

The fix is operationally cheap. The IR runner script
`ir_run_round27.py` ships at the workspace root. `push.bat` invokes
it before staging files. On Vincent's Windows machine the source
files are intact and Python's module cache works correctly, so
the runner sees all 95 operators and 103 predicates and produces
`IR_RUN_2026-04-28_round27.md` directly into
`07_VISION_SUBSTRATE/reports/`. The numbers below are filled in
by that runner — this document is the *frame*, the IR_RUN file is
the *content*.

## What the IR run will check (and what to look for)

### Always-False predicates

Going into Round 27 there are zero (Round 21 retired the last one
when `vignette_scene` was added). The four Round 26 additions could
push that back up:

* `has_warm_color_temperature` — fired 0/13 on the phone-photo
  corpus alone, but the synthetic corpus may include warm-toned
  scenes. If still 0% across the full corpus, it lands as the
  first new always-False since Round 21.
* `has_cool_color_temperature` — fired 4/13 on phone photos.
  Should remain non-zero across the full corpus.
* `has_vegetation_signature`, `has_skin_tone_signature` — both
  fired on phone photos and should fire on at least one synthetic
  color scene; expected non-zero.

### Equivalence classes

Going in: 2 EQ classes (1 tautological, 1 corpus-size artifact).
The Round 26 additions could create new EQ classes if any of them
turn out to be empirically identical to an existing predicate:

* `has_warm_color_temperature` vs `has_warm_palette` — different
  operators (R/B ratio vs. weighted-sum warmth), but they could
  fire on identical scene sets if the corpus is small.
* `has_cool_color_temperature` vs `has_cool_palette` — same risk.
* `has_skin_tone_signature` vs `has_red_dominant` /
  `has_significant_orange_hue` — skin chromaticity overlaps with
  warm hues; on a corpus dominated by indoor portraits these may
  fire on the same shots.

If any of these collapse, that's vocabulary cleanup work for
Round 28 — either retire the redundant one or add a corpus pump
that breaks the tie.

### Vegetation/Cool correlation

Round 26 noted these co-fired on the phone-photo corpus (4/4
overlap on morning outdoor shots). The full corpus should
separate them:

* `synthetic/green_dominant_scene` should fire VEG without firing
  COOL (it's pure green, not blue-tinted).
* `synthetic/blue_dominant_scene` should fire COOL without firing
  VEG (blue without green).

If they still co-fire across all corpora, they're empirically the
same and one should retire.

## How to read the IR_RUN file

The runner emits, in order:

1. **FIRING RATES** — every predicate, fraction-of-corpus that
   evaluated to True, plus n=fired/total.
2. **ALWAYS-FALSE PREDICATES** — rate = 0 and not blocked.
3. **ALWAYS-TRUE PREDICATES (saturated)** — rate = 1.
4. **FULLY-BLOCKED PREDICATES** — no scene in the corpus supplied
   the required fields (e.g. `raw_bayer` predicates have no v3.0
   capture path so they're permanently blocked).
5. **EQUIVALENCE CLASSES** — predicates with identical truth-row
   signatures across all scenes.
6. **REJECTED PREDICATES** — type-checker errors at vocab load.
7. **ROUND 26 VERIFICATION** — the four new predicates explicitly,
   with their corpus-wide firing rates.

## Output locations

* `Aurexis evolved/ir_run_round27.py` — the runner.
* `07_VISION_SUBSTRATE/reports/IR_RUN_2026-04-28_round27.md` — the
  generated report (filled in when push.bat runs).
* `07_VISION_SUBSTRATE/reports/ROUND_27_IR_RERUN.md` — this file,
  the human-readable framing.
