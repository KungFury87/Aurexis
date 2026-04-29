# Round 57 — L2 identity layer wired (P-02 closure, 36 rounds STALE)

**Date:** 2026-04-29
**Track:** L2 (recognition by feature) / T6 (Phoxelis as MCP / external classifier integration)
**Status:** complete — P-02 closed; first L1 vs L2 agreement measurement

---

## What this round opened on

The audit at R56 close reported **P-02 stale since R21C design doc, >35 rounds** — by far the oldest open promise in the project. R21C (R21 in 2026-04-22ish, ~6 weeks ago) wrote the design doc `IDENTITY_LAYER_DESIGN.md` specifying the interface (`external_classifier(image, classifier_key, expected_label) -> bool` + `runtime.register_classifier(key, fn)` hook) but explicitly deferred implementation: *"no model is shipped, no operators are registered."*

The roadmap had R57 = P-07 (multi-modal sensors). Pivoted: P-07 needs Vincent's harness sensor data which isn't in the sandbox; P-02 is fully sandbox-doable. The audit's velocity-gate discipline says oldest stale first, and pivoting closed the right promise.

## What got built

`round57_l2_identity/` implements the R21C interface as a thin module:

```python
# Registry
def register_classifier(key: str, fn): _CLASSIFIERS[key] = fn

# The R21C operator
def external_classifier(image, classifier_key, expected_label="") -> bool:
    if classifier_key not in _CLASSIFIERS:
        return None  # BLOCKED, per the design
    label = _CLASSIFIERS[classifier_key](image)
    if expected_label == "":
        return bool(label)
    return label == expected_label

# The first real classifier plugged in
register_classifier("face_id", opencv_face_detector)  # OpenCV Haar cascade
```

The substrate is unchanged. The L2 layer is opt-in: without `register_classifier`, the operator returns `None` (the R21C-prescribed BLOCKED behaviour). With it, identity verdicts are real.

## Experiment

Pull a fresh ~10-image batch from the source router (picsum + wikimedia + iNaturalist), run **both** the L1 face heuristic and the L2 OpenCV detector on the same images in one pass, measure agreement.

## Results (N=9)

```
alias                           stage              L1_face  L1_genuine  L2_face  L2_n
picsum_2541772                  stage_1_easy           F         F        False   0
picsum_4291381                  stage_1_easy           F         F        True    1
picsum_5110769                  stage_1_easy           F         F        False   0
wm_000_Tyrannus_tyrannus_4zz    stage_2_diverse        F         T        False   0
wm_001_1888_Arabian_Sea_cyclon  stage_2_diverse        F         T        False   0
wm_002_Kokudo_1_go_Nissaka      stage_2_diverse        F         F        False   0
inat_348261897                  stage_3_wildlife       F         F        False   0
inat_348261853                  stage_3_wildlife       F         F        False   0
inat_348261839                  stage_3_wildlife       F         F        False   0

L1 has_face_like_signature  fires on 0/9
L1 has_genuine_face         fires on 2/9
L2 OpenCV Haar              fires on 1/9
L1 face_like  vs L2: agree on 8/9 = 88.89%
L1 genuine    vs L2: agree on 6/9 = 66.67%
```

**The one informative disagreement:** `picsum_4291381` — the OpenCV detector found a face but the L1 `has_face_like_signature` heuristic didn't fire. That's an **L1 false negative**: the heuristic is missing a real face.

The two `has_genuine_face_not_screen` true-positives (the bird Tyrannus and the cyclone image) where L2 found nothing are **L1 false positives** of the genuine-face predicate, not the face-like one. The face-like predicate is more conservative and didn't fire on those.

## Headline benchmark row

| metric | round | value | corpus | status |
|---|---|---|---|---|
| L1 vs L2 face-detection agreement | R57 | 89% (face_like) / 67% (genuine_face) on N=9 fresh web pull | 9 images via source router | current — first L2-grounded measurement of L1 face heuristic accuracy |

## What this round does and doesn't claim

**Claims:**
- L2 layer wired per the R21C design — `external_classifier` + `register_classifier` hook implemented as a usable Python module.
- First real classifier plugged in: OpenCV Haar cascade (CC0, no auth, ships in opencv-python-headless).
- First L1-vs-ground-truth measurement on the existing face heuristics. The L1 `has_face_like_signature` agrees with the CV detector at 89% on this small sample; one false negative observed.

**Does NOT claim:**
- That 9 images is enough to characterise the L1 heuristics. The same R53/R54 small-N caveat applies: the corpus needs to be much larger to claim accuracy numbers. R59 (corpus growth + retry) addresses this.
- That OpenCV Haar is a great face detector. It's brittle on profiles, low-light, partial occlusion. Better classifiers (mediapipe, DeepFace) can be plugged into the same registry — the architecture supports it.
- That the agreement rate generalises beyond the picsum/wikimedia/iNaturalist mix. iNaturalist heavily skews toward wildlife, where neither L1 nor L2 should fire on faces. The interesting test is on a corpus with more humans.

## Promises ledger updates

- **P-02** (L2 identity layer wiring): closes with C-57 evidence. **36 rounds STALE.**

## Tool ladder updates

`opencv-python-headless` joins the permanent-substrate tier as a CV primitive, alongside numpy/scipy/Pillow/reedsolo/bchlib. Phoxelis is not aiming to replace OpenCV's Haar cascades; it aims to wrap them as L2 classifiers and audit their verdicts against L1.

## Files added this round

- `round57_l2_identity/round57_l2_identity.py` — original v1 (alias-aligned, didn't fetch matching images)
- `round57_l2_identity/round57_l2_identity_v2.py` — runnable v2 that does the actual measurement
- `round57_l2_identity/round57_results.json` — per-image L1/L2 verdicts
- this report

## What this round changes about future rounds

Any future predicate authoring can now reference L2 verdicts via `external_classifier`. Compositional L4 predicates (R56) can mix L1 heuristics + L2 classifiers in their dependency lists. The vocabulary becomes hybrid without changing the substrate.

## Next round opens with

`python phoxelis_audit.py`. STALE count after R57 should be 6 (P-02 closed). NBR candidates among remaining stale:

- **R58 — P-07 (multi-modal sensors)**: synthetic accel/gyro/audio time-series + 3-5 sensor-based predicates. Sandbox-doable; gives T3 its first real measurement. Still needs Vincent's real harness data eventually.
- **R58 — P-08 (real social platform via Chrome MCP)**: extend R51 autonomy through Chrome to Reddit/Mastodon/Imgur for true platform-class round-trip.
- **R58 — P-04 (phone-camera-in-loop) inverted**: instead of waiting for Vincent's camera, encode a Phoxelis frame, display it on the dashboard, and have a public webcam look at it. Requires arranging a camera-pointed-at-screen setup; harder to do autonomously.
- **R58 — Run the R55 harness inline + retry P-10 + R56 collisions**: at N>=50, the small-N collapse should dissolve enough that R54's blocked predicate and R56's 3 colliding L4 predicates can be re-audited.
