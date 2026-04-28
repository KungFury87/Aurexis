# Phoxelis Benchmarks Registry

Every empirical measurement made on the project. Each row is a single
verified number tied to a specific round, with an explicit transit condition
and a freshness status. New measurements append; old measurements either
remain valid, get superseded by a more recent equivalent, or get marked stale
when their underlying conditions change.

**Purpose:** so I cannot quietly forget a measurement. Every claim I make in
prose has to point to a row here.

## Vocabulary health

| metric | round | value | corpus | status |
|---|---|---|---|---|
| total predicates | R26 | 103 | — | current |
| total operators | R26 | 95 | — | current |
| always-False predicates | R27 | 1 (`has_polarization_signal`) | 57 inputs | superseded by R28 |
| always-False predicates | R28 (IR at scale) | 12 (10 motion + 2 spatial) | 161 live-source images | current; motion predicates are corpus-type artifacts |
| always-True predicates (saturated) | R28 | 0 | 161 inputs | current |
| Equivalence classes | R27 | 3 | 57 inputs | superseded |
| Equivalence classes | R28 | 2 (1 degenerate motion class + 1 tautological) | 161 inputs | current |
| Fully-blocked predicates | R28 | 3 (raw_bayer, multispectral, polarization-pair-required) | 161 inputs | current; honest hardware gates |
| Independence ratio | not yet computed at scale | — | — | **OUTSTANDING — needs corpus 10×+ larger** |

## Capture stability (R28 plumbing, R28b–R29 partial run)

| metric | round | value | scene | status |
|---|---|---|---|---|
| Predicates rock-solid (1.000) across 60 same-scene captures | R29 partial | 3 of 4 (overexposed, underexposed, specular_highlights) | glass+Switch polarization session | current |
| Flapping predicates | R29 partial | 1 (has_uniform_focus, stability 0.55) | same scene | current; predicate threshold sits on noise edge |

## .phox format

| metric | round | value | notes | status |
|---|---|---|---|---|
| Round-trip byte-exactness (write→read) | R35 | 7/7 test cases pass | up to 32×32×100 = 102,400 semantic bits | current |
| Min file size (1×1×1) | R35 | 19 bytes | overhead floor | current |
| File size at 32×32 × 100 predicates | R35 | 13,828 bytes (102,400 semantic bits) | reference scale | current |

## Encoding capacity (PNG transit, lossless)

| metric | round | value | canvas | predicate stack | status |
|---|---|---|---|---|---|
| Bits round-trip byte-exact (clean) | R33 (v0.1) | 16 | 256×256 | 1 (`has_red_dominant`) | superseded |
| Bits round-trip byte-exact (clean) | R36 | 256 | 256×256 | 4 mixed | superseded |
| Bytes round-trip byte-exact (PNG-clean) | R37c | 2,048 | 512×512 | 4 mixed | current |
| Bytes round-trip byte-exact (PNG-clean) | R39 | 2,304 | 768×768 | 8 hue-presence | current |
| Bytes round-trip byte-exact (PNG-clean) | R42 | 604 (RS-Q net of 1024 raw cap) | 768×768 | 8 hue-presence | current — integration demo, real data |
| Bytes round-trip byte-exact (PNG-clean) | R46 | 2,000 RS-M net | 768×768 | 8 hue + cell-as-symbol | current |

## Encoding capacity (camera-noise transit, simulated)

| metric | round | value | canvas | predicate stack | RS strategy | status |
|---|---|---|---|---|---|---|
| Bits survivable byte-exact (light cap, no FEC) | R34 v0.2 | 1024 at sat=0.20 | 256×256 | 1 (red_dominant) | none | current |
| Bytes survivable raw at 5.5% bit-BER | R39 | 1024 raw (no FEC) | 768×768 | 8 hue-presence | none | current |
| Bytes survivable byte-exact (moderate cap, RS) | R46 | **0** (RS structurally fails — bit-BER × 8 = byte-BER ≈ 36% beyond RS) | 768×768 | 8 hue-presence | RS-M/Q/H all tested | current — *bit-level FEC required* |

## Filter survival (the categorical first — R44–45)

