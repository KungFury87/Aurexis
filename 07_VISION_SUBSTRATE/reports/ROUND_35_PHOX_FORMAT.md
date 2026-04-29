# Round 35 — `.phox` format v0.1 (Phoxelis-native image file)

**Date:** 2026-04-28
**Headline:** First version of a Phoxelis-native image file format where
**predicate states over a cell grid are the canonical content**, not
pixel values. Pixels become a downstream rendering for display or for
transport through pixel-only channels. Round-trip writer/reader is
byte-exact across 7/7 tests.

## Why this exists

Round 34 (v0.2 saturation × distortion sweep) ran the encoding
simulation against JPEG/PNG/Gaussian distortions and produced the
first real cliff curve. That sweep tested whether predicates *survive*
a pixel round-trip. The deeper move — the one this round takes — is to
**not have a pixel round-trip at all**. The file IS the predicate-state
structure. Pixels become an optional rendering for display, not the
canonical representation.

This directly instantiates the philosophical claim. *"Meaning is
carried by composable measurements"* stops being a thing the runtime
observes and becomes a thing the file format encodes. The .phox file
is the composition.

## What shipped

`Aurexis_Workbench_v2_0/phoxelis_sim/phox_format.py` — ~280 lines.
Full byte-layout spec, `PhoxImage` dataclass, byte-exact `write_phox`
and `read_phox` functions. No pixel logic in this module — that's
Round 36's renderer.

### Byte layout (v0.1)

All integers little-endian.

```
HEADER (16 bytes fixed)
  bytes 0..3   magic        'PHOX'
  byte  4      version      0x01
  bytes 5..6   grid_w       uint16 (number of cell columns)
  bytes 7..8   grid_h       uint16 (number of cell rows)
  byte  9      n_predicates uint8 (1..255)
  bytes 10..15 reserved     must be zero

PREDICATE TABLE (variable; n_predicates entries)
  for each entry:
    byte 0      name_length uint8
    bytes 1..N  name        UTF-8

CELL DATA (n_cells * cell_byte_size bytes)
  cell_byte_size = ceil(n_predicates / 8)
  for each cell in row-major order (gy then gx):
    packed bit array — bit i is the verdict of predicate i

OPTIONAL TAIL (TLV chunks, repeated until EOF)
  byte  0     type     uint8 (0x01=PNG render, 0x02=JPEG render,
                              0xFF=user metadata)
  bytes 1..4  length   uint32
  bytes 5..   payload  bytes
```

### Test results

All 7 tests pass:

```
smallest                 (1x1 x 1):       19 bytes  PASS
v0.1 capacity            (4x4 x 1):       49 bytes  (16 semantic bits)  PASS
v0.3 capacity            (8x8 x 4):      161 bytes  (256 semantic bits)  PASS
full vocab               (16x16 x 100):  4244 bytes  (25600 semantic bits)  PASS
scaled                   (32x32 x 100): 13828 bytes  (102400 semantic bits)  PASS
determinism              (8x8 x 3):       86 bytes  PASS
with chunks              (2x2 x 3 + 2 chunks):    51 bytes  PASS
```

## Information density across formats — same 256×256 canvas

```
format                                    bytes   semantic bits  ratio vs RGB
raw RGB 256x256                          196608         1572864      1.0x
PNG-rendered (typical lossless)          ~50000         ~400000      ~4x compressed
JPEG q=75 (typical web)                  ~12000          ~96000      ~16x compressed
.phox 8x8 x 4 (v0.3 capacity)               161             256      1221x smaller
.phox 16x16 x 100 (full vocab)             3844           25600      51x smaller
.phox 32x32 x 100                         13828          102400      14x smaller
.phox 64x64 x 100 (business card scale)   53764          409600      4x smaller
```

### Reading the table honestly

`.phox` is **not "JPEG compressed harder."** It's a different unit
being stored. JPEG stores pixel values; `.phox` stores predicate
states. Two different abstractions, not substitutes.

