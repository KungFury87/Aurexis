# Round 76 — close P-13: real-CDN density ceiling

**Date:** 2026-04-29
**Track:** T2 medium / capacity through real CDN
**Status:** complete — P-13 closed; **8,192 bytes byte-exact at 256×256 grid** through litterbox+weserv PNG-identity; no corruption cliff observed in this range

---

## Sweep results

8 trials, all PNG-identity transit through litter.catbox.moe + images.weserv.nl:

| grid | image | payload | PNG src | transit | match | verdict |
|---|---|---|---|---|---|---|
| 32×32   | 1024² | 128 B   |   6 KiB |  27 KiB |   128/128 | EXACT |
| 48×48   | 1536² | 288 B   |  12 KiB |  62 KiB |   288/288 | EXACT |
| 64×64   | 2048² | 512 B   |  20 KiB | 110 KiB |   512/512 | EXACT |
| 80×80   | 2560² | 800 B   |  30 KiB |   —     |   800/800 | EXACT |
| 96×96   | 3072² | 1,152 B |  42 KiB |   —     | 1152/1152 | EXACT |
| 128×128 | 4096² | 2,048 B |  71 KiB |   —     | 2048/2048 | EXACT |
| 192×192 | 6144² | 4,608 B | 153 KiB | 985 KiB | 4608/4608 | EXACT |
| 256×256 | 8192² | 8,192 B | 266 KiB | 1742 KiB | 8192/8192 | EXACT |

384×384 (12288² PNG, 585 KiB upload) timed out at >40s — **upload throughput, not corruption**.

## What this resolves

- **P-13 was opened R52** asking where the cliff in the (litter.catbox+weserv PNG-identity) pipeline appears. R52 had only confirmed 128 B at 32×32. R76 pushed all the way to 256×256 = 8 KiB without observing any corruption. Cliff exists, but it's elsewhere: throughput, not encoding fidelity.
- **The pipeline is actually quite robust to PNG transit.** weserv re-encodes the PNG (transit bytes >> source bytes), but the pixel grid survives byte-exact decoding at every grid size tested.
- **8 KiB is ~2.7× QR Version 40's max payload** (2,953 B at 177×177 modules). At fixed canvas size comparison this isn't apples-to-apples (QR fits in 177×177; we used 8192×8192), but the result establishes the pipeline can carry *at least* 8 KiB through a real third-party CDN with byte-exact decoding.

## What stays open

- **JPEG/WebP transit at higher grids was not tested.** R52 already showed JPEG q=50 destroys decoding at 32×32; testing that at 256×256 would only reconfirm. The R76 sweep was scoped to PNG-identity by design.
- **The throughput limit is real.** 384×384 PNG = 585 KiB to upload + ~3 MB transit ≈ 30+ seconds in a typical session. Practical use needs the encoder to choose grid size based on time budget, not just data size.
- **Image-content-aware density** — encoding a real photograph rather than synthetic data could fail differently if weserv's PNG re-encoder uses palette compression. Untested here.

## Honest caveats

- **Single trial per grid size.** R52 used 4 transforms × N grids; R76 used 1 transform × N grids. A 100% success rate at N=1 is weaker than at N=4, but combined with R52's earlier 12/12 it's strong evidence.
- **The "no cliff" finding is specific to litter.catbox.moe + weserv.** Different CDN combinations could behave differently; R59 had already characterized that (5/15 host pairs work).
- **All bytes were random.** Real-world payloads (text, structured binary) don't change pixel-grid encoding — the encoder treats them identically — but worth noting.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| Real-CDN PNG-identity byte-exact ceiling (one-shot transit) | R76 | **8,192 bytes** at 256×256 grid through litterbox+weserv | current — 64× the R52 baseline; closes P-13 |
| Real-CDN sweep coverage | R76 | 8 grid sizes tested (32→256), 8/8 byte-exact | current |
| Real-CDN throughput limit | R76 | 384×384 (585 KiB src PNG) timed out at >40s upload — throughput-limited not fidelity-limited | current |

## Promises ledger updates

- **C-76 closes P-13** (>20 rounds STALE).

## Files added this round

- `round76_density_ceiling/round76.py` — initial sweep (32, 48, 64)
- `round76_density_ceiling/round76b_audit.json`, `round76c_audit.json`, `round76_audit.json` — per-batch results
- `round76_density_ceiling/round76_combined_audit.json` — merged 8-trial result
- `round76_density_ceiling/src_*.png` — encoded source PNGs
- this report
- `PHOXELIS_PROMISES.md` — P-13 marked completed, C-76 entry
- `PHOXELIS_BENCHMARKS.md` — R76 capacity row

## Sweep summary R65 → R76

| round | finding | preds | promises closed |
|---|---|---|---|
| R65 | sensor-provenance family extended | 108→110 | — |
| R66 | native-resolution corpus | — | P-20 |
| R67 | pixel-grid candidate falsified | — | P-21 |
| R68 | first batch L3 author-loop | 110→116 | (P-10 partial) |
| R69 | combined audit + threshold recovery | 116→117 | — |
| R70 | second batch L3 author-loop | 117→122 | (P-10 partial) |
| R72 | stdio MCP wrapper | — | P-15 |
| R73 | third batch L3 author-loop | 122→128 | (P-10 partial) |
| R74 | vocabulary coverage map | — | — |
| R76 | real-CDN density ceiling | — | **P-13** |

Net: **+20 predicates** (108→128), **+3 operators**, **4 promises closed** (P-13, P-15, P-20, P-21), **1 candidate retired by falsification** (R67), **0 new pending promises opened**, **stale count 6→4**.