| filter | round | bit survival | RS recovers byte-exact? | status |
|---|---|---|---|---|
| identity | R44 | 100% | YES | baseline |
| JPEG q=95 | R44 | 100% | YES | current |
| JPEG q=85 | R44 | 99.5% | YES | current |
| JPEG q=75 | R44 | 99.7% | YES | current |
| JPEG q=50 | R44 | 97.9% | no | current |
| JPEG q=25 | R44 | 94.5% | no | current |
| JPEG q=10 | R44 | 91.2% | no | current |
| Resize 0.75×→back | R44 | 100% | YES | current |
| Resize 0.5×→back | R44 | 100% | YES | current |
| Resize 0.25×→back | R44 | 94.3% | no | current |
| Brightness ±30% (4 levels) | R44 | 100% | YES (all 4) | current |
| Contrast ±30% (4 levels) | R44 | 100% | YES (all 4) | current |
| Saturation 0.5–1.5× (4 levels) | R44 | 100% | YES (all 4) | current |
| Color cast (warm/cool/green) | R44 | 100% | YES (all 3) | current |
| Gaussian blur r=1+ | R44 | 80–98% | no | current — predicates blur-fragile |
| Clarendon | R45 | 100% | YES | current |
| Gingham | R45 | 100% | YES | current |
| Lark | R45 | 100% | YES | current |
| Reyes | R45 | 100% | YES | current |
| Juno | R45 | 100% | YES | current |
| Slumber | R45 | 100% | YES | current |
| Crema | R45 | 100% | YES | current |
| Ludwig | R45 | 100% | YES | current |
| Aden | R45 | 100% | YES | current |
| Perpetua | R45 | 100% | YES | current |
| Amaro | R45 | 100% | YES | current |
| Moon (full monochrome) | R45 | 60% | no | current — strips chroma signal by design |

**Headline: 11/12 named Instagram filters preserve byte-exact recovery.** 21/31
common image manipulations preserve. Categorical first verified.

## Phone harness

| metric | round | value | status |
|---|---|---|---|
| App version installed on Samsung S23 | R23 v3.0.1 | polarization-pair protocol added; portrait orientation locked | current |
| Capture protocols supported | R23 | 5 (calibration, repetition, symmetry, low-light, polarization-pair) | current |
| Real polarization-pair session captured | R24 | 60 frames (30 axis-0 + 30 axis-90), v3.0.1, glass+LCD scene | current |
| Polarization predicate retired (false positive on matte) | R25 | `has_local_polarization_signal` retired with documented reason | current |

## Comparison vs prior art (camera-decode capacity, where applicable)

| system | bytes camera-decoded | canvas | source |
|---|---|---|---|
| QR Version 12 | 1,666 | ~256×256 | published spec |
| Data Matrix max binary | 1,556 | 144×144 modules | published spec |
| QR Version 25 | 1,853 | ~585×585 | published spec |
| QR Version 32 | 2,431 | ~768×768 | published spec |
| QR Version 40 max | 2,953 | ~870×870 | published spec |
| Aurexis E/D V2.1 (your prior work) | 3,568 | 128×128 modules at high res | live-camera proven 2026-04-17 |
| libcimbar single-image | ~7,500 | ~33×33 modules | published spec |
| JAB Code max | ~7,900 | up to 145×145 modules × 8 colors | ISO/IEC 23634 |
| **Phoxelis (R39 8-hue, no FEC, simulated camera)** | **0 net byte-exact** | 768×768 | R46 (RS structurally fails at this density) |

**Honest position:** Phoxelis is **not currently competitive** with QR or any
of the listed systems on camera-decode capacity at any canvas size. It is
**categorically first** on filter-survival. Mixing these claims is forbidden.

## Outstanding measurements

These are claims the project has made or plans to make that don't yet have a
verified row above. They appear here so they don't get forgotten.

- **IR at scale on 10,000+ image corpus** — claimed in R47 charter, never run
- **Capture-stability benchmark on user-staged scenes** — R28 runner exists,
  user hasn't staged scenes
- **Phone-camera-in-the-loop test of any encoding** — never run; is the actual
  question for the camera-decode story
- **Real Instagram round-trip** (upload Round 42 PNG to a real social platform,
  screenshot, decode) — not run
- **L2 identity layer wiring** — designed in R21C, not built
- **L4 compositional inference predicates** — never built
- **Phoxelis as MCP tool the LLM can call** — never built
- **External CV models as L2 scaffolding** — never wired

Each row above is a thing I've said would happen and hasn't. Tracked in
`PHOXELIS_PROMISES.md` with status.

## Update protocol

When a round produces a new measurement: add a row, mark prior equivalent
rows superseded, never delete. Status values: `current` / `superseded` /
`stale` (re-run needed) / `abandoned` (with reason in PROMISES.md).
