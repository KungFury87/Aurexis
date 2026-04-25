# ðŸ”’ Aurexis Core V1 â€” FROZEN BACKUP (do not modify)

**Folder:** `C:\Users\vince\Desktop\Aurexis evolved\back again`
**Frozen at:** 04/14/2026 13:35:33
**State:** This folder is the safe backup of the full Core V1 state, as of Aurexis Core Official Release 1.1 (ACOR-1.1).

## Do not modify anything in this folder

All new work happens in the working copy:

    C:\Users\vince\Desktop\Aurexis evolved\Aurexis_Core_WORKING_20260414-1335

## What this folder contains

The complete Core V1 state, including:

- Full `05_ACTIVE_DEV/aurexis_lang/` source tree (154 modules)
- `.git/` repository state with all branches, tags (including `core-v1-substrate-candidate-or1` and `core-v1-substrate-candidate-or1.1`), and commit history
- `00_PROJECT_CORE/` truth-surface (ROADMAP, PROJECT_STATUS, manifests, audit docs, release notes, locked release zip)
- `01_RELEASES/` â€” older V84/V85/V86 release zips
- `02_GATE_TRACKING/` â€” gate status docs
- `03_HANDOFFS_AND_CONTEXT/` â€” handoff logs and historical AI session exports
- `BACKUPS/` â€” older backup zips
- All session-helper scripts and logs from the ACOR-1 / ACOR-1.1 release passes

## How to restore from this backup

If the working copy becomes corrupt, delete it and run:

    robocopy "C:\Users\vince\Desktop\Aurexis evolved\back again" "C:\Users\vince\Desktop\Aurexis evolved\Aurexis_Core_WORKING_20260414-1335" /MIR /COPYALL

## Sibling working copy

Live work continues here:

    C:\Users\vince\Desktop\Aurexis evolved\Aurexis_Core_WORKING_20260414-1335

---

This notice was created automatically when the working copy was spun off. Delete this file only if you intentionally want this folder to resume as an editable working tree.
