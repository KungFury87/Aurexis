# Round 47 — Phoxelis Project Scaffolding

**Date:** 2026-04-28
**Track:** project infrastructure (anti-drift)
**Status:** complete

---

## What this round produced

After R46 the project had two failure modes that kept showing up: (1) claims drifting between rounds with no anchor to verify them against, and (2) promises ("Round N+1 will do X") that quietly aged out. This round builds the infrastructure to make both visible.

Five files at the repo root:

- `PHOXELIS_CHARTER.md` — load-bearing definition. Dual-fiber typed predicate calculus, the four architectural layers (L1 sensory invariants, L2 recognition by feature, L3 world knowledge, L4 compositional inference), the six tracks (T1 vocabulary health, T2 medium, T3 multi-modal, T4 tool ladder, T5 hardware substrate, T6 MCP tool), and seven hard anti-drift contracts. The single sentence: *Phoxelis is the substrate that makes "meaning carried by composable measurements" empirically testable, in both directions of the calculus, with the vocabulary auditing itself.*
- `PHOXELIS_BENCHMARKS.md` — every empirical measurement made on the project, with provenance (round, corpus, transit condition) and freshness status (current / superseded / stale / abandoned). Includes vocabulary health, capture stability, .phox format, encoding capacity (PNG-clean and camera-noise), the filter-survival table (11/12 named Instagram filters preserve byte-exact recovery), and comparison vs prior art (QR Versions 12/25/32/40, Aurexis E/D V2.1, libcimbar, JAB Code).
- `PHOXELIS_PROMISES.md` — every "Round N+1 will do X" tracked as a row with status. Eleven pending (P-01 through P-11), sixteen completed (C-30 through C-46), three abandoned (X-25 polarization-pair predicate, X-30-camera frame-quality-gate-on-real-photos, X-37c-claim QR comparison walk-back).
- `PHOXELIS_TOOL_LADDER.md` — external tools as scaffolding with replacement plans. Three currently active scaffolding entries (manual photo capture, manual predicate authoring, LLM-in-dialogue) — all sitting at step 1 with no progression, which is exactly the drift P-10 and P-11 are meant to address.
- `phoxelis_audit.py` — script that walks the four files plus `reports/ROUND_*.md` and produces a textual report and a regenerable `PHOXELIS_DASHBOARD.html`.

## First audit run

```
PHOXELIS AUDIT  -  2026-04-28T23:18:03Z
==============================================================================

  vocabulary:  103 predicates, 95 operators
  rounds:      11 round docs found, last = R42
  promises:    11 pending, 16 completed, 3 abandoned, 3 STALE (>5 rounds)
  tools:       3 active scaffolding, 0 stagnant
  flags:       0 FATAL, 3 WARN, 8 INFO

  WARN:
    PROMISE P-02 pending since R21C design doc (>21 rounds): Wire L2 identity layer with external CV models
    PROMISE P-03 pending since R28 plumbing (>14 rounds): Stage capture-stability benchmark on three scenes
    PROMISE P-04 pending since R37 (>5 rounds): Phone-camera-in-the-loop test of Phoxelis encoding
```

The three STALE promises are exactly the things the project has been carrying without progress for too long. P-02 (L2 identity layer) has been pending since the R21C design doc — twenty-one rounds without a build. P-03 (capture stability benchmark) has plumbing from R28 but no scenes staged. P-04 (phone-camera-in-the-loop) was supposed to land in R37 and didn't.

The eight INFO flags are missing per-round markdown files for R29, R34, R36–41 — work happened in standalone script directories rather than getting a `ROUND_N_*.md` companion. That's a documentation gap noted but not retroactively fixed.

## What this changes

The next round opens with `python phoxelis_audit.py`. Three STALE promises means the next round picks one and either resumes it, abandons it with a documented reason, or supersedes it. The audit is not advisory — it gates the round.

The categorical first headline (Round 44–45: 11/12 Instagram filters preserve byte-exact recovery) sits at the top of the dashboard so it doesn't drift back into capacity-claim territory. The honest-position note in BENCHMARKS.md (Phoxelis is *not* currently competitive on camera-decode capacity vs QR; it *is* categorically first on filter-survival) is a permanent reminder.

## Anti-drift contracts now load-bearing

Six of the seven hard contracts are mechanically checkable from this point:

1. **Every round produces a measurement** — audit script flags rounds with no numeric content.
2. **Capacity claims state transit conditions** — BENCHMARKS schema requires a transit column.
3. **Architectural firsts and capacity firsts don't blur** — separate sections in BENCHMARKS, separate cards on the dashboard.
4. **Promised future rounds are tracked** — PROMISES schema, audit reports stale.
5. **External tools used are named** — TOOL_LADDER schema, audit reports stagnant.
6. **Failed predicates are retired with documented reason** — abandoned table in PROMISES.
7. (the categorical-first headline rule) — dashboard shows the headline, not capacity rank.

## Files added

- `PHOXELIS_CHARTER.md` (8.5KB)
- `PHOXELIS_BENCHMARKS.md` (8.1KB)
- `PHOXELIS_PROMISES.md` (5.7KB)
- `PHOXELIS_TOOL_LADDER.md` (3.8KB)
- `phoxelis_audit.py` (~13KB)
- `PHOXELIS_DASHBOARD.html` (auto-generated, ~5KB)
- `Aurexis_Core_WORKING_20260414-1339/07_VISION_SUBSTRATE/reports/ROUND_47_PROJECT_SCAFFOLDING.md` (this file)

## What does NOT happen this round

No predicate work. No encoding measurements. No phone-camera tests. The round is pure infrastructure. The next round picks one of P-01 / P-08 / P-10 / P-11 (the four pending promises that move the project forward most: IR at scale, real Instagram round-trip, LLM-as-author at scale, web-corpus integration) and produces a measurement against it.

## Pointer

The single sentence: *Phoxelis is the substrate that makes "meaning carried by composable measurements" empirically testable, in both directions of the calculus, with the vocabulary auditing itself.*

If a future round doesn't make that more true, the audit will say so.
