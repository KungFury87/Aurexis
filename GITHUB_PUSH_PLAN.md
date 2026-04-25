# GitHub push plan — `core v1 incomplete` unified Core tree

This is the precise sequence of commands Vincent runs on his PC,
inside `Aurexis_Core_WORKING_20260414-1339\`, to publish the
unified Core working tree to
`https://github.com/KungFury87/Aurexis.git` **without** touching
any frozen V1 release ref or any backup branch.

This pass DID NOT push automatically. Pushing is Vincent's step,
to be run only after he reviews this plan and the unification
report.

---

## Pre-flight: snapshot the frozen state (do this first)

```powershell
cd C:\Users\vince\Desktop\Aurexis evolved\Aurexis_Core_WORKING_20260414-1339

# Confirm we have all 33 tags locally and on origin.
git fetch --tags
git tag | Sort-Object | Out-File ..\GROK_TAG_SNAPSHOT_BEFORE.txt
git branch -a | Out-File ..\GROK_BRANCH_SNAPSHOT_BEFORE.txt
```

Save these two files. Grok will diff them against the post-push
state to confirm nothing frozen was mutated.

---

## Step 1: deal with pre-existing V2 working-tree changes

`git status` will show:

- M  05_ACTIVE_DEV/aurexis_lang/src/aurexis_lang/v2_decode/*.js
- ??  several untracked files

These were left from a prior V2 session. Decide ONE of:

  **Option A — preserve V2 WIP on `working/core-v2`:**

      git checkout working/core-v2
      git add 05_ACTIVE_DEV/aurexis_lang/src/aurexis_lang/v2_decode/
      git add FROZEN_V1_BACKUP_NOTICE.md WORKING_COPY_NOTICE.md _acor11_body.txt
      git commit -m "V2 decode-engine WIP snapshot pre-unification"
      git push origin working/core-v2

  **Option B — leave V2 WIP uncommitted and carry it into the new
  branch as working-tree changes** (the new commit on
  `working/core-v1-incomplete` will include V2 WIP if you choose
  to stage it there). Skip this step and continue.

Either is non-destructive. The recommendation is Option A so that
V2 WIP has a clean save point before the unification commit.

---

## Step 2: create the unified working branch

```powershell
# Start from the same HEAD that has the unification files written
# to the working tree (this Cowork pass already wrote them).
git checkout -b working/core-v1-incomplete
```

This creates `working/core-v1-incomplete` from current HEAD. No
existing branch is moved. No tag is touched.

---

## Step 3: stage and commit the unification files

```powershell
git add README.md
git add ROADMAP.md PROJECT_STATUS.md
git add CORE_UNIFICATION_REPORT.md CORE_TREE_MAP.md
git add GROK_AUDIT_LANE.md GITHUB_PUSH_PLAN.md
git add 06_PROOF_SYSTEM/

git status --short    # review before committing
git commit -m "Core unification: v0.6 proof system + unified docs"
```

Optional cleanup — the v0.6 simulator was rsync'd in with a few
top-level CWD-output dossier copies that mirror `reports/`. They
are harmless but cluttered. To remove them:

```powershell
$litter = @(
  "ATLAS.md","BINDING.md","BOUNDARY.md","CONFIDENCE.md","COVERAGE.md",
  "FUSION.md","INFERRED_BINDING.md","INTERACTION.md","PRIMITIVE_AWARE.md",
  "PROOF_INDEX.md","REDESIGN.md","SEMANTIC_STABILITY.md","SOFT_BINDING.md",
  "UNLOCK.md","VALIDATION.md","atlas.json","binding.json","boundary.json",
  "confidence.json","coverage.json","fusion.json","inferred_binding.json",
  "interaction.json","primitive_aware.json","proof_index.json",
  "redesign.json","semantic_stability.json","soft_binding.json",
  "unlock.json","validation.json","stress_report.csv","stress_report.json"
)
foreach ($f in $litter) {
  Remove-Item "06_PROOF_SYSTEM\aurexis_research_sim\$f" -ErrorAction SilentlyContinue
}
git add -A 06_PROOF_SYSTEM/
git commit -m "06_PROOF_SYSTEM: drop top-level CWD-output litter (reports/ canonical)"
```

---

## Step 4: push the new branch (does NOT touch main)

```powershell
git push -u origin working/core-v1-incomplete
```

After this, GitHub will show the new branch in the dropdown next
to `main`, `master`, `working/core-v2`, and the 26 backup
branches. **No existing branch or tag is modified.**

---

## Step 5 (OPTIONAL — only after Grok audit passes)

If you decide the unified tree should also be the default branch
view, you can fast-forward `main` to point at the
`working/core-v1-incomplete` head — but only if `main` is an
ancestor of the new branch (no force push, no history rewrite).

```powershell
# Verify main is an ancestor (will print nothing if it is, message if not):
git merge-base --is-ancestor origin/main working/core-v1-incomplete

# If the above exits 0, fast-forward main:
git checkout main
git merge --ff-only working/core-v1-incomplete
git push origin main
```

If `git merge --ff-only` refuses, **do not force**. Open an issue,
talk to Grok, and resolve manually. The default-branch view stays
on the existing ACOR-1.1 README until you intentionally update it.

---

## Step 6: post-flight verification

```powershell
git fetch --tags
git tag | Sort-Object | Out-File ..\GROK_TAG_SNAPSHOT_AFTER.txt
git branch -a | Out-File ..\GROK_BRANCH_SNAPSHOT_AFTER.txt

# Diff before vs after. Tags must be identical.
fc ..\GROK_TAG_SNAPSHOT_BEFORE.txt ..\GROK_TAG_SNAPSHOT_AFTER.txt

# Branches must differ ONLY by the addition of working/core-v1-incomplete.
fc ..\GROK_BRANCH_SNAPSHOT_BEFORE.txt ..\GROK_BRANCH_SNAPSHOT_AFTER.txt
```

If `fc` reports any tag difference, STOP. A frozen V1 ref was
moved. Recover from the local clone or from `back again/` (the
sibling frozen backup folder).

---

## Forbidden in this push (read-only enforcement)

- `git tag -d ...`
- `git push origin :refs/tags/...`
- `git push --force` or `git push -f` against any branch.
- `git branch -D backup/v1-substrate-candidate-...`
- `git branch -D` of any branch listed in `CORE_UNIFICATION_REPORT.md`
  as frozen.
- `git push origin :backup/...`

If any of those are needed, the pass design is wrong. Stop and
talk to Grok / re-read `CORE_UNIFICATION_REPORT.md` first.

---

## What this push achieves

- Unified Core working tree visible at the new branch.
- `06_PROOF_SYSTEM/aurexis_research_sim/` published as part of the
  Core repo.
- New top-level docs visible.
- Frozen V1 release surface UNCHANGED.
- 26 backup branches UNCHANGED.
- 33 tags UNCHANGED.
- V2 work UNCHANGED.
- ACOR-1.1 (`core-v1-substrate-candidate-or1.1`) still the
  **current official release**.
- Repo front-page does NOT change unless you opt in via the
  optional Step 5.

That is "combine, don't delete."
