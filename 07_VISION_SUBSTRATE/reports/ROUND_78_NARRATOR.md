# Round 78 — Phoxelis narrator at full vocabulary scale

**Date:** 2026-04-29
**Track:** T6 / substrate-purpose deliverable
**Status:** complete — narrator runs full 128-pred vocab, emits human-readable description per image, demonstrates "meaning carried by composable measurements"

---

## What got built

`round78_narrator/phoxelis_narrate.py` — single-script narrator. Takes one
or more image paths (PNG/JPG/NPY), loads vocab, runs all 128 predicates,
groups verdicts into 12 themed clusters, emits a description per image.

Themes:
1. exposure / brightness   2. contrast / dynamic range
3. focus / sharpness        4. lighting direction
5. color palette            6. color temperature
7. channel dominance        8. hue presence
9. edges and structure     10. composition
11. content hints          12. capture provenance

Plus an `[other]` bucket for unclassified fired predicates.

## Sample output (5 images)

### iNat 356380102 (500×400) — 22/125 fired

```
[focus / sharpness]    uniform focus
[color palette]        high saturation; high color diversity
[color temperature]    warm color temperature
[channel dominance]    red dominant
[hue presence]         orange, yellow, green
[edges and structure]  gradient energy, circular, many corners, many small blobs
[composition]          horizontal balance, vertical balance, horizon at middle
[content hints]        indoor, busy textured
[capture provenance]   chroma subsampled, extreme chroma subsampling
```
→ Reads as a warm-toned, color-rich macro/close subject with multiple
small features. Plausible iNaturalist content (flower/insect macro).

### iNat 356382869 (500×361) — 21/125 fired

```
[color palette]        minimal palette diversity
[channel dominance]    red dominant
[composition]          perspective convergence, atmospheric haze
[other]                depth indicators
```
→ Distant landscape with depth cues (haze + perspective). Plausible.

### iNat 356383380 (281×500) — 30/125 fired

```
[lighting direction]   center weighted lighting, specular highlights
[color temperature]    warm palette, strongly warm palette
[content hints]        text like, skin tone, indoor, indoor warm
```
→ Center-lit warm scene. The narrator reports `text like` and
`skin tone` — these may be over-firing on this corpus type, but the
report is *faithful* to what the substrate measured.

### Screenshot `-LIMS-.jpg` (1280×811) — 36/125 fired

```
[exposure / brightness]  overexposed dominant, high key, clipped highlights
[color palette]          pure grayscale, monochrome, largely achromatic
[hue presence]           red, orange, yellow, blue (low-saturation residue)
[content hints]          overexposed low saturation
[capture provenance]     chroma subsampled, clipped highlights
```
→ Bright text/form screenshot, blown highlights, near-monochrome.
Correctly describes a LIMS web form screenshot.

### Screenshot `-VOR-SBO-audio-Signal.png` (1280×134) — 39/125 fired

```
[edges and structure]    horizontal dominant edges, strong horizontal
                          orientation mass, repetitive horizontal structure
[composition]            significant negative space, horizon at bottom third
[content hints]          text like, text dominant subject, textured blue dominant
[channel dominance]      strongly blue dominated
```
→ Wide-aspect blue-dominated panel with strong horizontal repetition.
Sounds like a waveform/spectrogram display. Correct.

## What this demonstrates

The narrator output is generated **purely from composable measurements**
— no learned representation, no embedding model, no caption-trained
network. Each clause traces back to typed fields (luma, color, burst)
through registered operators (mean, std, FFT peak, gradient energy,
chroma HF) into Boolean predicates with explicit thresholds.

This is the substrate's central philosophical claim under direct
demonstration: *meaning carried by composable measurements rather than
by symbols correlated to signal during training.* The narrator is the
philosophical claim made operational.

## Honest caveats

- **Theme assignments are hand-curated.** 12 clusters chosen by what
  looks coherent; new predicates need to be added to the right theme
  list. Future versions could derive theme clusters automatically from
  the R77 Jaccard matrix (predicates that often co-fire belong to the
  same theme).
- **Some "content hint" predicates over-fire.** R74's LOW bucket
  predicates (`screen_is_dominant_concept`, etc.) fire occasionally
  on edge cases. The narrator faithfully reports them; deciding
  whether to suppress is a presentation choice, not a substrate one.
- **No paragraphs, no linguistic flow.** Output is structured
  `theme: bullet list`. A paragraph-style narrator would be a thin
  presentation layer over the same data.
- **Single image only.** Doesn't yet handle bursts, sessions, or
  comparisons between images.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| Phoxelis narrator at full vocab scale | R78 | 128 predicates → 12 themed clauses; runs ~1s/image; tested on 5 corpus images, all produce coherent descriptions | current — first full-vocab narrator since R16's 33-pred version |
| Predicates fired per image (sample) | R78 | 21–39 / 125 across 5 images (range 17%–31%) | current |

## Promises ledger updates

- **C-78 closes:** narrator demonstration; substrate-purpose deliverable. Partial fulfillment of P-10 (LLM-as-author) since the narrator IS the substrate's voice.

## Files added this round

- `round78_narrator/phoxelis_narrate.py` — single-file narrator
- `PHOXELIS_PROMISES.md` — C-78 entry
- this report

## How to use

```
python3 round78_narrator/phoxelis_narrate.py path/to/image.jpg
python3 round78_narrator/phoxelis_narrate.py img1.png img2.npy
python3 round78_narrator/phoxelis_narrate.py     # demo on cached corpus
```

## Next round opens with

R79 — fourth batch L3 author-loop targeting LOW-coverage axes (red,
magenta, diagonal, rectilinear) per R74 coverage map.
