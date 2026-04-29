# Phoxelis Promises Ledger

Every claim of "Round N+1 will do X" tracked here. Status options:

- **pending** — promised, not yet attempted
- **in_progress** — actively being worked
- **completed** — done, evidence in benchmarks/reports
- **abandoned** — explicitly retired with a reason
- **superseded** — replaced by a different approach (with pointer)

Promises that age past 5 rounds without status update get an automatic
`stale` flag in the audit script and need explicit decision (resume, abandon,
or supersede).

---

## Active promises

| id | promise | round opened | track | target round | status | notes |
|---|---|---|---|---|---|---|
| P-01 | Run IR audit on 10,000+ image corpus | R47 charter | T1 | R48 | **pending** | Source router exists since R28; never run at scale |
| P-02 | Wire L2 identity layer with external CV models | R21C design doc | L2 | R49 | **pending** | Designed in `IDENTITY_LAYER_DESIGN.md`, never built |
| P-03 | Stage capture-stability benchmark on three scenes | R28 plumbing | T1 | R29 | **pending** | Runner shipped; user hasn't staged scenes; could use synthetic alternative |
| P-04 | Phone-camera-in-the-loop test of Phoxelis encoding | R37 | T2 | R50+ | **pending** | Print + photograph + decode; substantial setup |
| P-05 | Phoxelis as MCP tool the LLM can call | R47 vision | T6 | R51 | **pending** | Wraps existing runtime as MCP server |
| P-06 | L4 compositional inference predicates (predicates over verdicts) | R47 charter | L4 | R52+ | **pending** | Trivial extension of existing runtime; not yet exercised |
| P-07 | Sensor types beyond visual added to typed-field model | R47 charter | T3 | R52+ | **pending** | Harness already collects accel + lux per frame; vocab doesn't use them |
| P-08 | Real Instagram round-trip test | R45 | T2 | R48–R50 | **pending** | Upload Round 42 PNG, apply real platform processing, screenshot, decode |
| P-09 | Bit-level FEC (BCH or LDPC) for camera transit | R41/R46 finding | T2 | R51+ | **pending** | Byte-level RS structurally fails at 8 bits/cell; bit-level needed for camera-decode |
| P-10 | LLM-as-predicate-author at scale | R47 vision | L3, T1 | R48 | **pending** | I am the LLM; subagent invocation can author predicates from caption text |
| P-11 | Web-corpus integration (ImageNet, COCO, OpenImages, YouTube frames) | R47 vision | T1 | R48 | **pending** | Web fetch tool exists; Round 28 source router is starting point |

## Recently completed (R30–R47)

| id | promise | opened | completed | evidence |
|---|---|---|---|---|
| C-30 | Frame-quality gate v0.1 in Python | R29 wrap | R30 | `frame_quality.py`, R30 doc |
| C-31 | Synthetic verification of frame-quality gate | R30 | R31 | `frame_quality_synthetics.py` (note: I claimed it ran 4/6 in R32 review; actual numbers in R30 doc) |
| C-32 | JS port of frame-quality gate | R31 | R32 | `Aurexis_ED/frame_quality_gate.js` + Node test |
| C-33 | First PVS encoding sim (16-bit kernel) | R47 charter framing | R33 | `phoxelis_sim/`, R33 doc |
| C-34 | Compress margin, find cliff | R33 | R34 | R34 saturation × distortion sweep |
| C-35 | Define .phox format with byte-exact round-trip | R34 | R35 | `phox_format.py`, R35 doc |
| C-36 | Pixel round-trip at v0.3 capacity (256 bits) | R35 | R36 | R36 results, BER tables |
| C-37 | Density push: 16×16, 32×32, 64×64 | R36 | R37 | R37 capacity table; PNG-clean 2,048 B at 512×512 |
| C-38 | Capture-noise model + predicate selection criterion | R37 | R38 | R38 finding: red_dominant + sat survive blur, edge + oex don't |
| C-39 | 8 hue-presence predicates per cell | R38 | R39 | R39 results, 768×768 PNG-clean 2,304 B |
| C-40/41 | Bit interleave + reedsolo + diagnostic | R39 | R41 | R41 finding: byte-level RS wrong layer for 8-bits-per-cell |
| C-42 | End-to-end integration demo | R41 | R42 | `phoxelis_demo_round42/` with byte-exact recovery |
| C-43 | Re-rendering survival test | R42 | R44 | R44 result: 21/31 manipulations preserve byte-exact |
| C-44 | Filter gauntlet | R44 | R45 | R45 result: 11/12 named Instagram filters survive |
| C-45 | Cell-as-symbol RS | R45 | R46 | R46 finding: same fundamental ceiling as byte-level RS |
| C-46 | Project scaffolding (charter, benchmarks, promises, tool ladder, audit script, dashboard) | R46 | R47 | this round |
| C-47 | Audit integrity check (real import + vocab parse) | R47 | R48 | `phoxelis_audit.py::integrity_check`, R48 doc; caught silent vision_ops.py + vocab.aurex truncation |
| C-48 | Restore vision_ops.py + vocab.aurex from git HEAD blob | R48 (same round) | R48 | 1502 lines / 103 predicates parse cleanly; audit reports integrity OK |

## Abandoned promises

| id | promise | opened | abandoned | reason |
|---|---|---|---|---|
| X-25 | Polarization-pair predicate (`has_local_polarization_signal`) | R24 | R25 | Empirically falsified on matte control; per-pixel anisotropy after handheld rotation is dominated by translation noise, not polarization |
| X-30-camera | Frame-quality gate operational on real phone photos | R30 | R30 (same round) | Gate rejects 100% of indoor photos because every indoor scene has eye-glints/screens triggering `has_specular_highlights`. Wrong abstraction layer for E/D artifact-capture; needs ROI-restricted scoring. Logged as Round-33 future work that has been *deprioritized* in favor of the `.phox`/Phoxelis-encoding direction. |
| X-37c-claim | "Phoxelis beats QR Version 12 at PNG transit" | R37 | R39 | Walked back: 2,048 B at 512×512 vs QR-V12's 1,666 B at 256×256 isn't apples-to-apples (4× canvas). Per-pixel density still QR's. Replaced by R44–45 categorical first which holds at fixed canvas. |

## Process commitments (R47)

- Each round opens with a read of this file. Anything pending past 5 rounds
  triggers explicit decision (resume / abandon / supersede).
- Each round closes with an entry: either a new completed row or a new
  abandonment row.
- Promises that aren't tracked here are unenforceable; if I make a verbal
  promise during a conversation that doesn't end up in this file, that's
  drift and should be noticed.
