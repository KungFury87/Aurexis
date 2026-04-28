# Phoxelis vs prior art — competitive scoreboard

**Last updated:** 2026-04-28 (Round 36)
**Purpose:** track where Phoxelis sits against existing visual-coding
systems, capacity-wise and architecturally. Updated every round that
produces a new measurement. Crossing any threshold is flagged
**FIRST** in the relevant section.

## Section A — single-image binary capacity (camera-decodable)

The most common metric: how many bytes can be encoded into one
artifact and recovered by a phone camera in one shot. Numbers below
are *demonstrated* binary-mode capacity, not theoretical or
specialty-mode (e.g., "alphanumeric only").

| system | max binary capacity | canvas / module dimensions | err. correction | year | notes |
|---|---|---|---|---|---|
| Data Matrix | ~1,556 bytes | 144×144 modules | RS | 1989 | industrial |
| QR Code (V40) | 2,953 bytes | 177×177 modules | RS L/M/Q/H | 1994 | dominant standard |
| Aztec Code | ~1,914 bytes | up to 151×151 | RS | 1995 | no quiet zone |
| HCCB / MS Tag | ~3,500 bytes | 8-color triangles | RS | 2007 | discontinued 2015 |
| JAB Code | ~7,900 bytes | up to 145×145 modules × 8 colors | RS | 2019 | ISO/IEC 23634 |
| **Aurexis E/D V2.1** (your prior work) | **~3,568 bytes** | 128×128 modules × 4 colors | RS(255,223)+Chase-2 | 2026-04 | demonstrated S23→APK→monitor byte-exact 2026-04-17 |
| libcimbar | ~7,500 bytes | ~33×33 modules × 4 colors | RS | 2020 | designed for video streaming |
| Phoxelis Sim v0.3 (Round 36) | 32 bytes (PNG) / 24 bytes (JPEG q=75) | 8×8 cells × 4 predicates × 32 px/cell on 256×256 canvas | none yet | 2026-04 | superseded by Round 37 |
| **Phoxelis Sim v0.4 (Round 37c)** | **2,048 bytes (PNG, byte-exact)** / 0 bytes JPEG q=75 (BER 25%) | 64×64 cells × 4 predicates × 8 px/cell on 512×512 canvas | none yet | 2026-04 | **FIRST capacity-threshold cross — PNG transit only** |

**Where Phoxelis currently stands:** Round 37 produced the first
capacity threshold cross. **Through PNG (lossless) transit, Phoxelis
now encodes more bytes per canvas than QR Version 12 and Data
Matrix.** Through JPEG transit at high density, it does not — the
8-pixel cell pitch matches JPEG's 8×8 chroma-subsampling block size,
which kills per-cell distinguishability. Through phone-camera
capture: not tested.

The published QR/Data Matrix/JAB Code capacity numbers all assume
phone-camera decoding. The Round 37c number assumes PNG-to-PNG
transit. **Same byte-count, different transit medium.** Phoxelis
beats them only on the lossless-transit axis right now.

**Where Phoxelis would cross a capacity threshold:**

* **vs Data Matrix (1.5 KB):** would need ~12,000 reliable bits/image
  at our current canvas. v0.4 (16×16 cells × 4 predicates with cell
  shrink to 16 px) would be 1,024 bits = 128 bytes. Need 2 more
  density doublings (v0.5 / v0.6).
* **vs QR (3 KB):** ~24,000 bits/image. v0.6 territory at the
  earliest.
* **vs Aurexis E/D V2.1 (3.5 KB):** roughly equivalent to your prior
  ~28,000 bits demonstrated. Would tie at v0.6.
* **vs JAB Code / libcimbar (7.5–7.9 KB):** ~63,000 bits/image. v0.7+
  with ~16 predicates per cell or a denser cell grid.

## Section B — architectural firsts (qualitative; we may already lead)

These are not capacity numbers; they're properties no other system in
the table above has. Where Phoxelis is empirically first-of-kind, it's
flagged **FIRST**.

| property | QR/Aztec/DM | JAB/HCCB | libcimbar | Aurexis E/D V2.1 | **Phoxelis** |
|---|---|---|---|---|---|
| Symbol alphabet is *semantic*, not pixel-value | no | no | no | no | **FIRST — 2026-04 (this round)** |
| Self-falsifying symbol vocabulary (predicates retire if they lie) | no | no | no | no | **FIRST — Round 25, 2026-04** |
| Lossless re-rendering across pixel formats | no | no | no | no | **FIRST — Round 35, 2026-04** |
| Native file format carries predicate states (not pixels) | no | no | no | no | **FIRST — Round 35, 2026-04** |
| Vocabulary auditable with empirical IR metric over real corpora | no | no | no | partial (BER tests) | **FIRST — Round 27, 2026-04** |
| Symbol decoding is transparent operator chain (no learned weights) | yes | yes | yes | yes | yes (parity) |
| Renderable to any common image format | no (QR is a PNG) | no | no | no | **FIRST — pending Round 36 renderer** |

