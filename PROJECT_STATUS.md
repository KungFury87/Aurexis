# Aurexis Core — unified project status (`core v1 incomplete`)

**As-of:** 2026-04-25
**Repo:** https://github.com/KungFury87/Aurexis
**Working tree:** `Aurexis_Core_WORKING_20260414-1339/`

This is the **top-level** project status. The V1-specific status
lives at `00_PROJECT_CORE/PROJECT_STATUS.md` and is preserved
unchanged.

---

## Status banner

- ACOR-1.1 is the **current official public release** of the V1
  Substrate Candidate. Frozen. Tag:
  `core-v1-substrate-candidate-or1.1`.
- The wider project is in **Core v1 incomplete** state. The V1
  substrate is one piece of the eventual full Core; it is the only
  piece audited and released so far.
- V2 research lane continues. V2 charter is locked; V2 decode-engine
  work is active on branch `working/core-v2`.
- Engine-semantics proof system (current research lane) is at v0.6
  framing, in `06_PROOF_SYSTEM/aurexis_research_sim/`.

## Today's per-primitive evidence (from
`06_PROOF_SYSTEM/aurexis_research_sim/reports/PROOF_INDEX.md`)

| family | boundary_tag | validation | confidence_state | semantic_stability |
|---|---|---|---|---|
| cardinality  | PRIMITIVE_AWARE_HELPS        | -           | HOLD              | SEMANTIC_STABLE     |
| repetition   | PRIMITIVE_AWARE_HELPS        | WEAK_ROBUST | HOLD              | SEMANTIC_UNSTABLE   |
| role_zone    | PRIMITIVE_AWARE_HELPS        | WEAK_ROBUST | HOLD              | -                   |
| ordering     | PRIMITIVE_AWARE_HELPS        | SUSPECT     | **REJECT**        | -                   |
| symmetry     | PRIMITIVE_AWARE_HELPS        | -           | HOLD              | -                   |
| adjacency    | METRIC_GAP_ROI_INSENSITIVE   | -           | NEED_MORE_EVIDENCE | -                  |
| orientation  | METRIC_GAP_ROI_INSENSITIVE   | -           | NEED_MORE_EVIDENCE | -                  |
| hierarchy    | METRIC_GAP_ROI_INSENSITIVE   | -           | NEED_MORE_EVIDENCE | -                  |

Headline calibrated finding (Engine-semantics): **ordering as a
promoted primitive is currently REJECT.** The arbitration win is
local; the broader stress test failed. This is exactly the kind of
multi-evidence calibration the proof system was reframed to surface.

## Branch and tag state (read-only summary)

- `main` — release-aligned head; ACOR-1.1 README. UNCHANGED.
- `master` — legacy mirror. UNCHANGED.
- `working/core-v2` — V2 active. Has uncommitted V2 decode-engine
  WIP from a prior session, intentionally preserved.
- `working/core-v1-incomplete` — to be created by user via
  `GITHUB_PUSH_PLAN.md`. Holds the unified Core working body.
- 26 `backup/v1-substrate-candidate-*` branches — frozen.
- 33 tags including `core-v1-substrate-candidate-or1`,
  `core-v1-substrate-candidate-or1.1`, `core-v2-decode-engine-d3`,
  26 `backup-v1-substrate-candidate-*`, 4 `v1-substrate-20260413-*`
  — all UNCHANGED.

## What remains for the next Core gate

See `ROADMAP.md`. Short version:
- Real-evidence anchoring (move from STUB to PARTIAL).
- Unblock 3 remaining METRIC_GAP_ROI_INSENSITIVE families.
- Promote strip-based repetition fix in place to `binding.py`.
- Continue V2 decode-engine work on `working/core-v2`.
- Define the next Core official release gate.

## How to verify locally

```
cd Aurexis_Core_WORKING_20260414-1339/
# V1 substrate candidate test surface (frozen):
cd 05_ACTIVE_DEV/aurexis_lang
PYTHONPATH=src python3 run_pytest_surface.py
# Expected: TOTAL: 327 passed, 0 failed (V1 substrate candidate).

# Engine-semantics proof system (current research):
cd ../../../06_PROOF_SYSTEM/aurexis_research_sim
python3 -m pytest tests -q
# Expected: 221 passed.

python3 -m aurexis_sim.proof_index
# Prints v0.6 master Engine-semantics index.
```

## What this status is NOT

- Not a new release announcement. ACOR-1.1 is the current release.
- Not a claim that Core is complete. The header literally says
  "core v1 incomplete."
- Not E/D / Client / Runtime status. That lives outside this repo.
