# Round 55 — checkpointed corpus harness (P-14 closure)

**Date:** 2026-04-29
**Track:** T1 (Vocabulary Health)
**Status:** complete — P-14 closed; convergence trajectory visible across 3 sessions

---

## What this round opened on

R53 finding: a single sandbox bash call (45s budget) can pull at most ~10 web images from the source router because most sources have multi-second response times. R54 confirmed the consequence from the predicate-author side: at N=8, even a brand-new orthogonal predicate IR-collides with an arbitrary existing one.

P-14 (opened R53) proposes the structural fix: **persistent state on disk that grows N across many sessions**. Each call reads the state, pulls a wall-time-budgeted batch, evaluates the vocabulary, and writes the state back. Across N sessions the corpus grows monotonically and the equivalence-class structure converges toward the true vocabulary.

This round implements that harness and demonstrates accumulation.

## Architecture

`round55_corpus_harness/corpus_harness.py` ↔ `corpus_state.json`.

State schema:
```
{
  "n_images": int,
  "vocab_hash": str,                          # invalidates state on vocab change
  "predicate_names": [...],                   # for index alignment
  "image_aliases": [...],
  "image_sources": [...],
  "verdicts": {pred_name: "TFFTF...?TT" (one char per image)},
  "seen_urls": [...],                         # dedup
  "source_rotation_offset": int,              # round-robin pointer
  "session_log": [
    {timestamp, n_added, elapsed_pull, elapsed_eval, n_total_after}, ...
  ]
}
```

Per call:

1. Install vocabulary, hash it, load matching state (or fresh if vocab changed).
2. Pull a wall-time-budgeted batch from the source router, dedup'd against `seen_urls`. Source rotation pointer moves forward each session so successive calls hit different stages first.
3. Evaluate every predicate on each new image; append a single character (`T`/`F`/`?`) to that predicate's verdict string.
4. Write state.

The state file is portable: same layout works on Vincent's machine and across sandbox sessions. Carrying it forward unbounded eventually closes P-01.

## Convergence trajectory across this round's three sessions

```
session  N    always_F  always_T  EQ_classes  largest_EQ
   1      4      52         6         12          52
   2     12      27         1         11          27
   3     20      23         1          6          23
R28     161      12         0          2         ~12   (reference baseline)
```

Every metric monotonically converging toward R28. The largest equivalence class shrank from 52 (at N=4) → 27 (N=12) → 23 (N=20). With another ~5 sessions (~50 more images), N would reach ~70 and the structure should be substantially closer to R28's 2-class final form. With ~30 sessions it should match.

## Headline benchmark row

| metric | round | value | corpus | status |
|---|---|---|---|---|
| Checkpointed corpus growth across sessions | R55 | 3 sessions accumulate N=4→12→20; always-False 52→27→23, largest EQ class 52→27→23, monotonic convergence toward R28 | live web pull, persisted in `corpus_state.json` | current — first multi-session accumulation; harness ready to grow corpus indefinitely |

## What this changes about how P-01 works

Before R55: P-01 ("IR audit at 10,000+ images") was a Vincent-machine task because no sandbox bash call could fit the runtime.

After R55: P-01 is a **multi-call task with explicit checkpointing**. Each sandbox round contributes ~10–20 images. Across rounds, N grows. Vincent's machine can also drive the harness without changing the protocol — same state file, same script. The 10k threshold remains far (would need ~500 sandbox rounds, or one Vincent-machine batch run), but the path is unambiguous.

## Promises ledger updates

- **P-14** (checkpointed corpus harness): closes with C-55 evidence.
- **P-01** (IR audit at 10,000+ images): stays pending but is no longer structurally blocked. It's now bounded by N sandbox sessions accumulating, which is a non-blocking timeline.

## Files added this round

- `round55_corpus_harness/corpus_harness.py` — the harness
- `round55_corpus_harness/corpus_state.json` — current state, N=20 after 3 sessions
- this report

## What this round changes about future rounds

The harness can be invoked at the start of any future round to add images to the corpus before doing other work. The marginal cost is ~25–30 seconds per call. After many rounds the corpus is large enough that:
- IR audits become reliable (small-N collapse goes away)
- LLM-authored predicates can be IR-checked properly (R54's blocked promotion would resolve)
- Always-False predicate retirement decisions become defensible

## Next round opens with

`python phoxelis_audit.py`. STALE count after R55 should be 8 (P-14 wasn't STALE since just opened). The audit's velocity gate prefers older STALEs. Strongest candidates for R56:

- **R56 — close P-06 (L4 compositional inference predicates)**: predicates whose arguments are other predicates' verdicts. Trivial extension of the existing runtime — just need a way to thread predicate-verdicts back into the type system. Sandbox-doable single-round.
- **R56 — call the harness mid-round + close P-08 attempt**: drive Chrome MCP to anonymous-upload-friendly social platforms (Reddit, Mastodon) for true platform-class round-trip. Extends R51 autonomy.
- **R56 — corpus-pull session 4-7 inline + P-10 retry on bigger N**: every session adds ~5-10 images; once N>=50, retry the R54 LLM-authored predicate and check if the IR-collision still holds. If it doesn't, promote the predicate to vocab.aurex (vocabulary growth, the actual P-10 close).