The 1221× ratio at v0.3 capacity reflects the fact that we're storing
256 bits of *semantic content* vs the pixel-storage's 1.5M bits of
*pixel-content*. The denser the semantic encoding (more predicates ×
more cells), the more `.phox` bytes you need — at 64×64 cells × 100
predicates the file approaches 1/4 the raw RGB size while carrying
410,000 bits of structured semantic information.

## What this format earns the project

1. **Lossless predicate-state preservation.** Two `.phox` files with
   identical `cell_states` are byte-identical regardless of pixel
   rendering. JPEG round-trips can flip predicates near decision
   boundaries (Round 34 v0.2 demonstrated this directly: at sat=0.10
   JPEG quality 50 actually made things worse than quality 5 because
   the chroma subsampling was non-monotonic).

2. **Renderable to any pixel format.** `.phox → renderer → PNG/JPEG/raw`
   is one-way deterministic synthesis. The `.phox` is canonical;
   pixels are the rendering target. Round 36 builds this.

3. **Decodable from any pixel format.** `pixels → vocabulary → .phox`
   is the inverse. Round 36 also builds this. The round-trip
   `.phox → render → JPEG → capture → decode → .phox'` is the actual
   end-to-end PVS experiment.

4. **Native to the runtime.** Loading a `.phox` IS evaluating the
   vocabulary structurally — no impedance mismatch between "what's
   in the file" and "what the runtime sees."

5. **Tiny enough to be definitive.** ~280 lines. Anyone reading the
   byte-layout spec can implement a compatible reader in any language.
   Byte-exact determinism makes it suitable for hashing, signing,
   versioning.

## Math for the 10 MB / business-card target

```
10 MB           = 80,000,000 bits
÷ 100 preds/cell = 800,000 cells needed
≈ 1100 × 730     cell grid (business-card aspect)

storage cost: ~10 MB (.phox file ~1:1 with payload at this density)
```

The `.phox` format doesn't magically compress you to the target. It
gives you a different *kind* of bit. The 10 MB question becomes:
**can a phone camera reliably read 100 predicate verdicts per cell
across an 1100×730-cell grid printed on cardstock?** That's the
empirical question the rest of the simulation curve answers.
v0.3 (4 predicates per cell at saturation 0.30 with ~10× margin) was
the first data point. v0.4+ scales it up. v0.5+ adds phone-camera-in-
the-loop.

## What this round does NOT do

* No renderer. `PhoxImage → pixels` is Round 36+.
* No vocabulary-based decoder. `pixels → PhoxImage` is Round 36+.
* No round-trip through real pixel formats. The 7 tests are
  byte-exact write/read of `PhoxImage` objects, which is the
  foundation but not the full claim.
* No compression of the format itself. v0.2+ may add a chunk
  type that brotli-compresses the cell-data section. Not needed
  yet — at v0.3 capacity the files are already small.

## Vocabulary state after Round 35

Unchanged. **103 predicates, 95 operators, 38 synthetic scenes.**
The `.phox` format consumes the vocabulary by name (predicate
names go in the predicate table); it doesn't extend or modify the
vocabulary itself.

## What lands next

**Round 36**: `phox_renderer.py` and `phox_decoder.py`. The renderer
takes a `PhoxImage` and synthesizes pixels that satisfy the
predicate constraints — i.e., it reverse-engineers a pixel pattern
where running the Phoxelis vocabulary on each cell would produce
the listed verdicts. The decoder takes pixels and runs the
vocabulary to produce a `PhoxImage`. The round-trip
`PhoxImage → render → JPEG → load → decode → PhoxImage'` is the
real end-to-end PVS demonstration.

**Round 37**: phone-camera-in-the-loop. Print a rendered `.phox`
artifact, photograph it with the harness, decode the photo back to
`PhoxImage`, compare. This is where Donald's phoxel-law work directly
applies — what predicates *survive* display→capture is the empirical
load-bearing question.
