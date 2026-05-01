# T6 — Phoxelis as MCP Tool (v0.1.0)

The Phoxelis substrate wrapped as an MCP-protocol-compliant stdio
JSON-RPC server. An LLM (Claude Desktop, Claude Code, or any
MCP-aware client) can call Phoxelis predicates and reason
symbolically over the verdicts.

This is the charter T6 track — the door named in R115 design, opened
in R116-R118 implementation, validated in R118 smoke tests.

## What it exposes

5 tools:

- **`phoxelis_list_predicates`** — discovery; returns the 151
  installed predicates with their intent, expected fields, return
  type. Optional `filter` substring narrows the list.
- **`phoxelis_describe_predicate`** — full info for one predicate
  including its DSL body.
- **`phoxelis_evaluate_image`** — the core verb. Run the substrate
  on an image; return which predicates fire as a fingerprint dict.
  Optional `depth_path` and `spectral_path` arguments enable R107
  multi-modal predicates; absent them, those predicates correctly
  abstain.
- **`phoxelis_compare_images`** — substrate-Jaccard similarity
  between two images. Beats pHash and dHash on geometric transforms
  per R98/R99.
- **`phoxelis_install_predicate`** — install a new predicate from
  DSL source at runtime; persists for the session.

## Quick test

From this directory:

```
python3 test_mcp_server.py
```

Should report 7/7 smoke tests passing.

## Wiring into Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows)
and merge in the contents of `claude_desktop_config.json` from this
directory, replacing `/PATH/TO/...` with the absolute path to your
Aurexis checkout.

After restarting Claude Desktop, the substrate is callable:

> Show me a photo and I'll have Phoxelis evaluate it.

The LLM can then call `phoxelis_evaluate_image` with the file path and
reason symbolically over the returned fingerprint.

## What an LLM does with this

The grounded-AI claim from charter §2: "meaning carried by composable
measurements." An LLM with access to Phoxelis reasons like:

> The image fingerprint shows `has_dominant_green_hue`,
> `has_significant_red_hue` (small amount), `has_meaningful_color`,
> `has_strong_horizontal_balance`, `has_high_edge_density`. That's
> consistent with vegetation viewed from a centered angle with detail —
> probably a forest scene or close foliage.

Each clause has a measurement trail. If the user asks "why do you
think it's foliage?" the LLM points to the specific predicates that
fired, which trace to specific operators on the typed fields.

## Multi-modal usage (R107)

For images that have paired depth or hyperspectral data:

```json
{
  "image_path": "/path/to/scene.png",
  "depth_path": "/path/to/depth.npy",
  "spectral_path": "/path/to/cube.npy"
}
```

R107 predicates (`is_distant_vegetation`, `is_close_chromatic_object`,
`is_uniform_lit_far_field`) need both depth + hyperspectral. They
correctly abstain on RGB-only images.

## Performance

- Boot: ~2-3 seconds (loads 151 predicates from vocab.aurex)
- Per-image eval: ~0.4 seconds at 320×320 single-thread
- The server is single-process; concurrent tool calls serialize.

## Honest caveats

- **Stdio only.** No HTTP transport in v0.1. MCP supports both;
  stdio is sufficient for desktop client integration.
- **No allowlist.** The server reads any file path passed in
  arguments. Harden with an allowlist directory if exposing to
  untrusted callers.
- **Backward fiber not exposed.** R86-R89 image synthesis from
  predicate targets is real but fragile; not in v0.1.
- **No bulk corpus tool.** `phoxelis_evaluate_image` is single-image;
  for batch IR audit use the existing `cli_visual` script.
- **install_predicate persists for the session only.** To make a
  predicate canonical, edit `data/vision/vocab.aurex` directly via
  a documented round (R107 protocol).

## Architecture

```
LLM client (Claude Desktop)
   │  JSON-RPC 2.0 over stdio
   ▼
mcp_server.py
   │  reuses
   ▼
Aurexis Workbench Runtime (in-process)
   │  151 predicates installed at boot
   ▼
vocab.aurex + vision_ops.py + fields.py
```

The stdio JSON-RPC infrastructure was built in R72 (P-15). R115
designed the MCP protocol shell on top. R116-R118 implemented and
validated.

## Round provenance

- R54 (P-05) — in-process LLM-callable runtime
- R72 (P-15) — stdio JSON-RPC wrapper, 4 methods
- R115 — MCP tool surface design
- R116-R118 — MCP protocol implementation + 5-tool surface + smoke
  tests + this README

## Smoke test reference

```
T1_initialize         — protocol handshake returns version + capabilities
T2_tools_list         — 5 tools enumerated with valid schemas
T3_list_predicates    — 151 predicates returned
T4_evaluate_image     — fingerprint shape correct, predicates fire
T5_compare_images     — Jaccard in [0, 1]
T6_install_predicate  — new DSL predicate installed at runtime
T7_unknown_tool       — error envelope correct for unknown tool
```

All 7 should pass.
