# Aurexis Core V2 — Charter Amendments

---

## Amendment 1 — Decode Engine Track (2026-04-18)

**Authorized by:** Vincent Anderson
**Reason:** The E/D client's decode pipeline (~2000 lines in `aurexis_ed_unified.html`) is structurally a Core capability, not a client feature. Finder detection, homography, format selection, module sampling, color classification, RS decode, and frame fusion are Core-level functions that any client should call. Extracting and proving them as a standalone, DOM-free, testable module is Core v2 work.

**What changes:**

1. **V2_EXCLUSIONS.md §6 ("E/D work") is narrowed.** V2 still does not touch E/D *client* files (UI, camera management, APK). V2 *does* build a standalone decode engine module that E/D (and any future client) can import. The decode engine is Core, not E/D.

2. **V2_ROADMAP.md gains a decode engine milestone track (D0–D4)** running parallel to the calibration track (M3–M8). The decode track does not block or modify the calibration track. Both tracks share the V2 branch, test suite, and provenance standard.

3. **V2_MILESTONE_GATES.md gains decode-track gates (GD0–GD4).**

4. **V2_EXCLUSIONS.md §5 ("broad new theory branching") is unaffected.** The decode engine extracts and refines existing proven logic from the E/D client. No new Core branches, bridge families, or substrate categories are created.

5. **V2_EXCLUSIONS.md §12 ("motion and video pipelines") is unaffected.** The decode engine processes single frames. Multi-frame fusion is frame-by-frame accumulation of static captures, not video/motion.

**What does NOT change:**

- V1 freeze, V1/V2 isolation rule, clean-room provenance standard — all unchanged
- Calibration track (M0–M8) — unmodified, still the primary V2 deliverable
- E/D client files — not touched by V2
- No new Core branches, bridge families, or exotic optics

---
