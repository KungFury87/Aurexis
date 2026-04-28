# Phoxelis Round 42 — End-to-End Integration Demo

This folder is the first working artifact of the Phoxelis system. It contains a
real text payload encoded through the full pipeline (Reed-Solomon error
correction + bit-level interleaving + 8-hue-presence cell rendering) into a
viewable PNG image, and recovered byte-exact by decoding that PNG through the
Phoxelis runtime.

## Files

| file | size | what it is |
|---|---|---|
| `source.txt` | 604 B | Two paragraphs from `on_composable_measurement.md` — the philosophical root document of the project |
| `phoxelis_artifact.png` | 10,109 B | The rendered Phoxelis encoding, 768×768 px, viewable in any image viewer |
| `phoxelis_artifact.phox` | 11,203 B | The native Phoxelis-format file (canonical predicate states + embedded PNG render in TLV chunk) |
| `recovered.txt` | 604 B | The byte-exact recovered payload (SHA-256 matches `source.txt`) |

## How to verify byte-exactness yourself

```
# On Windows / WSL / Linux / Mac
sha256sum source.txt recovered.txt
# Both lines should print the same hash: 8edb9e583f063ab7...
```

Or:

```
diff source.txt recovered.txt    # silent = identical
```

## Encoding parameters used

* Grid: 32 × 32 cells
* Cell size: 24 × 24 pixels
* Total canvas: 768 × 768 pixels
* Bits per cell: 8 (one per named hue band)
* Raw cell capacity: 1024 bytes (32×32 cells × 8 bits)
* Reed-Solomon: RS(255, 191) — 64 parity bytes per 255-byte block (RS-Q)
* RS-encoded payload: 860 bytes
* Net payload: **604 bytes**

The 8 hue carriers per cell are the named-hue presence predicates that the
Phoxelis vocabulary already defines (`has_significant_red_hue`,
`has_significant_orange_hue`, `has_significant_yellow_hue`,
`has_significant_green_hue`, `has_significant_cyan_hue`,
`has_significant_blue_hue`, `has_significant_violet_hue`,
`has_significant_magenta_hue`). Each cell is rendered as a 4×2 mosaic of
sub-rectangles where each sub-rectangle is either saturated band-color (bit=1)
or mid-gray (bit=0). The decoder evaluates the same predicates on each cell's
pixels and recovers 8 bits per cell.

## What this demonstrates

This is the first round where the project exists as a working integrated
*system*, not as individually-tested components. Twelve rounds of work
(R31–R42) chained together:

1. The vocabulary (Round 27 IR audit confirmed empirically clean at 161 images)
2. The runtime (predicate evaluation over typed field bundles)
3. The `.phox` format (Round 35 byte-layout spec)
4. The encoder (constructive cell synthesis)
5. The decoder (pixels → predicate states via the runtime)
6. The error-correction layer (Reed-Solomon over GF(256) with bit-level interleaving)

The PNG file is plain enough that any image viewer can open it. The .phox file
is the source-of-truth canonical representation. The byte-exact recovery
through the PNG is the demonstration that the architecture works.

## What this does NOT yet demonstrate

* **Phone-camera capture.** PNG round-trip is lossless storage; phone capture
  introduces blur, sensor noise, color cast, and JPEG compression. Round 41
  measured ~5.5% bit-BER under simulated camera noise at this density, which
  byte-level RS could not recover. Round 43+ will pursue bit-level FEC (BCH or
  convolutional) for camera transit.
* **Capacity competitive with QR.** This demo holds 604 net bytes in a 768×768
  canvas. QR Version 18 holds ~750 bytes binary in a much smaller (~400×400)
  canvas. Phoxelis is not yet competitive on per-pixel capacity for camera
  transit; it has architectural firsts but not capacity firsts on standard axes.
* **Unique re-rendering survival.** The .phox file's claim that "predicate
  states survive re-rendering" hasn't been tested against actual re-rendering
  attacks (re-saving the PNG through different image software, etc.). Round 44+.

## What the philosophical claim says about this artifact

From `on_composable_measurement.md`:

> Predicates over composed measurements can carry meaning. Not derive meaning
> from elsewhere, not be assigned meaning by an interpreter, not stand for
> something else — *carry* meaning, in the same way a sentence carries meaning,
> except that the carrying is done by the computational structure of the
> predicate itself rather than by any associative bridge to a referent.

The PNG in this folder is one specific test of that claim. The 604 bytes of
text are encoded into the PNG via 1024 cells, each cell holding 8 predicate
verdicts. To recover the bytes, the decoder runs the predicates on the pixels
and reads the verdicts as bits. There is no associative lookup, no learned
embedding, no statistical decoder — just composable measurements over a typed
field bundle.

The byte-exact recovery is empirical evidence that the predicates *are*
carrying the meaning, in the sense the essay describes.
