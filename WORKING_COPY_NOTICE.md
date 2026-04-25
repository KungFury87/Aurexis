# Aurexis Core -- WORKING COPY (live)

**Folder:** `C:\Users\vince\Desktop\Aurexis evolved\Aurexis_Core_WORKING_20260414-1339`
**Spun off at:** 04/14/2026 13:42:55
**Source snapshot (frozen):** `C:\Users\vince\Desktop\Aurexis evolved\back again`

## This is the live working tree

All new Core development happens here. The frozen backup at `C:\Users\vince\Desktop\Aurexis evolved\back again` must not be modified.

## What this folder contains

An exact mirror of the Core V1 state at spin-off time -- same 154 source modules in `05_ACTIVE_DEV/aurexis_lang/src/aurexis_lang/`, same `.git/` state, same truth-surface, same release zip. Use it as the starting point for the next phase of Core work.

## Relationship to GitHub

`.git/` in this folder has the same remote (`https://github.com/KungFury87/Aurexis`) as the frozen backup. Pushes from here go to the same remote.

**Recommended next steps:**

1. Decide whether pushes from the working copy should target a new branch or `main`.
2. If you want the working copy to diverge on its own branch, create one:

        git checkout -b working/<name>

3. The frozen backup still has the release branches and tags; leave those alone.

## Relationship to the locked release zip

`00_PROJECT_CORE/aurexis_core_v1_substrate_candidate_locked.zip` in this folder is a copy of the ACOR-1.1 zip. Rebuilding it here overwrites only this folder's copy -- the original is preserved in the frozen backup.

## How to restart from the backup

    robocopy "C:\Users\vince\Desktop\Aurexis evolved\back again" "C:\Users\vince\Desktop\Aurexis evolved\Aurexis_Core_WORKING_20260414-1339" /E /COPY:DAT
