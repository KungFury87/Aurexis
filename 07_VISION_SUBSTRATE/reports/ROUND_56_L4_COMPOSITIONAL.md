# Round 56 — L4 compositional inference predicates (P-06 closure)

**Date:** 2026-04-29
**Track:** L4 (compositional inference)
**Status:** complete — architecture proven; 2/5 LLM-authored L4 predicates IR-clean at N=20

---

## What this round opened on

P-06 stale since R47. Charter description of L4: *predicates whose arguments are predicate verdicts*. The architectural claim has been there for 9 rounds. Time to stop carrying it as theoretical.

This round implements L4 as the smallest correct thing: a Python function over a verdict dict. No DSL changes; no new operators in the registry; just thread-through composition over what L1 already produces.

## Architecture

`L4Layer` is implicit in the runtime structure. Each L4 predicate is `(name, intent, dependencies, fn(verdict_dict)->bool)`. When evaluating L4 predicates on a bundle, the runtime first evaluates all dependencies (L1 predicates, cached or fresh), then applies the L4 lambda. If any dependency is `?` (operator error / blocked field), the L4 predicate is `?`.

Crucial efficiency point: L4 evaluation costs **zero new L1 evaluations** when verdicts are already cached. R55's `corpus_state.json` has N=20 × 103 verdicts cached. R56's L4 layer reads that cache and produces L4 verdicts in under a second, no network, no recomputation.

## L4 predicates authored this round

```
is_indoor_warm_scene       = has_indoor_scene_signature AND has_warm_palette
is_text_dominant_subject   = has_text_like_signature AND has_genuine_text_not_screen
is_outdoor_landscape       = has_horizon_line_signature AND has_low_edge_density
                             AND NOT has_indoor_scene_signature
is_busy_warm_scene         = has_many_corners AND has_warm_palette
is_high_concept_diversity  = has_polychromatic_palette AND has_many_small_blobs
```

Each is a 2-3 term composition of existing L1 predicates. None had been expressible at L1 directly.

## Results on R55 corpus (N=20)

```
       L4 predicate                rate    fired   IR-clean?
  is_indoor_warm_scene             0.100   2/20    OK
  is_text_dominant_subject         0.300   6/20    OK
  is_outdoor_landscape             0.000   0/20    twin=has_subframe_motion
  is_busy_warm_scene               0.250   5/20    twin=has_warm_palette
  is_high_concept_diversity        0.000   0/20    twin=has_subframe_motion
```

**2/5 IR-clean**: `is_indoor_warm_scene` and `is_text_dominant_subject` produce verdict patterns that don't match any of the 103 L1 predicates. They carry new information.

**3/5 collide** for honest, diagnostic reasons:
- `is_outdoor_landscape` and `is_high_concept_diversity` never fire because their dependencies don't co-occur in this 20-image corpus. They collapse into the always-False bucket alongside motion predicates.
- `is_busy_warm_scene` has a verdict pattern identical to `has_warm_palette` — the `has_many_corners` dependency fires on almost everything (R28 firing rate 91%), so the composite is dominated by warm-palette.

These are not bugs in the L4 layer; they're the small-N collapse R53 measured, applied to compositional predicates instead of vocabulary predicates. The architecture is proven; the discrimination needs N >> 20.

## Headline benchmark row

| metric | round | value | corpus | status |
|---|---|---|---|---|
| L4 compositional predicate layer | R56 | 2/5 LLM-authored L4 predicates IR-clean (`is_indoor_warm_scene`, `is_text_dominant_subject`); architecture takes zero new L1 evaluations when verdicts are cached | R55 corpus_state, N=20 | current — first L4 layer measurement; same small-N caveat as R53/R54/L1 |

## Promises ledger updates

- **P-06** (L4 compositional inference predicates): closes with C-56 evidence.

## Files added this round

- `round56_l4_compositional/round56_l4_compositional.py` — L4 implementation + 5 example predicates
- `round56_l4_compositional/round56_l4_results.json` — full data + verdict patterns
- this report

## What this changes about future rounds

L4 is now a working layer. Authoring a new L4 predicate is one Python lambda + a dependency list. The same audit discipline (IR-cleanness check via verdict-pattern equivalence) applies to L4 just as it does to L1. R58 (grow corpus + retry P-10) will benefit L4 too — at N >> 20, the 3 currently-colliding L4 predicates will likely separate from their twins.

The bigger architectural unlock: **any future round that needs to ask "is this a wedding photo?" or "is this a dashboard screenshot?" or "is this a chart?" no longer needs new L1 predicates** — those questions are L4 compositions over the existing 103-predicate vocabulary. The vocabulary is broader than its pred-name list suggests.

## Next round opens with

`python phoxelis_audit.py`. STALE count after R56 should be 7 (P-06 closed). NBR candidates:

- **R57 — P-08 (real social platform via Chrome MCP)**: extend R51's autonomy pattern from a generic CDN to specific social platforms. Reddit allows anonymous reads; Mastodon allows anonymous tooting on some instances; Imgur API needs a Client-ID. Requires Chrome MCP for anything past pure GET/POST.
- **R57 — P-07 (multi-modal sensor types)**: extend the typed-field model to accel/gyro/audio/lux. Vincent's harness already collects this data; the vocab doesn't yet use it. Sandbox-doable single-round if I author a few accel-based predicates.
- **R57 — Run R55 harness 5 more sessions inline**: grow N from 20 to ~70, then retry R54's blocked predicate AND R56's 3 colliding L4 predicates. The actual P-10 close at scale.
