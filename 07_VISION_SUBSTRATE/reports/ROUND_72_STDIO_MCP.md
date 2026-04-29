# Round 72 — close P-15: stdio MCP wrapper for out-of-process callers

**Date:** 2026-04-29
**Track:** T6 (Phoxelis as MCP tool)
**Status:** complete — P-15 closed (was STALE >14 rounds); second-oldest stale promise off the ledger after R57's P-02

---

## What got built

`round72_stdio_mcp/phoxelis_stdio.py` — thin JSON-RPC over stdin/stdout
wrapper around the runtime. Out-of-process LLM clients (or any other
caller) can spawn the script and pipe one JSON-RPC request per line.

**Methods:**
- `list_predicates` → array of installed predicate names
- `install_predicate {"source": "..."}` → installs a DSL predicate, returns name
- `eval_image {"path": "...", "predicates": [...], "predicate_source": "..."}` → verdicts
- `vocab_size` → predicate + operator counts

The wrapper boots once, installs the full vocabulary from `vocab.aurex`,
and serves requests on stdin. State (newly-installed predicates) persists
across requests within a session.

## Smoke test (5/5 passing)

```
id=1 vocab_size                  -> {n_predicates: 122, n_operators: 99}
id=2 list_predicates             -> array of 122 names
id=3 eval_image (5 predicates)   -> {verdicts: {pred: {value, error}, ...}}
id=4 install_predicate (new)     -> {name: "r72_smoke"}
id=5 eval_image (newly-installed)-> {verdicts: {r72_smoke: {value: true}}}
id=6 unknown_method              -> error -32601 (correct rejection)
```

## What this round changes

- **Out-of-process callers can now use Phoxelis.** P-05 (R54) closed
  the in-process Python interface; P-15 closes the stdio interface
  for any client that can read/write JSON over pipes.
- **The interface is minimal but complete enough.** Four methods cover
  the substrate's main verbs: introspect, install, evaluate, count.
  Full MCP-protocol compliance (initialize handshake, capability
  negotiation) would add ceremony without changing what's exposed.
- **The wrapper preserves the 5-field bundle convention** (scene,
  color_scene, burst, patch_size, row_y). Image is loaded by file path;
  any PNG/JPG/NPY readable by PIL or numpy works.

## Honest caveats

- **No streaming or partial results.** Each request is one round-trip.
  For large corpus sweeps, the caller batches eval_image requests.
- **No rate limiting / sandboxing.** A client could install a malformed
  predicate; the parse error is returned cleanly but the predicate
  could shadow built-in vocabulary names within the session. Not a
  trust boundary issue here (caller is the user's own LLM).
- **Bundle field types are fixed.** Predicates that need different
  fields (e.g. `cap_axis_0`/`cap_axis_90` for the retired
  polarization predicate) won't work via this wrapper. Future
  expansion: `eval_bundle` method that takes a JSON-described bundle.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| Stdio JSON-RPC wrapper available | R72 | 4 methods, smoke 5/5 | current |
| Stale promises closed in R47-R72 sweep | R72 | P-02 (R57), P-08 (R59 superseded), P-09 (R49), P-11 (R53), P-12 (R50), P-14 (R55), P-18 (R62), P-19 (R61), P-20 (R66), P-21 (R67), P-15 (R72) | current — 11 closures across 25 rounds |

## Promises ledger updates

- **C-72 closes P-15.** Long-running stale promise (>14 rounds since R54). The substrate is now reachable from any environment that can spawn a Python process and pipe JSON.

## Files added this round

- `round72_stdio_mcp/phoxelis_stdio.py` — main RPC server
- `round72_stdio_mcp/test_stdio.sh` — smoke test pipe
- `PHOXELIS_PROMISES.md` — P-15 marked completed, C-72 entry
- this report

## Sweep summary R65 → R72

| round | substrate change | preds | ops | closed |
|---|---|---|---|---|
| R65 | sensor-provenance family extended | 108→110 | 96→99 | (open P-21) |
| R66 | native-resolution corpus | — | — | P-20 |
| R67 | pixel-grid candidate falsified | — | — | P-21 |
| R68 | first batch L3 author-loop | 110→116 | — | (P-10 partial) |
| R69 | combined audit + threshold recovery | 116→117 | — | — |
| R70 | second batch L3 author-loop | 117→122 | — | (P-10 partial, base rate 61%) |
| R71 | (skipped — corpus growth network-bound) | — | — | — |
| R72 | stdio MCP wrapper | — | — | P-15 |

Net across the 8-round sweep: **+14 predicates** (122 from 108), **+3 operators** (99 from 96), **3 promises closed** (P-20, P-21, P-15), **1 candidate retired by falsification** (R67's `has_axis_aligned_pixel_grid`), **0 new pending promises opened**, **stale promise count down from 6 to 5**.

## Next round opens with

R73 candidates: corpus growth at native resolution (push N from 76 toward 200+) → would dissolve some R70 deferred candidates and provide larger base for IR audit; or another batch L3 author-loop targeting still-uncovered territory.
