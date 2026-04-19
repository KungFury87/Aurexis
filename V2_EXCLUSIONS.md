# Aurexis Core V2 — Exclusions (Non-Goals)

**Locked:** 2026-04-14

The following are explicitly out of scope for V2. If any of these appear in a task prompt, the response is: "out of V2 scope — requires charter amendment."

---

## Hard exclusions

1. **Print-based calibration.** No printed targets, no paper fixtures, no physical calibration boards as a V2 dependency. V2 is screen-based only.
2. **Multi-person / team-dependent workflows.** V2 must be executable end-to-end by Vincent alone.
3. **Multi-phone as a requirement.** Additional devices may appear in optional later expansions but are never a V2 completion requirement.
4. **Exotic optics.** No macro lenses, no lab-grade optics, no camera rigs beyond a stable consumer phone mount.
5. **Broad new theory branching.** V2 does not spawn new Core branches, new bridge families, or new substrate categories. V2 exercises what V1 already substrates.
6. **E/D client work.** V2 does not touch E/D client files (UI, camera management, APK, `aurexis_ed_unified.html`). V2 *does* build a standalone decode engine module (`v2_decode/`) that extracts and proves Core-level decode logic (finder detection, homography, format selection, module sampling, RS decode, frame fusion) as a testable, DOM-free module. The decode engine is Core, not E/D. *(Amended 2026-04-18 — see `V2_CHARTER_AMENDMENTS.md` §1.)*
7. **Full Core completion.** V2 is a calibration candidate, not the final Core.
8. **Modifications to the frozen V1 backup folder** (`C:\Users\vince\Desktop\Aurexis evolved\back again`). Reads only.
9. **Rewriting V1 substrate modules.** V1 is frozen. V2 may add modules and add evidence; V2 does not alter V1 substrate source.
10. **Protected / copyrighted / licensed code** in a form that obligates paid licensing or unsupplyable attribution. Clean-room standard inherited from V1.
11. **GitHub pushes without explicit Vincent instruction.** Local commits and branches are fine; remote pushes require his sign-off.
12. **Motion and video pipelines.** V2 is static-first. Video / live tracking is out of V2.
13. **Simulated / synthetic evidence substituted for real captures.** V2's whole point is real optical evidence. Synthetic data may only be used as reference for specification, never as a stand-in for the pilot or validation runs.
14. **Unmeasured improvement claims.** Before/after statements must be numeric and traceable to specific captures.

15. **Reuse or mutation of any V1 backup / release surface.** V2 must never override, delete, retag, or reuse V1 refs. All V2 refs use V2-only namespaces.

    - **Allowed:** `working/core-v2`, `backup/v2-...` branches, `backup-v2-...` tags, future `core-v2-...` release tags.
    - **Forbidden:** reusing or mutating `backup/v1-...` branches, reusing or mutating `backup-v1-...` tags, changing `core-v1-substrate-candidate-or1`, changing `core-v1-substrate-candidate-or1.1`, pushing V2 state onto any V1 release surface, force-pushing / deleting / retagging any V1 ref, renaming V1 refs.

    This exclusion is immutable for the duration of V2 and cannot be amended.

## Soft exclusions (require charter amendment before entry)

- Additional benchmark categories beyond the M2-locked set
- Additional calibration profiles beyond the M5 pass (unless earned through M7 controlled expansion)
- Integration with external services, cloud pipelines, or third-party APIs
- User-facing packaging (GUI, installer, distribution channel)
- Performance / optimization work unrelated to calibration correctness

## Re-scope procedure

If Vincent wants to bring any excluded item into V2:
1. State the item and the justification explicitly.
2. Update the charter, completion definition, roadmap, and gates in one bundled pass.
3. Record the amendment in `V2_CHARTER_AMENDMENTS.md` with date and reason.
4. Only then is the excluded item in scope.
