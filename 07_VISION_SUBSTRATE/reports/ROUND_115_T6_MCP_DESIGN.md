# Round 115 — T6 MCP wrapping arc opens: tool surface design

**Date:** 2026-05-01
**Track:** T6 (Phoxelis as MCP tool — the grounded-AI door Vincent prioritized)
**Status:** complete — design round, no implementation; identifies exact gap between what R54/R72 already built and what real MCP-protocol compliance requires; specifies the LLM-facing tool surface

---

## Why this is the door that matters

Vincent's prioritization placed the "cross-modal substrate as basis for
grounded AI" claim alongside the alternative-paradigm claim. The
mechanism: an LLM calls predicates, gets typed verdicts, reasons
symbolically over them. Every perceptual claim the LLM makes has a
fingerprint trail.

That mechanism doesn't exist yet, but it almost does. R54 (in-process
LLM-callable runtime) and R72 (stdio JSON-RPC wrapper) built the
runtime plumbing. What's missing is the **MCP-protocol shell** that
turns "JSON-RPC over pipes" into "tools an LLM can discover and call
through standard MCP clients."

R115 designs that shell. R116+ implements it.

## What R54/R72 already built

| component | location | status |
|---|---|---|
| In-process Python `Runtime` class | `aurexis_workbench/runtime.py` | mature; 151 predicates installable |
| Stdio JSON-RPC wrapper | `round72_stdio_mcp/phoxelis_stdio.py` | works; 4 methods (`list_predicates`, `install_predicate`, `eval_image`, `vocab_size`); 5/5 smoke tests pass |
| Vocab.aurex auto-load | R72 boots vocabulary on stdin entry | persists installed predicates across requests |
| Inline DSL authoring | `install_predicate` accepts source text | LLM can author at runtime |

Reusing all of this. The gap is purely the protocol shell.

## What real MCP requires that R72 doesn't yet have

| MCP requirement | R72 has? | gap |
|---|---|---|
| `initialize` handshake with capability negotiation | no | trivial to add — return `{"protocolVersion": ..., "capabilities": {"tools": {}}}` |
| `tools/list` returning JSON Schema for each tool | no | needs structured schema per tool |
| `tools/call` with name + arguments shape | no | R72's `eval_image` is close but not standard-shaped |
| Tool result envelope (`content: [{"type": "text", "text": ...}]`) | no | wrap existing returns in MCP envelope |
| Notification handling (notifications/cancelled, etc.) | no | optional for v1 |
| stderr logging that doesn't pollute stdio | partial | already separates stdout=protocol from stderr=logs |

R72 is the substrate; R116 is the wrapping. About 200-300 lines of
Python on top of the existing wrapper.

## Design — LLM-facing tool surface

The principle: each tool maps to a verb the LLM would naturally form.
"What predicates exist?" "Tell me about predicate X." "Run the substrate
on this image." "Compare these two images." "Describe this image in
prose." Authored as 5 tools, not 1 — granularity matches LLM intent.

### Tool 1 — `phoxelis_list_predicates`

Discovery. The LLM uses this to learn what perceptual capabilities
exist on this substrate.

```
input  schema: { filter?: string }   // optional substring filter
return shape:  {
  predicates: [
    {
      name: string,           // e.g. "has_gradient_energy"
      intent: string,         // e.g. "scene_contains_any_oriented_structure"
      expects: [{name, dtype}], // e.g. [{name: "scene", dtype: "image"}]
      returns: string         // e.g. "bool"
    },
    ...
  ],
  total: int                 // 151 currently
}
```

Why include `intent` here: lets the LLM scan all 151 predicates in
one call without N follow-up describe calls. ~30KB JSON for the full
list — fits in any reasonable context.

### Tool 2 — `phoxelis_describe_predicate`

For when the LLM needs the actual DSL body (e.g., to compose with it
or to understand what a predicate is doing).

```
input  schema: { name: string }
return shape:  {
  name: string,
  body_dsl: string,         // raw DSL body
  expects: [{name, dtype}],
  returns: string,
  intent: string,
  source_round?: string     // e.g. "R107" if known
}
```

