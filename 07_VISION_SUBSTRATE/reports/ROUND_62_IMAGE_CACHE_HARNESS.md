# Round 62 — image-cache harness (P-18 closure)

**Date:** 2026-04-29
**Track:** T1 (Vocabulary Health) + harness infrastructure
**Status:** complete — P-18 closed; retroactive predicate evaluation works; R54 retry-at-full-N pending R63 growth

---

## What this round opened on

R60's blocked retry of R54's `has_busy_textured_scene`: the R55 corpus harness cached predicate verdicts but not images, so newly-authored predicates couldn't be evaluated against the historical corpus. P-18 opened R60 with the fix.

## What was built

`corpus_harness_v2.py`: drop-in extension of R55's harness that

1. **Caches a downsampled (160×160) uint8 RGB ndarray per image** to `corpus_images/<safe_alias>.npy`. Per-image footprint ~76 KB; 1000 images ≈ 76 MB on disk.
2. **Adds `--retry-predicate-file <file.aurex>` mode** that loads a DSL predicate source, installs it into a fresh runtime alongside the existing 106-predicate vocabulary, evaluates it against every cached image, and reports IR-cleanness vs the L1 verdict patterns.
3. **Tracks vocab_hash drift** — if `vocab.aurex` changes since the cache was built, the harness notes that cached verdicts may be partial (the new predicates didn't exist when verdicts were written).

## Results

After one fresh session via `corpus_harness_v2.py`, state grew N=36 → 42, image cache reached 18 `.npy` files (6 aligned with current state aliases; 12 orphans from a prior timed-out run that pulled images but didn't finish committing state).

**R54 retry on the cached 6-image sub-corpus:**

```
predicate:       has_busy_textured_scene
cached images:   6 / 42
fired:           1 / 6      (rate 0.167)
pattern:         ????????????????????????????????????FFFFTF
IR-clean:        YES
```

At R54 (N=8) this predicate IR-collided with `has_significant_red_hue`. On the 6 newly-cached images, it doesn't match any L1 predicate's verdict pattern — IR-clean.

**Caveat:** the IR-cleanness check is against L1 predicates' full N=42 verdict strings, so a "?" prefix on the new predicate biases toward IR-clean (no L1 predicate has 36 "?"s). The 6-image evidence is weak. The right test is the same predicate against *all* images cached — which requires R63 to grow the cache by re-pulling the older 36 images (or accepting R63's larger N as the real test set going forward).

## Headline benchmark row

| metric | round | value | corpus | status |
|---|---|---|---|---|
| Image-cache harness + retroactive predicate evaluation | R62 | Mechanism works: cache 6 images, evaluate `has_busy_textured_scene` retroactively, report IR-cleanness; orphan-handling and vocab-hash drift tracked | 6 cached images aligned with state of N=42 | current — first time the harness can validate new predicates against historical images |

## Promises ledger updates

- **P-18** closes with C-62 evidence.

## Files added this round

- `round55_corpus_harness/corpus_harness_v2.py` — image-cache + retroactive eval
- `round55_corpus_harness/corpus_images/` — 18 cached `.npy` files (~76 KB each)
- `round55_corpus_harness/corpus_state.json` — updated to N=42 with vocab_hash refresh
- `round55_corpus_harness/round62_retry_result.json` — R54 retry result
- this report

## What this round changes about the harness

R55 was sufficient for vocabulary-health audits over a fixed predicate set. R62 makes the harness **author-cycle-friendly**: once an image is in the cache, *any* future predicate can be checked against it without re-pulling. The marginal cost of growing the substrate's vocabulary drops to "write a predicate and run one retroactive eval call." This is the architectural unlock that R56 / R60 had been waiting on.

Combined with R61 (DSL promotion of IR-clean predicates), the substrate now has the full author-then-validate-then-promote cycle in working form:

```
1. LLM authors predicate  (R54 P-05)
2. Evaluate against cached corpus  (R62 P-18)
3. Audit IR-cleanness  (R56 / R60 / R62)
4. Promote to vocab.aurex if clean  (R61 P-19)
5. Audit confirms vocab.aurex parses  (R48 integrity check)
```

That's the L3-layer-as-author flow the charter described, in working form.

## Next round opens with

R63: push corpus to N=70+ via the new image-cache harness. Each session adds ~5-15 images with both verdicts and cached arrays. After ~3-5 sessions the corpus has enough cached images to do a full R54 retry, and the small-N caveats on every prior round dissolve in earnest.