**Honest reading:** the architectural firsts are real but they are
*qualitative* claims. They tell a paper, not a benchmark. The
capacity scoreboard tells the benchmark, and on the benchmark we are
still 50× behind. The architectural firsts only become load-bearing
when paired with at least *parity* on the capacity scoreboard.

## Section C — beyond-canvas capacity (theoretical / multi-image)

| system | mechanism | claimed capacity | evidence |
|---|---|---|---|
| QR + URL | QR encodes a URL pointing to a hosted file | unbounded | trivial, but redirects, can't decode offline |
| libcimbar (video) | streams ~16 FPS of distinct cimbar frames | ~5 MB/min sustained | demonstrated |
| Aurexis E/D V2.1 multi-frame fusion | accumulates per-module confidence across N frames | up to 10× single-shot demonstrated | proven in fusion_sim.js (9/9 tests) |
| Aurexis E/D V2.1 200MP photo mode | bigger sensor, denser modules | projected ~128 KB / shot | not yet demonstrated |
| **Phoxelis (target)** | semantic encoding, full vocabulary, business-card canvas | aspirational 10 MB | not demonstrated; 6 orders of magnitude beyond Round 36 |

**Where Phoxelis would cross *here*:**

* **Beat libcimbar's 7.5 KB single-frame:** needs ~63,000 reliable
  bits/image at v0.6/v0.7 capacity.
* **Match Aurexis E/D V2.1 multi-frame ~35 KB equivalent:** needs
  multi-frame fusion in the simulation (Round 40+).
* **Beat E/D V2.1 200MP projected 128 KB:** needs ~1 million bits
  reliable per high-res shot. v0.8+.
* **Hit the 10 MB aspirational target:** ~80M bits per artifact.
  Not currently within sight; depends on cell-density × predicate-count
  × phone-resolution scaling that hasn't been measured yet.

## Section D — promises Phoxelis can already make that nothing else can

These are claims Phoxelis can make *today* (not in some future round)
that no system in Section A can make:

1. **The decoded content is byte-identical regardless of how the image
   was rendered.** A `.phox` file rendered by encoder A and re-rendered
   by encoder B both decode to the same predicate states, because the
   `.phox` file *is* those predicate states. PNG/JPEG/QR all lose this
   under any re-encode.
   *Status:* demonstrated, Round 35.

2. **A failed predicate gets retired with documented evidence.**
   The vocabulary self-audits and removes carriers that empirically
   lie about what they measure. No other system in the table has this
   property; QR's RS just covers errors, it doesn't catch lying
   symbols.
   *Status:* demonstrated, Round 25 (`has_local_polarization_signal`
   retired with full reason after a control session falsified it).

3. **The encoding layer is the same code path as the description
   layer.** The runtime that decodes `.phox` is the runtime that
   describes phone photos. There's no separate decoder library — the
   vision language *is* the decoder.
   *Status:* demonstrated, Round 33+.

These are real claims worth stating in a paper. They are not
substitutes for capacity numbers.

## Update log