### Tool 3 — `phoxelis_evaluate_image`

The core verb. Given an image (and optionally auxiliary fields), return
which predicates fire.

```
input  schema: {
  image_path: string,                    // absolute path to image file
  depth_path?: string,                   // optional depth map (.npy or grayscale png)
  spectral_path?: string,                // optional hyperspectral cube (.npy)
  predicate_filter?: string[]            // optional subset; omit = all 151
}
return shape: {
  fingerprint: { [pred_name]: bool },    // fired or not
  errors: { [pred_name]: string },       // for predicates that errored
  n_fired: int,
  n_evaluated: int,
  n_abstained: int,                      // predicates whose required field wasn't provided
  intent_summary: string                 // brief human description of the fingerprint
}
```

`intent_summary` is a small contribution the substrate makes to the LLM:
"high gradient energy + many corners + vegetation red-edge step +
dominant green hue." This is the narrator output as a single string.

### Tool 4 — `phoxelis_compare_images`

Symbolic image similarity at the substrate level — beats pHash/dHash
on geometric transforms (R98/R99) without training.

```
input  schema: {
  image_a_path: string,
  image_b_path: string,
  predicate_filter?: string[]
}
return shape: {
  jaccard: float,             // [0, 1]
  shared_fires: string[],     // predicates that fire on both
  a_only: string[],
  b_only: string[],
  near_duplicate: bool        // J >= 0.80 heuristic
}
```

### Tool 5 — `phoxelis_install_predicate`

LLM authors a new DSL predicate at runtime. Persists for the session.

```
input  schema: { source: string }
return shape: {
  name: string,
  type_check_passed: bool,
  diagnostics?: string[]
}
```

The LLM can iterate: install → eval → see if it fires sensibly →
refine. R56 demonstrated 2/5 LLM-authored L4 predicates IR-clean at
N=20; this surface lets that happen during conversation rather than
in a round.

## Design — what NOT to expose in v1

- **Bulk corpus IR audit.** The existing `cli_visual` does this; it's
  a long-running operation that doesn't fit the request-response shape.
  Could be a v2 "background tool" but not v1.
- **Backward fiber synthesis.** R86-R89's image construction from
  predicate targets is exciting but fragile (55% target hit rate).
  Premature to expose to LLMs as a callable.
- **Phoxel splatting / 3D rendering.** T7 work; will get its own
  dedicated arc when Phase 2 lands.
- **Vocabulary mutation (retire/recalibrate).** These should be
  human-driven via rounds, not LLM-driven mid-conversation. The
  charter's anti-drift contract requires documented evidence per
  vocabulary change.

## Design — the multi-modal question

The R107-promoted predicates need `depth` or `hyperspectral` fields.
LLMs typically have file paths in conversation, so:

- v1 (R116): file paths only. RGB image → all 4 RGB-modality fields
  populated. R107 multi-modal predicates correctly abstain.
- v2 (R117+): optional `depth_path` / `spectral_path` arguments. Server
  loads .npy or grayscale-png for depth, .npy for hyperspectral cubes.

This means the v1 surface can ship without solving the multi-modal
data-passing problem. R107 multi-modal predicates already handle
abstention correctly via the typed-field interface.

## Design — error handling

Every tool returns either success or a structured MCP error
(`{"isError": true, "content": [{"type": "text", "text": "..."}]}`).
Predicate-level errors (e.g. type mismatch on a malformed bundle) bubble
up in the `errors` dict of `evaluate_image`, not as protocol errors.
This lets the LLM see "predicate X errored on this input" without the
entire tool call failing.

## Design — security posture

The MCP server reads files from disk. Any LLM that connects can request
any file path. Mitigations:

- Document: server reads files passed in `image_path` etc. — caller's
  responsibility to whitelist.
- Default: server only reads from a configurable allowlist directory
  (e.g. `~/PhoxelisAllowlist/`) with absolute-path validation.
- v1 scope: no allowlist (manual user trust). v2 candidate: add it.

