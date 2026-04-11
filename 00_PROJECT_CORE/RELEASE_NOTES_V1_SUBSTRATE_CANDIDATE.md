# AUREXIS CORE — RELEASE NOTES

## Release: aurexis-core-v1-substrate-candidate

**Date:** April 9, 2026
**Type:** Locked baseline — candidate package

---

## What Was Accepted

A narrow V1 law-bearing substrate candidate for Aurexis Core, containing a frozen visual grammar (3 primitives, 3 operations), deterministic semantics layer (10 subsystems at V1.0), and a top-level substrate integration path. Accepted by ChatGPT (planner/auditor) as "real, coherent, and substantive."

## What Wording Was Corrected

During the acceptance pass, the following overstated claims were corrected:

- "Full visual computing substrate" → "Narrow V1 law-bearing substrate candidate"
- "100% complete" → "V1 substrate ladder complete — not full Aurexis Core"
- "No subsystem is heuristic" → "Law-governed semantics are deterministic after inputs enter the grammar; CV extraction may be heuristic"
- "630 tests" (previously unverifiable from shipped package) → Standalone runners now shipped and reproducible
- process_image "stability-tested" → "calibrates, parses, type-checks, and executes (no stability testing)"
- verify_substrate as "proof" → "integration coherence check"
- "Grammar fully describes itself" → "narrow self-hosting"

## What Remains Outside Scope

- Full Aurexis Core completion
- Real-world camera/print/scan robustness
- End-to-end non-heuristic operation (input layer may be heuristic)
- Equally strong independent proof for every subsystem
- Image-as-program from actual raster artifacts (next milestone: Raster Law Bridge V1)

## Why This Is a Candidate Baseline

This package proves a narrow law-bearing slice works: frozen grammar, deterministic evaluation, type safety, composition, calibration, narrow self-hosting, and integration coherence. It does not prove the full Aurexis Core vision. The broader vision requires, at minimum, actual image artifacts carrying programs, real-world capture robustness, and broader grammar expressiveness. This baseline is the foundation for that work.

## Git Tag

Not created in this environment (no git repository available). To create:

```bash
git tag -a aurexis-core-v1-substrate-candidate -m "Aurexis Core V1 Substrate Candidate — locked baseline, narrow law-bearing package"
git push origin aurexis-core-v1-substrate-candidate
```

---

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
