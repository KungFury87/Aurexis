# Aurexis Core V2 Charter

**Codename:** Aurexis Core V2 — Real-World Calibration Candidate
**Charter locked:** 2026-04-14
**Working folder:** `Aurexis_Core_WORKING_20260414-1339`
**V2 git branch:** `working/core-v2`
**Predecessor:** Aurexis Core Official Release 1.1 (ACOR-1.1), tag `core-v1-substrate-candidate-or1.1`

---

## Purpose (exact)

V2 takes the V1 substrate — a clean-room-verified 51-bridge, 6,358-assertion, 327/327-green Core — and puts it through a solo-feasible, screen-based, real-world calibration loop. V2 proves Aurexis Core can ingest controlled real camera evidence, measure its own failure modes against a frozen benchmark, calibrate from the observed evidence, and demonstrate measurable before/after improvement on the same setup.

V2 is not a new Core. V2 is the first honest real-world calibration of the V1 Core against real optical evidence, packaged for review.

## Posture (exact)

V2 is:
- **screen-based only** — the evidence source is a single screen displaying the benchmark artifact set
- **one-phone-first** — one camera, one device, one operator, one rig
- **static-first** — no motion, no video pipelines, no live tracking dependencies
- **controlled repeatable capture protocol** — frozen steps, frozen distances, frozen lighting, reproducible on demand
- **benchmark artifact set** — a frozen, versioned set of on-screen artifacts the capture protocol targets
- **real evidence ingestion and delta analysis** — V1's evidence/delta bridges run against actual captured frames
- **evidence-driven calibration** — calibration passes derive their parameters from observed failures, not from assumed values
- **before/after measured improvement** — the same setup is re-run after calibration and the delta is reported honestly
- **clean V2 candidate packaging later** — after the loop closes, V2 gets a locked candidate release zip and provenance audit pass

V2 is not:
- **not print-based** — no printed fixtures, no paper targets, no physical calibration boards as a V2 dependency
- **not multi-person / team-dependent** — Vincent can run the entire loop solo
- **not multi-phone as a requirement** — additional devices are optional later, never required for V2 completion
- **not exotic optics** — consumer phone camera only, no macro rigs, no lab optics
- **not a broad new theory branch** — V2 does not spawn new Core branches; it exercises what V1 already substrates
- **not E/D work** — the E/D track belongs to GPT; V2 does not touch it
- **not full Core completion** — V2 is a calibration candidate, not the final Core

## V1 / V2 backup and release isolation (hard rule)

V1 is frozen. V2 must never override, delete, retag, or reuse any V1 branch, tag, release, or backup surface. All V2 refs — local, remote, and backup — use V2-only namespaces.

**Allowed V2 ref patterns:**
- working branch: `working/core-v2`
- backup branch: `backup/v2-...`
- backup tag: `backup-v2-...`
- release tag (future): `core-v2-...` only

**Forbidden (absolute):**
- reusing or mutating any `backup/v1-...` branch
- reusing or mutating any `backup-v1-...` tag
- changing the tag `core-v1-substrate-candidate-or1`
- changing the tag `core-v1-substrate-candidate-or1.1`
- pushing V2 state onto any V1 release surface (branch, tag, or GitHub release)
- force-pushing to, deleting, or retagging any V1 ref
- renaming V1 refs

This rule is immutable for the duration of V2. A charter amendment cannot override it; V1 surfaces are frozen.

## Relationship to V1

V1 is frozen. V2 reads from V1, runs against V1, and reports measurements about V1. V2 does not rewrite V1. V2 may:
- exercise V1 bridges against real evidence
- activate pre-V1 Core-language modules already present on disk (camera bridge, capture session manifest, capture tolerance, calibration recommendation, evidence delta analysis, evidence tiers, real capture ingest profile, hardware calibration, phoxel schema, gate 3/4/5 runners, live camera feed, CV extractors) when they directly serve the locked V2 loop
- add new V2-scoped modules, docs, fixtures, and protocols in this working tree
- add new V2-scoped gate runners and benchmarks

V2 may not:
- modify the frozen V1 backup folder at `C:\Users\vince\Desktop\Aurexis evolved\back again`
- rewrite V1 substrate modules or invalidate V1 gate proofs
- introduce protected / copyrighted / licensed code in a form that would obligate licensing
- push to GitHub without Vincent's explicit instruction

## Legal / provenance posture

V2 inherits V1's clean-room provenance audit standard. No copyrighted, proprietary, or licensed code enters V2 in a form that requires paid licenses or unsupplyable attribution. If protected code is ever detected, it is rewritten to clean-room or dropped. V2 is not actively hunting for protected code, but the standard is maintained.

## Charter Amendments

- **Amendment 1 (2026-04-18):** Decode engine track added. V2 builds a standalone, DOM-free decode engine module (`v2_decode/`) extracting Core-level decode logic from the E/D client. E/D client files remain untouched. See `V2_CHARTER_AMENDMENTS.md` for full details.

## Execution constraints

- Solo-feasible end to end
- Honest reporting of limitations at every milestone
- No scope broadening beyond this charter without explicit Vincent approval
- Planning-only passes stay planning-only; implementation passes stay scoped
- Before/after claims must be backed by real captured evidence, not simulated data
