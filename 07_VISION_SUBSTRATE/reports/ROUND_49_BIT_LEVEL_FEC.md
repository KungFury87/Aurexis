# Round 49 — Bit-level FEC (P-09 resolution)

**Date:** 2026-04-29
**Track:** T2 (Phoxelis as Medium)
**Status:** complete — measurement landed; P-09 closed; new follow-up promise opened

---

## What this round opened on

`python phoxelis_audit.py`:
- integrity OK (95 ops, 103 preds)
- 4 STALE pending promises: P-02, P-03, P-04, P-09

P-09 (bit-level FEC) became the target. R46 found that byte-level Reed-Solomon structurally fails at 8 bits/cell because byte-BER inflates ~8× over bit-BER — at the simulated camera bit-BER of 5.5%, byte-BER is ~36%, beyond any RS strength. The architectural fix is a bit-level forward-error-correcting code that operates on individual bit errors directly.

## Experiment

BCH(255, k, t) over GF(2^8) — codeword length 255 bits, parameter `t` is the number of correctable bit errors per codeword.

Sweep:
- `t ∈ {9, 12, 15, 18, 21, 24, 27, 30}` (the valid range for m=8; t<9 raises ValueError in bchlib)
- bit-BER `p ∈ {0, 0.005, 0.01, 0.02, 0.04, 0.055, 0.07, 0.10}`
- 30 trials × 80 codewords per (t, p) cell = 2400 codewords per cell

Tool: `bchlib==2.1.3` (added to the tool ladder this round).

## Results

### Plain BCH

```
   t    rate  data_B/cw   p=0.000  p=0.005  p=0.010  p=0.020  p=0.040  p=0.055  p=0.070  p=0.100
   9   0.722         23     1.000    0.406    0.155    0.022    0.001    0.000    0.000    0.000
  12   0.627         20     1.000    0.448    0.188    0.035    0.002    0.000    0.000    0.000
  15   0.533         17     1.000    0.513    0.240    0.071    0.003    0.001    0.000    0.000
  18   0.439         14     1.000    0.575    0.335    0.101    0.007    0.002    0.000    0.000
  21   0.345         11     1.000    0.636    0.417    0.173    0.027    0.007    0.002    0.000
  24   0.251          8     1.000    0.741    0.528    0.272    0.074    0.025    0.007    0.001
  27   0.157          5     1.000    0.834    0.685    0.448    0.188    0.112    0.054    0.018
  30   0.063          2     1.000    0.916    0.847    0.710    0.525    0.393    0.317    0.180
```

At the R46 camera bit-BER (p=0.055), the strongest BCH (t=30, rate 0.063) reaches **39.3% block success**. R46 byte-level RS at the same condition: **0**.

That alone discharges P-09's headline claim: **bit-level FEC produces nonzero camera-decode survival where byte-level RS produced zero.**

### BCH preceded by 3× bit repetition + majority vote

A simple inner code reduces bit-BER from 0.055 to `3p² − 2p³ ≈ 0.0087` before BCH sees it. Same parameter sweep at p=0.055:

```
  t    rate_eff  data_B/cw   block_success
  9    0.2405          23           0.2004
 12    0.2092          20           0.2404
 15    0.1778          17           0.2942
 18    0.1464          14           0.3896
 21    0.1150          11           0.4604
 24    0.0837           8           0.5617
 27    0.0523           5           0.6979
 30    0.0209           2           0.8675
```

**3rep + BCH(t=30) reaches 86.75% block success at p=0.055.**

## Headline benchmark row

| metric | round | value | corpus | status |
|---|---|---|---|---|
| Block success at simulated camera bit-BER 5.5% — bit-level FEC | R49 | 0.8675 (3rep+BCH t=30) / 0.393 (BCH t=30 alone) | 2400 trials | current — first nonzero camera-decode-survival in project history |

R46 was 0.000 at the same bit-BER. R49 is 0.8675. P-09 closed.

## What this does NOT yet show

End-to-end byte-exact recovery of a complete frame requires *every* codeword to decode. With 1024 codewords per 768×768 frame at 8-hue density and 86.75% per-block success, the per-frame success rate is ~0.8675^1024 ≈ 10^(-65). That's not the right metric: in practice you concatenate an outer code (Reed-Solomon over GF(2^16) treating each successfully-decoded BCH block as a symbol, with erasure decoding for failed blocks) so frame success becomes a much weaker condition — failed blocks just become erasures.

That outer-code concatenation is the natural Round 50 work and gets logged as **P-12 (new pending promise)**: "Outer RS-with-erasures atop bit-level FEC for end-to-end byte-exact frame recovery at the simulated camera bit-BER."

## Files added this round

- `round49_bch_fec/round49_bit_level_fec.py` — sweep harness
- `round49_bch_fec/round49_results.json` — full sweep data
- `Aurexis_Core_WORKING_20260414-1339/07_VISION_SUBSTRATE/reports/ROUND_49_BIT_LEVEL_FEC.md` — this file

## Tool ladder addition

`bchlib==2.1.3` joins the permanent-substrate tier alongside numpy/scipy/Pillow/reedsolo. It's a bit-level FEC primitive; Phoxelis is not aiming to replace it.

## Promises ledger updates

- **P-09** moves from `pending`/STALE to `completed` with C-49 evidence: this round.
- **P-12** opens: outer RS-with-erasures atop bit-level FEC for end-to-end byte-exact frame recovery.

## Audit after this round should report

- 3 STALE pending (P-02, P-03, P-04 — P-09 cleared)
- 19 completed (was 18, +C-49)
- 12 pending (was 11, +P-12)
- categorical first headline still anchored to R44–45

## Next round opens with

`python phoxelis_audit.py`. Three STALE pending. R50 picks one of:
- **P-12** (just opened): outer RS-with-erasures + integration with the encoder pipeline. End-to-end byte-exact frame recovery at p=0.055.
- **P-04** (10+ rounds STALE): phone-camera-in-the-loop test of the actual encoder. Vincent-machine task.
- **P-02** (26+ rounds STALE): L2 identity layer wiring.