Note this is the standard MCP file-access posture. Not a Phoxelis-specific
concern.

## Design — performance posture

Per-image eval is ~0.4s on the sandbox CPU. For an LLM in conversation,
1-2 second tool-call latency is acceptable. For batch corpus runs,
async/streaming would be needed — out of scope for v1.

R109 evaluated N=76 in ~30s; R111 evaluated N=226 in ~80s. The MCP
surface is for single-image queries from an LLM, not batch jobs.

## What R116 (next NBR) will implement

Given this design, R116 builds:

1. **`mcp_server.py`** — async asyncio implementation reading
   line-delimited JSON-RPC from stdin
2. **MCP protocol handlers** — `initialize`, `tools/list`, `tools/call`,
   notification routing
3. **Tool implementations** — five tools above, each a thin wrapper
   over R72's existing handlers + JSON envelope construction
4. **Schema definitions** — JSON Schema for each tool's inputs and outputs
5. **Smoke tests** — at minimum, MCP handshake, list_predicates, and
   evaluate_image roundtrips through stdin/stdout

R116 is implementation-heavy. Estimate 400-600 lines of Python; doable
in 2-3 NBR rounds (R116 = handshake + list_predicates + evaluate_image;
R117 = compare + describe + install_predicate; R118 = smoke tests +
README + first end-to-end LLM-call demo).

## Honest caveats

- **MCP is a moving target.** The protocol spec is at v0.4-ish; minor
  changes between releases. The server should declare the protocol
  version it implements and reject unknown future versions.
- **Real deployment requires a manifest.** Beyond the server itself,
  Claude/other clients need a `claude_desktop_config.json` or
  equivalent telling them how to launch the server. R116 should ship
  that config alongside.
- **The substrate's most interesting predicates need fields that don't
  exist on most images.** R107 cross-modal predicates (`is_distant_vegetation`,
  etc.) need depth + hyperspectral. v1 ships with these abstaining;
  the grounded-AI win is real but bounded to RGB until v2.
- **No Vincent-side hardware loop yet.** A real grounded-AI demo would
  involve the LLM calling the substrate on a phone-camera capture,
  reasoning, recommending an action. The MCP surface ships without
  that loop — it's testable in conversation but not in deployment.

## What this round changes

- **Nothing canonical.** This is a design round.
- **Charter Section 5 T6 row** — should update from "Not built; clear
  next step" to "Designed in R115; R116+ implementation arc opened."
- **Promises ledger** — opens C-115 (design captured) + P-24
  (implementation work tracked across R116-R118).

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| T6 MCP wrapping arc — design captured | R115 | 5-tool LLM-facing surface specified; gap from R72 stdio wrapper to MCP-compliant server identified (~250 lines wrapping); 3-round implementation plan named | current — no implementation; design only |

## Promises ledger updates

- **C-115 closes:** T6 design round complete. Tool surface specified,
  gap from R54/R72 named, 3-round implementation plan opened as P-24.
- **P-24 opens:** Implement T6 MCP server per R115 design. Target
  R116-R118 (handshake/list/eval → compare/describe/install → tests/docs/demo).

## Files added this round

- this report
- `PHOXELIS_PROMISES.md` — C-115 entry, P-24 opens
- `PHOXELIS_BENCHMARKS.md` — R115 row
- `PHOXELIS_CHARTER.md` — Section 5 T6 row update

No code or canonical-file changes. R115 is design.

## Next round opens with

R116 implementation:

1. Build `t6_mcp/mcp_server.py` with `initialize` + `tools/list` +
   `tools/call` for `phoxelis_list_predicates` and
   `phoxelis_evaluate_image` only (smallest viable surface).
2. Smoke test: launch server, run MCP handshake, list 151 predicates,
   evaluate one cached image, verify fingerprint structure.
3. Ship `claude_desktop_config.json` snippet for local testing.

R117 adds `compare_images`, `describe_predicate`, `install_predicate`.
R118 ships smoke tests + README + an end-to-end LLM-call demo.