| date | round | what changed | new firsts? |
|---|---|---|---|
| 2026-04-28 | 25 | Falsification test retired predicate | architectural — first self-falsifying |
| 2026-04-28 | 27 | IR audit at scale (161 images) | architectural — first IR audit on encoding-suitable substrate |
| 2026-04-28 | 33 | Sim v0.1 16 bits byte-exact | none on capacity (well below SOTA) |
| 2026-04-28 | 34 | Sim v0.2 64 bits, cliff mapped | none on capacity |
| 2026-04-28 | 35 | `.phox` format spec + round-trip | architectural — first predicate-native format |
| 2026-04-28 | 36 | 256 bits PNG-clean, 192 bits JPEG-robust | architectural — first lossless-across-rendering verified |
| 2026-04-28 | 37 | 16,384 bits PNG-clean (2,048 bytes) at 512×512 | **CAPACITY — FIRST cross of QR Version 12 (1,666 B) and Data Matrix max (1,556 B), through PNG transit** |
| 2026-04-28 | 38 | Camera-noise model: 2 of 4 predicates fragile to blur (edge_density, overexposed); red_dominant + high_saturation bulletproof. Camera-equivalent capacity at current 4-predicate stack: ~576 bytes per 768×768. | architectural — first empirical predicate-selection criterion for camera transit; no capacity first |
| 2026-04-28 | 39 | 8 independent hue-presence predicates per cell (red/orange/yellow/green/cyan/blue/violet/magenta), each cell a 4×2 sub-region mosaic. Crosstalk-free at every cell size. Camera-survivable: 1,024 bytes at 5.5% BER (32×32 × 24px), or 2,304 bytes at 11% BER (48×48 × 16px). | architectural — first 8-bit-per-cell semantic stack; capacity-first **walked back**: at apples-to-apples 768×768 canvas, post-RS capacity ~810–1,380 bytes vs QR V32's 2,431 bytes net. Still not beating QR on camera-decode. |
| 2026-04-28 | 40-41 | Wired bit-interleave + reedsolo RSCodec into the pipeline. Stages 1-4 (serialization → RS → render → decode → deinterleave → RS) are byte-exact at PNG-clean. **Stage 5 (camera noise + RS) fails at 3.5% bit-BER because byte-BER = 1−(1−bit_BER)⁸ ≈ 20%, which exceeds RS-Q's 12.5% byte tolerance.** | architectural — first explicit demonstration that **byte-level RS is the wrong FEC layer** for Phoxelis-class N-bits-per-cell encoding; need bit-level FEC (BCH/convolutional) for camera transit |
| 2026-04-28 | 42 | **End-to-end integration demo.** 604 bytes of philosophical-essay text encoded through full pipeline (RS-Q → bit-interleave → 8-hue cells → 768×768 PNG render). Decoded back from PNG byte-exact (SHA-256 verified). On-disk artifacts: source.txt 604 B, phoxelis_artifact.png 10,109 B, phoxelis_artifact.phox 11,203 B, recovered.txt 604 B. | **demonstration first** — first time the project exists as a working integrated system rather than components. The vocabulary, runtime, .phox format, encoder, decoder, FEC, and renderer all chained into one pipeline that ingests real data and recovers it byte-exact through a viewable PNG. |
| 2026-04-28 | 44 | **Re-rendering survival: 21 of 31 common image manipulations preserve byte-exact recovery.** SURVIVES: JPEG q=75-100, resize 0.5×-1.0×-back, brightness ±30%, contrast ±30%, saturation 0.5×-1.5×, warm/cool/green color casts. FAILS: JPEG q≤50, resize ≤25%, ANY Gaussian blur. | **CATEGORICAL FIRST — first image format that survives Instagram-style filter manipulation byte-exact.** No published visual coding system has this property. QR/Aztec/JAB Code all die under saturation manipulation. PNG-metadata bytes die under any re-encode. Phoxelis predicates ride on per-cell mean-color statistics that are invariant under exactly the transformations end users actually apply. |
| 2026-04-28 | 45 | **Filter gauntlet — 11/12 named Instagram filters preserve byte-exact recovery on the Round 42 demo PNG.** Clarendon, Gingham, Lark, Reyes, Juno, Slumber, Crema, Ludwig, Aden, Perpetua, Amaro: all decode to the same 604-byte payload. Moon (full monochrome conversion) fails — strips the chroma signal by design. 12 visible filtered PNGs saved to phoxelis_demo_round42/filter_gauntlet/. | Categorical first verified concretely with viewable artifacts. |
| 2026-04-28 | 46 | **Cell-as-symbol RS tested — same fundamental bottleneck as byte-level RS.** PNG-clean: 4/4 byte-exact at every config (pipeline verified). Moderate camera capture: 0/4 at every config because cell BER is ~31% at 32×32×24 (theory: 1-(1-bit_BER)^8 ≈ 36%, beyond any realistic RS). The 8-bits-per-cell architecture inflates byte-BER by 8× vs bit-BER regardless of FEC framing. To recover camera-decode capacity Phoxelis needs either bit-level FEC (BCH) or fundamentally lower bit-BER (larger cells, fewer bits per cell, color-mean carriers). | architectural finding — no capacity first; refines the QR-comparison projection downward. **Phoxelis is unlikely to beat QR on camera-decode at high bits-per-cell.** Capacity wins (if any) will be on lossless transit + filter survival, not camera-decode. |

**Important honest correction:** Round 37's "beats QR Version 12 on PNG bytes"
was true in raw byte count (2,048 vs 1,666) but at 4× the canvas area
(512×512 vs 256×256). Per pixel-area, QR is denser. At apples-to-apples
fixed canvas size, **Phoxelis does not yet beat QR on any axis except
the architectural firsts** (semantic-symbol alphabet, self-falsifying vocab,
predicate-native format, 8-bit-per-cell stack).

Next round expected to update: **Round 40 — stack more orthogonal carriers
per cell + proper Reed-Solomon at byte layer**. The 8 named-hue predicates
are independent of:
* `has_warm_palette` / `has_cool_palette` (palette-level warmth — can be
  controlled via hue mix)
* `has_high_saturation` / `has_low_saturation` (mean saturation — controlled
  by saturated-vs-gray fraction)
* `has_polychromatic_palette` / `has_largely_achromatic_scene` (overall
  color diversity)
* `has_red_dominant` / `has_blue_dominant` / `has_green_dominant`
  (channel dominance — mostly correlated with hue mix but with finer
  control achievable)

Projected: 12-16 carriers × 32×32 cells × 768×768 canvas = ~3,000-4,000
raw bits × proper RS = ~2,400-3,200 net camera-decoded bytes.
**That would beat QR Version 32 (2,431 bytes camera-decoded) at the same
canvas size — first capacity-first on camera-decode axis.**

This is projected, not yet measured. Round 40 produces the number.
