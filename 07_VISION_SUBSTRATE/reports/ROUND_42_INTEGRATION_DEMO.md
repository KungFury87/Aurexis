# Round 42 — End-to-end integration demo (the project as a working system)

**Date:** 2026-04-28
**Headline:** First time Phoxelis exists as a working integrated pipeline,
not as separately-tested components. 604 bytes of real philosophical-essay
text encoded through RS-Q + bit-interleave + 8-hue-cell rendering into a
768×768 PNG, decoded byte-exact through the runtime. Verifiable artifacts
on disk in `phoxelis_demo_round42/`.

## Why this round was the right next move

The previous twelve rounds (R31–R41) added components — vocabulary, runtime,
`.phox` format, encoder, decoder, RS, interleaving — without ever assembling
them into one pipeline that ingests real data and produces a verifiable
artifact. Round 41 specifically revealed a structural finding (byte-level RS
is wrong for N-bits-per-cell encoding under camera noise) but didn't produce a
demonstrable working system.

This round closes that gap. The deliverable is a folder of files anyone can
inspect: source text, rendered PNG, native `.phox` file, recovered text. The
recovery is byte-exact, SHA-256 verified.

## What the pipeline does

```
source.txt (604 bytes, UTF-8 text)
    ↓
RS-Q encode  (RSCodec(64), encoded = 860 bytes)
    ↓
Pad to capacity  (860 + 164 zero-bytes = 1024 bytes raw cell capacity)
    ↓
Bit interleave   (column-major: byte i bit j → stream position j*1024 + i)
    ↓
Pack into 32×32 grid of 8-bit cells   (8192 bits → 1024 cells × 8 bits each)
    ↓
Render each cell as 24×24 px 4×2 hue mosaic
    (each sub-rectangle is saturated band-color if bit=1, gray if bit=0)
    ↓
phoxelis_artifact.png  (768×768 RGB, ~10 KB on disk after PNG compression)
phoxelis_artifact.phox (canonical predicate-state file with embedded PNG)

  --- ROUND TRIP STARTS HERE ---

Load phoxelis_artifact.png as numpy array
    ↓
Split into 32×32 grid of 24×24 px cells
    ↓
For each cell: convert RGB→HSV, count saturated pixels in each of 8 hue bands,
    test fraction > 10% threshold → 8 boolean verdicts per cell
    ↓
Pack verdicts into bit stream (row-major)
    ↓
De-interleave  (inverse of column-major transpose)
    ↓
RS-Q decode (corrects up to 32 byte errors per 255-byte block)
    ↓
Strip padding, return first 604 bytes
    ↓
recovered.txt
```

## On-disk artifacts

```
phoxelis_demo_round42/
├── README.md                      explains the demo to a new reader
├── source.txt                     604 B — paragraphs from the philosophical essay
├── phoxelis_artifact.png         10,109 B — viewable in any image viewer
├── phoxelis_artifact.phox        11,203 B — native format with embedded PNG
└── recovered.txt                   604 B — byte-exact match to source
```

SHA-256 of source.txt = SHA-256 of recovered.txt = `8edb9e583f063ab7…`

## What is now true that wasn't true before this round

1. **The Phoxelis encoding pipeline ingests real-world data and produces
   verifiable artifacts.** The 604 bytes of text aren't synthetic random
   bytes; they're real prose from the project's own philosophical document.
   The PNG file is a real image. The recovery is byte-exact.

2. **The architecture works as a chain.** Six independent components had
   each been verified individually before this round (vocabulary, runtime,
   `.phox` format, encoder, decoder, RS+interleave). Now they work as a
   sequence with no impedance mismatch.

3. **Anyone with the artifacts can independently verify the claim.** The
   files are on disk. Reading `recovered.txt` and comparing it to
   `source.txt` is a one-command check (`diff` or `sha256sum`). No special
   tools needed beyond standard Unix utilities.

## What is still NOT true

* **Phone-camera capture is not yet demonstrated.** This demo is PNG
  round-trip — lossless storage transit. Phone capture introduces blur,
  sensor noise, color cast, JPEG, and Round 41 measured 3.5–5.5% bit-BER
  under simulated camera noise at this density, beyond byte-level RS
  recovery. Round 43 needs bit-level FEC.

* **Phoxelis is not yet competitive with QR on capacity per pixel-area.**
  This demo holds 604 bytes in a 768×768 canvas (393 KP). QR Version 18
  holds ~750 binary bytes in roughly 400×400 (160 KP). On per-pixel
  density Phoxelis is still well behind QR.

* **Re-rendering survival is not yet tested.** The .phox claim ("identical
  predicate states regardless of pixel rendering") is theoretical until
  we actually re-render the PNG through different image software and
  verify the predicate states survive.

## Where this fits in the scoreboard

Updated scoreboard entry (in `PHOXELIS_VS_PRIOR_ART.md`):

> Round 42: **demonstration first** — first time the project exists as
> a working integrated system rather than components. Six independent
> sub-systems chained into one pipeline that ingests real data and
> recovers it byte-exact through a viewable PNG. Not a capacity first;
> a coherence first.

## What lands next

**Round 43**: bit-level FEC (BCH(255, 131) over GF(2)) replacing the
byte-level reedsolo. Re-runs the full pipeline through the Round 41
camera-noise model. If BCH recovers byte-exact at 5.5% bit-BER, we have
the first end-to-end Phoxelis camera-decode-survivable pipeline. Net
capacity projects to ~520 bytes per 32×32×24 (24-px cell) configuration —
still under QR Version 18 but the first real point on that axis.

**Round 44**: re-rendering survival. Open `phoxelis_artifact.png` in a
common image editor (Pillow JPEG, Photoshop equivalent, GIMP), re-save
with mild quality reduction, attempt decode. Test how many predicates
survive different re-encoding paths. This validates (or falsifies) the
core architectural claim of `.phox`.
