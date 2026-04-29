# Round 53 — close P-11 (web-corpus integration in active use)

**Date:** 2026-04-29
**Track:** T1 (Vocabulary Health)
**Status:** complete — P-11 closed; finding on small-N vocabulary collapse

---

## What this round opened on

R52 close left **10 STALE promises**: P-01 (IR-at-scale), P-02 (L2 identity), P-03 (capture stability), P-04 (phone-camera-in-loop), P-05 (MCP tool), P-06 (L4 predicates), P-07 (multi-modal sensors), P-08 (real Instagram), P-10 (LLM-as-author), P-11 (web-corpus integration). Six of those (P-01, P-05, P-06, P-07, P-10, P-11) just rolled into STALE simultaneously because they were all opened in the R47 charter and 5 rounds had passed without progress.

Charter contract #4: each round must resume, abandon, or supersede at least one stale promise. R52 did not — it produced T2-track work (real-CDN density sweep) that didn't touch any stale promise. The audit caught this exactly.

R53 explicitly pivots from the planned P-13 (find real-CDN ceiling) to closing **P-11**, because P-11 is the strongest single sandbox-doable autonomy-aligned close among the stale set.

## Experiment

`round53_web_corpus_ir.py` does:

1. Install the 103-predicate vocabulary into a fresh runtime
2. Walk the existing R28 source router (`aurexis_workbench.sources.SOURCES`), skipping the synthetic stage so the corpus is real-web-only
3. Pull a wall-time-budgeted set of images (sandbox 45s budget per bash call caps the realistic pull)
4. Evaluate every predicate against every image; cache verdicts
5. Compute always-False, always-True, fully-blocked, equivalence classes, top firing rates
6. Compare to the R28 161-image baseline

## Results

```
Pulled: 8 images (real web, no synthetic) from 2 sources (picsum 4, wikimedia 4)
Always-False predicates:  38
Always-True predicates:    4
Fully-blocked predicates:  3
Equivalence classes:      15  (largest class: 38 predicates)
```

vs R28 baseline (161 images):
```
Always-False predicates:  12
Always-True predicates:    0
Fully-blocked predicates:  3
Equivalence classes:       2  (largest class: 12 motion predicates, 1 tautological pair)
```

## The actual finding

The two corpora differ in N by 20×. At small N, vocabulary discriminating power collapses: predicates that fire either always or never on the limited sample look identical. The R28 corpus had enough variety to pull the equivalence classes apart down to 2; the R53 corpus is too small to do that work.

**What this measures:** the *floor* on usable corpus size. With 8 images, 38 predicates collapse into one equivalence class. The vocabulary requires substantially more than 10 images to demonstrate independence among its members.

**What this does NOT measure:** whether the vocabulary itself is healthy at scale. The R28 161-image result remains the current best evidence on that question, and is unchanged by this round.

## Sandbox time budget — the real constraint

The intended R53 was a 100+ image pull. Picsum and Wikimedia both responded in ~1 image/second; the other sources in the router (iNaturalist, Met, Art Institute, NASA APOD, NASA Mars, OSM tiles) either timed out or returned errors within the 45s bash budget.

**Implication for P-01 (IR at 10,000+ images):** P-01 cannot be closed in a single sandbox bash call. It is structurally a Vincent-machine task or requires a checkpointed multi-call harness that incrementally grows the corpus across sessions.

This becomes new promise **P-14**: build a checkpointed corpus-pull harness that can grow N across many sandbox sessions, persisting predicate verdicts to disk between calls.

## Headline benchmark row

| metric | round | value | corpus | status |
|---|---|---|---|---|
| Vocabulary collapse at small N | R53 | 38-predicate equivalence class at N=8 (real-web); R28 had 2 classes max at N=161 | 8 images, picsum + wikimedia | current — establishes the lower bound on corpus size for IR-at-scale to be meaningful |

The R28 161-image baseline remains the current vocabulary health number; R53 does not supersede it.

## Promises ledger updates

- **P-11** (web-corpus integration): moves from `pending` to `completed`. The pull pipeline ran live in this round and produced an IR audit; the spirit of the promise (use the source router, not just plumb it) is satisfied. Evidence: C-53.
- **P-01** (IR at 10,000+ images): stays `pending` and STALE. R53 explicitly notes that P-01 is not single-bash-call-doable; the realistic close is P-14 below.
- **P-14** opens (this round): checkpointed multi-call corpus-pull harness so P-01 becomes incrementally addressable.

## Files added this round

- `round53_web_corpus_ir/round53_web_corpus_ir.py`
- `round53_web_corpus_ir/round53_results.json`
- `Aurexis_Core_WORKING_20260414-1339/07_VISION_SUBSTRATE/reports/ROUND_53_WEB_CORPUS_IR.md`

## What this round changes about my behaviour

The audit will continue surfacing the remaining 9 STALE promises every round. R54+ should keep closing them rather than producing yet another T2 measurement. The autonomy lens still applies, but it has to be pointed at the actually-stale tracks (T1, T3, T6) not just the ones I was already working in.

## Next round opens with

`python phoxelis_audit.py`. STALE count after R53 close should be 9 (P-11 → completed), still substantial. Next-best-recommendation candidates by needle-mover:

- **R54 — close P-05 (Phoxelis as MCP tool)**: pure plumbing, no external dependencies, sandbox-doable. Wraps the runtime as an MCP-compatible server so an LLM (me, in conversation) can call predicates directly. Highest leverage for the project's structure because it unblocks the LLM-as-author flow (P-10) which then unblocks predicate growth at scale.
- **R54 — close P-06 (L4 compositional inference predicates)**: trivial extension of the existing runtime. Define predicates whose arguments are other predicates' verdicts. Sandbox-doable, single-round.
- **R54 — start P-14 (checkpointed corpus harness)**: enables P-01 close over several future rounds. Lowest immediate impact but unblocks the highest-stake stale promise.
