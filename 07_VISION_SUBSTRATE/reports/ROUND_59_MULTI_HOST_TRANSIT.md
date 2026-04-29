# Round 59 — multi-host autonomous transit characterization (P-08 partial)

**Date:** 2026-04-29
**Track:** T2 (Phoxelis as Medium) + tool ladder
**Status:** complete — characterized the auth-gate landscape; honest finding that the autonomy pipeline narrows to one host/CDN pair

---

## What this round opened on

P-08 (real Instagram round-trip test) opened R45, partially advanced R51 (litterbox + weserv autonomous transit), but the literal target — Instagram — has remained blocked. R59 set out to extend R51's autonomy pattern to a *named social platform*. The honest probe of the landscape:

| platform | anonymous upload? |
|---|---|
| Imgur | requires Client-ID (registered app) |
| Reddit | requires account |
| Discord | requires account / webhook |
| Twitter / X | requires account |
| Facebook | requires account |
| Mastodon (any instance) | requires account |
| TikTok | requires account |
| Instagram | requires account |
| Telegraph (telegra.ph) | returns "Unknown error" to automated POSTs (anti-bot) |
| postimages.org | returns 403 "Automated uploads are not allowed" |

**Every named social platform is sandbox-blocked.**

Reachable from sandbox without auth (verified live this round): `litterbox.catbox.moe`, `qu.ax`, `gofile.io`, `filebin.net`. None of these are social platforms; they're anonymous file-share CDNs.

## What this round actually measured

Instead of spinning on auth-gated paths, R59 characterized **how broadly the R51 autonomy pattern generalises across the reachable anonymous-CDN landscape**. The pipeline:

```
encode_bytes(32-byte payload, 16x16 grid, 512px)
 -> upload to {litterbox, qu.ax, filebin}
 -> for each host's URL:
       pipe through images.weserv.nl with platform-mimicking JPEG presets
       (instagram-q85, twitter-q75, reddit-q80, discord-q90 + identity-png)
       decode each download through Phoxelis runtime
 -> report (host x transform) byte-exact matrix
```

## Results

```
        host    identity-png  instagram-q85  twitter-q75  reddit-q80  discord-q90
   litterbox              OK             OK           OK          OK           OK
       qu.ax            FAIL           FAIL         FAIL        FAIL         FAIL
     filebin            FAIL           FAIL         FAIL        FAIL         FAIL

5 / 15 (host x transform) cells preserved byte-exact recovery.
```

The qu.ax and filebin failures are **not** Phoxelis decode failures — they're **HTTP 404 from images.weserv.nl** when it tries to fetch from those hosts. qu.ax serves a downloadable file at `https://qu.ax/yyr7w` (no extension); weserv refuses to recognise it as an image. filebin requires a browser-flow auth cookie before serving the actual bytes; weserv doesn't follow that flow.

## Honest finding

**The autonomous transit pipeline is single-host fragile.** R51 demonstrated litterbox + weserv works. R59 demonstrates **only** litterbox + weserv works among the public hosts I can reach. Specific named social platforms remain auth-gated and structurally unreachable from sandbox.

Practical implication for P-08: **the literal closure (Instagram round-trip) requires a Vincent-side step**. Two reasonable paths:

1. Vincent provides a logged-in browser session via Chrome MCP, and I drive uploads through that session.
2. Vincent uploads the test PNG to Instagram manually, screenshots the rendered post, and I decode the screenshot.

Neither is the literal "Phoxelis closes P-08 autonomously" outcome. Both are achievable in a single Vincent-collaborative round.

## Headline benchmark row

| metric | round | value | status |
|---|---|---|---|
| Multi-host autonomous transit | R59 | 5/5 transforms work via litterbox + weserv (matches R51); 0/5 transforms work via qu.ax or filebin (weserv anti-hotlink); 0 named social platforms reachable without auth | current — autonomy pipeline characterised, narrows to one host/CDN pair |

## Promises ledger updates

- **P-08** (real Instagram round-trip): stays `pending` and STALE (>13 rounds). Status note added: structurally requires Vincent-side auth or Chrome-MCP browser session; not single-bash-call closable.
- **P-16** opens: harden the autonomy pipeline — find a *second* working (anonymous-host × transform-CDN) pair so a single host outage doesn't eliminate the autonomy harness.
- **P-17** opens: Chrome-MCP-driven literal-platform round-trip — when Vincent's browser is connected with auth, drive an actual Instagram/Reddit/Mastodon upload + screenshot + decode.

## Files added this round

- `round59_multi_host_transit/round59_multi_host_transit.py` — multi-host upload + transit + decode harness
- `round59_multi_host_transit/round59_results.json` — full (host × transform) cell data
- `round59_multi_host_transit/source.png` — encoded source
- this report

## Tool ladder updates

`gofile.io`, `qu.ax`, `filebin.net` join the **probed-but-not-load-bearing** tier: known reachable from sandbox, but not currently part of any working transit chain. Either of them could become load-bearing if a different transform CDN (not weserv) accepted them as input.

## Why this is the right close

The autonomy reframe (R50→R58) closed eight stale promises in eight rounds by always picking the sandbox-reachable thing. R59 honest-faces the limit of that pattern: **specific named social platforms are not reachable from sandbox, period**. Continuing to spin on auth-gated paths would be the same drift the audit was designed to catch in the other direction. R59 produces a measurement (the 5/15 matrix) and a documented finding (the auth gate) and surfaces the next-step requirements (Vincent's auth or Chrome MCP).

## Next round opens with

`python phoxelis_audit.py`. STALE count after R59 should still be 6 (P-08 stays stale, but that's the right answer; P-16 and P-17 just opened so neither is stale yet).

R60 candidates:
- **R60 — corpus growth + retry P-10 / R56 collisions**: run R55 harness 5+ times inline, grow N from 20 to ~70, re-audit R54's predicate and R56's 3 colliding L4s. The actual P-10 close at scale.
- **R60 — sensor layer in DSL (R61 in roadmap)**: promote R58 from Python module to first-class typed substrate.
- **R60 — P-16 (autonomy hardening)**: find a second working host/CDN pair. Lower leverage than the others.
