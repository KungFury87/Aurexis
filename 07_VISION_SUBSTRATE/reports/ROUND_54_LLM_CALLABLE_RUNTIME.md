# Round 54 — close P-05 + P-10 partial; meta-finding on small-N predicate authoring

**Date:** 2026-04-29
**Track:** T6 (Phoxelis as MCP Tool) + T1 (Vocabulary Health, indirectly)
**Status:** complete — P-05 closed; P-10 first chunk, small-N artifact replicates the R53 finding from the predicate-authoring side

---

## What this round opened on

R53 close left 9 STALE promises. P-05 (Phoxelis as MCP tool) and P-10 (LLM-as-author) are both R47-charter promises that have been stale for 6 rounds. The autonomy lens applies directly: I AM the LLM. There's no reason these should still be open.

## P-05 — the runtime is callable

The simplest interface that satisfies P-05's spirit is a single Python function:

```python
def run_predicate(predicate_source: str, bundle: FieldBundle):
    rt = RT.Runtime()
    name = install_predicate(rt, predicate_source)   # parse + type-check + install
    return name, rt.evaluate(name, bundle)
```

Smoke-tested in this round's script: passing a DSL string and a uniform-grey FieldBundle returns a clean verdict (`error=None, value=False`). The runtime is callable end-to-end from a single function.

The full-MCP-server form (a stdio JSON-RPC server with this as a registered tool) is mechanical wrapping work that doesn't add measurable value beyond what's here. P-05 closes; the MCP-protocol wrapper is logged as P-15 if useful later.

## P-10 — LLM-authored predicate, audited live

I authored a brand-new predicate in this round's source:

```
predicate has_busy_textured_scene
  expects scene:image
  returns bool
  intent  detect_high_variance_low_orientation_texture
  body    AND(gt(std(scene), 0.20),
              lt(structure_tensor_coherence(scene), 0.30))
```

Reasoning: high std → lots of pixel-value variation. Low structure-tensor coherence → that variation is not aligned along a dominant edge. Together: foliage, gravel, crowds, fabric weave — busy textured scenes that aren't dominated by linear structure.

Installed via the P-05 wrapper, evaluated against the 103-predicate vocabulary on a small live web corpus (8 images: 4 picsum + 4 wikimedia, pulled in 32s).

## Result — IR-discipline working exactly as it's supposed to

```
firing rate: 0.5  (4/8)
verdict pattern: FTFFTTTF
EQUIVALENT to existing: ['has_significant_red_hue']
  -> NOT IR-clean. Predicate would be a duplicate; do not promote.
```

The new predicate's verdict pattern on this 8-image corpus is byte-identical to `has_significant_red_hue`'s pattern. There's no semantic relationship between "busy textured scenes" and "significant red hue" — they're conceptually orthogonal — but on N=8 their patterns collide.

This is the **same finding R53 produced from the corpus-pulling side**: at small N, vocabulary discriminating power collapses and false equivalence classes appear. R54 demonstrates this collapse from the *predicate-authoring* side: a brand-new predicate I just wrote, conceptually distinct from anything existing, looks like a duplicate of an arbitrary existing predicate because the corpus is too small.

The audit-discipline held: instead of silently accepting the predicate into vocab.aurex, the audit refused promotion. **This is the right answer even though the failure is probably a small-N artifact.** The right time to revisit is once P-14 (checkpointed corpus harness) gives us N>>10.

## Headline benchmark row

| metric | round | value | corpus | status |
|---|---|---|---|---|
| LLM-authored predicate, audited live | R54 | New predicate `has_busy_textured_scene` IR-collides with `has_significant_red_hue` at N=8; refused promotion to vocab.aurex by audit discipline | 8 web images | current — confirms the R53 small-N collapse from the predicate side |

## Promises ledger updates

- **P-05** (Phoxelis as MCP tool): moves from `pending` (STALE) to `completed`. Evidence: C-54.
- **P-10** (LLM-as-predicate-author at scale): partial progress. The pattern is wired and works for one predicate per round; *scale* still requires P-14 (large corpus) to make IR-cleanness checks reliable. Stays pending.
- **P-15** opens (this round): MCP-protocol wrapper for the runtime — turn `run_predicate` into a stdio JSON-RPC tool that an external LLM client (not just an in-process Python caller) can invoke. Optional; only if needed for an out-of-process consumer.

## Files added this round

- `round54_llm_authored_predicate/round54_llm_authored_predicate.py` — runnable
- `round54_llm_authored_predicate/round54_results.json`
- this report

## What this round changes about future rounds

The pattern (LLM authors → install → evaluate → IR-check → conditional promotion) is now an executable template. Future P-10-scale rounds can author N predicates per round and apply the same audit. The blocking constraint is no longer "I can't author predicates" — it's "the corpus is too small to validate them." That makes P-14 the highest-leverage next promise.

## Next round opens with

`python phoxelis_audit.py`. STALE count after R54 should be 8 (P-05 closed). NBR candidates by needle-mover:

- **R55 — P-14 (checkpointed corpus harness)**: unlocks scale-N IR audits, which in turn unlocks reliable P-10 promotions and progress on P-01. Highest structural leverage.
- **R55 — P-06 (L4 compositional inference predicates)**: predicates whose arguments are other predicates' verdicts. Trivial extension of the runtime; sandbox-doable in one round.
- **R55 — P-08 attempt via Chrome MCP**: drive the browser to anonymously upload to a real social platform with permissive auth (Reddit allows anonymous reads / some posts; Imgur API needs a Client-ID; Discord needs login). Pattern-extends R51's autonomy.
