# Round 50 — Concatenated FEC: outer RS atop bit-level BCH (P-12 closure)

**Date:** 2026-04-29
**Track:** T2 (Phoxelis as Medium)
**Status:** complete — first nonzero whole-frame byte-exact recovery in project history

---

## What this round opened on

`python phoxelis_audit.py`:
- integrity OK (95 ops, 103 preds)
- 3 STALE pending: P-02, P-03, P-04
- P-12 newly opened R49: outer RS-with-erasures atop bit-level FEC

P-12 is the natural follow-up to R49. R49 closed P-09 by showing bit-level BCH gives nonzero per-block survival at p_bit=0.055 (3rep+BCH t=21: 46% block success; t=30: 87%). But whole-frame recovery still required *every* block to decode: 1024 blocks × 0.87 per-block = 10⁻⁶⁵ frame success. Useless.

The architectural fix is concatenation: outer Reed-Solomon over the BCH-decoded blocks treats each successful block as a symbol and each failed block as a known erasure. RS(N, K) over GF(2⁸) corrects up to N-K erasures. Frame succeeds iff failed blocks ≤ N-K.

## Experiment

Monte-Carlo simulation: 5,000 trials per (inner_t, K) cell, sampling per-block success from R49's measured rates.

- Outer code: RS(N=255, K) over GF(2⁸) — N=255 matches GF(2⁸) natural codelength
- K swept 20 → 250 in steps of 10
- Inner: 3rep+BCH(t∈{21,24,27,30}), per-block success rates 0.460 / 0.562 / 0.698 / 0.868 from R49 measurements at simulated camera bit-BER 5.5%
- Frame succeeds iff erasure count ≤ N-K

## Results — best operating point per inner

| inner t | inner db | inner p_block | RS(N,K) | frame success | net data bytes | overall rate |
|---|---|---|---|---|---|---|
| 21 | 11 |  0.460 | 255, 90  | 0.9996 | **990** | 0.122 |
| 24 |  8 |  0.562 | 255, 120 | 0.9982 |  960   | 0.118 |
| 27 |  5 |  0.698 | 255, 160 | 0.9950 |  800   | 0.098 |
| 30 |  2 |  0.868 | 255, 200 | 1.0000 |  400   | 0.049 |

The headline pick is **inner t=21, RS(255, 90)** — 990 bytes byte-exact per 255-block frame at 99.96% frame reliability. Higher inner-t configs sacrifice net rate without much frame-reliability gain, since the outer code is already absorbing the erasure variance.

## Headline benchmark row

| metric | round | value | corpus | status |
|---|---|---|---|---|
| Whole-frame byte-exact recovery at simulated camera bit-BER 5.5% | R50 | **990 bytes/frame at 99.96% frame success** (3rep+BCH(t=21) + RS(255,90)) | 5,000 Monte-Carlo trials | current — *first nonzero whole-frame recovery in project history* |

Comparison ladder (camera-decode capacity, simulated):

| system | bytes camera-decoded | reliability | source |
|---|---|---|---|
| R46 byte-level RS at p_bit=5.5% | 0 | n/a | structurally fails |
| R49 3rep+BCH(t=30) per-block | 2 (per codeword) | 0.868 block | P-09 closure |
| **R50 concatenated 3rep+BCH(t=21) + RS(255,90)** | **990 (per frame)** | **0.9996 frame** | **this round** |
| QR Version 12 (real, not sim) | 1,666 | n/a | published spec |
| Aurexis E/D V2.1 (live-camera proven 2026-04-17) | 3,568 | n/a | prior work |

We are now within a factor of 1.7 of QR Version 12 on simulated camera capacity, and the gap closes further with predicate-side bit-BER reduction (any predicate-stack improvement that drops p_bit from 0.055 to e.g. 0.030 cascades through the whole pipeline).

## What this measurement does and does not claim

**Claims:**
- The architecture (outer RS-with-erasures + inner bit-level BCH + inner repetition) gives nonzero whole-frame byte-exact recovery at the R46 simulated camera bit-BER.
- The headline number (990 bytes / 99.96%) is reproducible from `round50_concatenated_fec.py` with seed 20260430.
- The result is consistent with the architectural prediction in R46/R49.

**Does NOT claim:**
- That this beats QR on real-camera capacity (QR Version 12 = 1,666 bytes verified through actual cameras; we have a *simulated* camera channel only).
- That the channel model is realistic. We assumed independent bit errors at p=0.055. Real camera errors are bursty (glare regions, motion blur, focus falloff). Bursty errors hurt RS less than independent errors of the same total rate (RS handles bursts well) but help BCH less. Net effect unclear without a real measurement.
- That this is the optimal concatenation. LDPC + RS or convolutional + RS would likely do better. BCH+RS is just the simplest reasonable choice that works.

The next architectural milestone is real-camera transit (P-04, currently STALE >12 rounds), which is a Vincent-machine task (print + photograph + decode).

## Files added this round

- `round50_outer_rs/round50_concatenated_fec.py` — Monte-Carlo sweep
- `round50_outer_rs/round50_results.json` — full sweep data
- `Aurexis_Core_WORKING_20260414-1339/07_VISION_SUBSTRATE/reports/ROUND_50_CONCATENATED_FEC.md` — this file

## Promises ledger updates

- **P-12** moves from `pending` to `completed` with C-50 evidence: this round.

## Audit after this round should report

- 3 STALE pending (unchanged: P-02, P-03, P-04)
- 21 completed (was 20, +C-50)
- 11 pending (was 11, +0 net — none opened, P-12 closed but P-12 wasn't STALE)
- categorical first headline still anchored to R44–45

## Next round opens with

`python phoxelis_audit.py`. Three STALE pending. R51 picks one of:
- **P-04** (12+ rounds STALE, T2 track): phone-camera-in-the-loop test of the actual encoder. Vincent-machine task; prints the R50 frame, photographs, decodes through the same pipeline. Closes the simulation→reality gap.
- **P-05** (T6 track): Phoxelis as MCP tool. Wraps the runtime so an LLM can call it during conversation. Pure plumbing; sandbox-doable.
- **P-02** (28+ rounds STALE, L2 track): wire external CV models as L2 identity layer. Sandbox-doable but biggest scope.

The single needle-mover for the categorical-first claim is now P-04 (real camera). Everything else is interior.
