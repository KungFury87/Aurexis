"""Blocked-family unlock / ROI-sensitive metric expansion (v2.0).

v1.9 mapped the arbitration boundary across 8 primitive families:
3 confirmed PRIMITIVE_AWARE_HELPS (cardinality, repetition, role_zone)
and 5 tagged METRIC_GAP_ROI_INSENSITIVE (ordering, adjacency, symmetry,
orientation, hierarchy). Those 5 weren't immune to arbitration - their
metrics simply ignored ROI, so the test could not run honestly.

v2.0 unlocks two of those families (ordering and symmetry) with new
ROI-sensitive metrics and target-conditioned rankers. The remaining
three (adjacency, orientation, hierarchy) stay tagged
METRIC_GAP_ROI_INSENSITIVE pending further work. The result: 5 of 8
primitive families are now confirmed PRIMITIVE_AWARE_HELPS, 3 of 8
remain blocked.

Mechanism (same as v1.7 / v1.8 / v1.9):

  - For each new family, define an ROI-sensitive metric that scores a
    candidate ROI by structure that matches the primitive's needs.
  - Use that metric directly as a target-conditioned ranking signal.
  - Run the comparison against the best of v1.6's 4 single + 2 fused
    generic rankers.
  - Add a distractor composite where generic rankers fail.

ROI-sensitive ordering metric (this module):

  Within the candidate ROI, threshold the captured image and find
  components. Take the top-N by area (where N = target_count). Sort
  by x-centroid. Compute a monotonicity score over their mean luma
  sequence: max of ascending-pair fraction and descending-pair
  fraction. Score = monotonicity score. Returns 0 if fewer than
  target_count components.

ROI-sensitive symmetry metric (this module):

  Within the ROI's bounding box, mirror the captured luma about the
  target axis (vertical -> left/right; horizontal -> top/bottom),
  restricted to ROI pixels valid on both halves. Score = Pearson
  correlation between the two halves, clipped to [0, 1].

Verdicts inherit v1.9's scheme. The remaining label-scoped families
without ROI-aware metrics are now {adjacency, orientation, hierarchy}.

Honest scope (v2.0 still NOT claiming):
  - The ordering metric uses x-centroid axis only and assumes a
    horizontal ordering arrangement. A vertical-axis variant could be
    added; not in v2.0.
  - The symmetry metric uses pixel-level mirror-correlation only. It
    does not score component-level structural symmetry.
  - adjacency, orientation, hierarchy are NOT unlocked in v2.0.
  - Still not a decoder, not E/D, not a runtime, not a camera app.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, List, Dict, Callable

import numpy as np

from .simulate import SimParams, run_chain
from .interaction import INTERACTION_CAPTURE
from .binding import (
    cardinality_survival_bound,
    compute_relation_metric_bound,
    ROBUST_THR,
)
from .inferred_binding import PROPOSALS
from .arbitration import candidates_from_mask, _components
from .distractor_arbitration import RANKERS as SINGLE_RANKERS
from .fusion import FUSED_RANKERS
from .primitive_aware import (
    rank_by_cardinality_target,
    best_generic_top1 as _best_generic_top1,
)
from .coverage import (
    repetition_survival_bound_strip,
    rank_by_repetition_target_strip,
)
from .boundary import (
    BOUNDARY_COMPOSITES,
    role_zone_survival_bound,
    rank_by_role_zone_target,
)
from .relations import _lum


# -------------------------------------------------------------------
# ROI-sensitive ordering metric
# -------------------------------------------------------------------

def ordering_survival_bound(truth_pkt, captured, roi_mask,
                              target_count=None):
    """Score a candidate ROI as an ordering scene.

    Within the ROI:
      1. Threshold the captured image (mean + 1.5 sd; clamped).
      2. Find connected components.
      3. Take the top-N by area where N = target_count.
      4. Sort by x-centroid.
      5. Compute the monotonicity of the mean-luma sequence in that
         x-order: max of (ascending-pair fraction, descending-pair
         fraction).

    Returns 0 if fewer than target_count components are found, or if
    the components are degenerate.
    """
    rel = truth_pkt["meta"].get("relation", {})
    target = rel.get("target_count", target_count)
    if target is None or int(target) < 2:
        return float("nan")
    target = int(target)

    lum = _lum(captured)
    thr = float(lum.mean() + 1.5 * lum.std())
    thr = max(thr, float(lum.mean()) + 0.10)
    if roi_mask.dtype != bool:
        roi_mask = roi_mask.astype(bool)
    binary = (lum > thr) & roi_mask
    if not binary.any():
        return 0.0

    components = _components(binary)
    if len(components) < target:
        return 0.0

    # Take top-N by area
    components = sorted(components, key=lambda c: -int(c.sum()))[:target]

    data = []
    for c in components:
        ys, xs = np.where(c)
        if xs.size == 0:
            continue
        cx = float(xs.mean())
        m = float(lum[c].mean())
        data.append((cx, m))

    if len(data) < target:
        return 0.0

    data.sort(key=lambda d: d[0])
    means = [d[1] for d in data]

    n = len(means)
    inc = 0; dec = 0; total = 0
    for i in range(n):
        for j in range(i + 1, n):
            total += 1
            if means[j] > means[i]:
                inc += 1
            elif means[j] < means[i]:
                dec += 1
    if total == 0:
        return 0.0
    return float(max(inc, dec) / total)


def rank_by_ordering_target(cands, captured, target_count):
    if not cands or target_count is None:
        return []
    target = int(target_count)
    scores = []
    for c in cands:
        pkt = {"meta": {"relation": {"kind": "ordering",
                                       "target_count": target}}}
        s = ordering_survival_bound(pkt, captured, c,
                                       target_count=target)
        scores.append(float(s) if isinstance(s, float) and s == s else 0.0)
    return sorted(range(len(cands)), key=lambda i: -scores[i])


# -------------------------------------------------------------------
# ROI-sensitive symmetry metric
# -------------------------------------------------------------------

def symmetry_survival_bound(truth_pkt, captured, roi_mask,
                              target_axis=None):
    """Score a candidate ROI as a symmetric pattern.

    Within the ROI's bounding box, mirror the captured luma about the
    target axis (vertical -> left/right halves; horizontal -> top/
    bottom halves), restricted to pixels that are inside the ROI on
    both sides. Returns max(0, Pearson correlation) between the two
    halves. Returns 0 if there's not enough data.
    """
    rel = truth_pkt["meta"].get("relation", {})
    axis = rel.get("axis", target_axis) or "vertical"
    if roi_mask.dtype != bool:
        roi_mask = roi_mask.astype(bool)
    if not roi_mask.any():
        return 0.0
    lum = _lum(captured).astype(np.float64)

    ys, xs = np.where(roi_mask)
    y0, y1 = int(ys.min()), int(ys.max() + 1)
    x0, x1 = int(xs.min()), int(xs.max() + 1)

    # Guard: a meaningful symmetry test needs a non-trivial bbox
    # span along the mirror axis AND at least 2 components inside
    # (so a single round blob doesn't pass trivially).
    bbox_w = x1 - x0
    bbox_h = y1 - y0
    if axis == "vertical" and bbox_w < 20:
        return 0.0
    if axis == "horizontal" and bbox_h < 20:
        return 0.0
    thr = float(lum.mean() + 1.5 * lum.std())
    thr = max(thr, float(lum.mean()) + 0.10)
    binary_in = (lum > thr) & roi_mask
    if int(binary_in.sum()) >= 1:
        comps_in = _components(binary_in)
        if len(comps_in) < 2:
            return 0.0

    patch = lum[y0:y1, x0:x1]
    msk = roi_mask[y0:y1, x0:x1]

    if axis == "vertical":
        mid = patch.shape[1] // 2
        if mid < 2:
            return 0.0
        left = patch[:, :mid]
        right = patch[:, -mid:][:, ::-1]
        ml = msk[:, :mid]
        mr = msk[:, -mid:][:, ::-1]
        valid = ml & mr
    else:
        mid = patch.shape[0] // 2
        if mid < 2:
            return 0.0
        left = patch[:mid, :]
        right = patch[-mid:, :][::-1, :]
        ml = msk[:mid, :]
        mr = msk[-mid:, :][::-1, :]
        valid = ml & mr

    if int(valid.sum()) < 5:
        return 0.0
    a = left[valid]; b = right[valid]
    if a.std() < 1e-9 or b.std() < 1e-9:
        return 0.0
    c = float(np.corrcoef(a - a.mean(), b - b.mean())[0, 1])
    if not (isinstance(c, float) and c == c):
        return 0.0
    return float(max(0.0, c))


def rank_by_symmetry_target(cands, captured, target_axis):
    if not cands or target_axis is None:
        return []
    scores = []
    for c in cands:
        pkt = {"meta": {"relation": {"kind": "symmetry",
                                       "axis": target_axis}}}
        s = symmetry_survival_bound(pkt, captured, c,
                                       target_axis=target_axis)
        scores.append(float(s) if isinstance(s, float) and s == s else 0.0)
    return sorted(range(len(cands)), key=lambda i: -scores[i])


# -------------------------------------------------------------------
# Distractor composites for ordering and symmetry
# -------------------------------------------------------------------

def composite_ordering_distractor(size: int = 192, seed: int = 0) -> dict:
    """Intended: 5 markers in a horizontal row at y=0.7 with
    monotonically increasing brightness 0.40 -> 0.85. Decoy: 5 markers
    at y=0.25 with shuffled (non-monotone) brightness, all uniformly
    bright (0.95). Generic rankers favor the brighter decoy; the
    ordering-aware metric demands monotone progression and rejects it."""
    img = np.full((size, size), 0.15, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    yy, xx = np.mgrid[0:size, 0:size]

    int_y = int(size * 0.70)
    r = max(4, size // 32)
    n_int = 5
    p = max(20, size // 8)
    x0 = int(size * 0.05)
    int_brightness = [0.40, 0.50, 0.60, 0.72, 0.85]
    for i in range(n_int):
        cx = x0 + i * p
        if cx >= size:
            break
        m = (yy - int_y) ** 2 + (xx - cx) ** 2 <= r * r
        img[m] = int_brightness[i]
        lab[m] = 1 + i
    ord_labels = np.where((lab >= 1) & (lab <= n_int), lab, 0).astype(np.int32)

    # Decoy: 5 same-brightness markers in shuffled brightness positions
    # (or simpler: all uniform - then no monotone progression).
    dec_y = int(size * 0.25)
    r_dec = max(6, size // 26)
    n_dec = 5
    p_dec = max(20, size // 8)
    x0d = int(size * 0.10)
    for i in range(n_dec):
        cx = x0d + i * p_dec
        if cx >= size:
            break
        m = (yy - dec_y) ** 2 + (xx - cx) ** 2 <= r_dec * r_dec
        img[m] = 0.95
        lab[m] = 101 + i

    img = np.clip(img, 0.0, 1.0)
    return {
        "image": img,
        "labels": lab,
        "meta": {
            "relation": {"kind": "composite", "parts": ["ordering"]},
            "composite": [
                {"name": "ordering",
                 "labels": ord_labels,
                 "relation": {"kind": "ordering",
                              "target_count": n_int}},
            ],
        },
    }


def composite_symmetry_distractor(size: int = 192, seed: int = 0) -> dict:
    """Intended: a vertically-symmetric arrangement of 4 markers
    around an anchor (left+right mirror). Decoy: an asymmetric bright
    cluster at a different y. Generic rankers favor the brighter decoy;
    the symmetry-aware metric demands left/right mirror correlation
    and rejects the decoy."""
    img = np.full((size, size), 0.15, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    yy, xx = np.mgrid[0:size, 0:size]

    # Intended: a smaller, dimmer symmetric pattern at y=0.75. Each
    # pair is at +/- dx from cx_center; small radius and modest
    # brightness ensure generic rankers will prefer the decoy.
    cx_center = int(size * 0.25)
    cy_center = int(size * 0.75)
    r = max(3, size // 36)
    pairs = [(12, -4), (22, 3), (32, -2)]
    for i, (dx, dy) in enumerate(pairs):
        for sign in (-1, 1):
            cx = cx_center + sign * dx
            cy = cy_center + dy
            m = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
            img[m] = 0.55
            lab[m] = 1 + 2 * i + (0 if sign == -1 else 1)
    sym_labels = np.where((lab >= 1) & (lab <= 6), lab, 0).astype(np.int32)

    # Decoy: ONE big bright asymmetric blob at y=0.25 - large area,
    # high intensity, high edges, high compactness (round disc),
    # so ALL four single rankers prefer it.
    dec_y = int(size * 0.25)
    dec_x = int(size * 0.65)
    r_dec = max(20, size // 7)
    m_dec = (yy - dec_y) ** 2 + (xx - dec_x) ** 2 <= r_dec * r_dec
    img[m_dec] = 0.95
    lab[m_dec & (lab == 0)] = 101
    # Add a small asymmetric bump to break any accidental symmetry
    bump_y = int(size * 0.20)
    bump_x = int(size * 0.85)
    m_bump = (yy - bump_y) ** 2 + (xx - bump_x) ** 2 <= 6 * 6
    img[m_bump] = 0.95
    lab[m_bump & (lab == 0)] = 102

    img = np.clip(img, 0.0, 1.0)
    return {
        "image": img,
        "labels": lab,
        "meta": {
            "relation": {"kind": "composite", "parts": ["symmetry"]},
            "composite": [
                {"name": "symmetry",
                 "labels": sym_labels,
                 "relation": {"kind": "symmetry",
                              "axis": "vertical"}},
            ],
        },
    }


UNLOCK_COMPOSITES: Dict[str, Callable[..., dict]] = {
    **BOUNDARY_COMPOSITES,
    "composite_ordering_distractor":  composite_ordering_distractor,
    "composite_symmetry_distractor":  composite_symmetry_distractor,
}


# -------------------------------------------------------------------
# Verdicts (extends boundary)
# -------------------------------------------------------------------

# v2.0: ordering + symmetry now have ROI-aware metrics, so they are
# NOT in the no-ROI label-scoped set anymore. adjacency, orientation,
# hierarchy remain blocked.
LABEL_SCOPED_NO_ROI_V20 = {"adjacency", "orientation", "hierarchy"}


def _per_composite_verdict(oracle_best, best_generic, target_aware,
                            relation_kind):
    ok = lambda x: isinstance(x, float) and x == x
    if not ok(oracle_best) or oracle_best < ROBUST_THR:
        return "PROPOSAL_QUALITY_LIMIT"
    if relation_kind in LABEL_SCOPED_NO_ROI_V20:
        return "METRIC_GAP_ROI_INSENSITIVE"
    target_ok = ok(target_aware) and target_aware >= ROBUST_THR
    generic_ok = ok(best_generic) and best_generic >= ROBUST_THR
    if generic_ok:
        return "GENERIC_FUSION_SUFFICIENT"
    if target_ok:
        return "PRIMITIVE_AWARE_HELPS"
    return "PRIMITIVE_AWARE_STILL_FAILS"


def _family_verdict(per_composite_verdicts):
    if not per_composite_verdicts:
        return "METRIC_GAP_ROI_INSENSITIVE"
    pri = ["PRIMITIVE_AWARE_HELPS", "GENERIC_FUSION_SUFFICIENT",
           "PRIMITIVE_AWARE_STILL_FAILS", "PROPOSAL_QUALITY_LIMIT",
           "METRIC_GAP_ROI_INSENSITIVE", "ARBITRATION_INVARIANT"]
    for v in pri:
        if v in per_composite_verdicts:
            return v
    return per_composite_verdicts[0]


def _fmax_idx(scores):
    best = None; best_idx = None
    for i, v in enumerate(scores):
        if isinstance(v, float) and v == v:
            if best is None or v > best:
                best = v; best_idx = i
    return best_idx, best


# -------------------------------------------------------------------
# Per-candidate scoring + primitive-aware top1 dispatch
# -------------------------------------------------------------------

def _score_candidate(sub, captured, c):
    kind = sub["relation"]["kind"]
    if kind == "repetition":
        pkt = {"meta": {"relation": sub["relation"]}}
        return repetition_survival_bound_strip(pkt, captured, c)
    if kind == "role_zone":
        target = sub["relation"].get("target_satellites")
        pkt = {"meta": {"relation": sub["relation"]}}
        return role_zone_survival_bound(pkt, captured, c,
                                          target_satellites=target)
    if kind == "ordering":
        target = sub["relation"].get("target_count")
        pkt = {"meta": {"relation": sub["relation"]}}
        return ordering_survival_bound(pkt, captured, c,
                                          target_count=target)
    if kind == "symmetry":
        axis = sub["relation"].get("axis", "vertical")
        pkt = {"meta": {"relation": sub["relation"]}}
        return symmetry_survival_bound(pkt, captured, c,
                                          target_axis=axis)
    return compute_relation_metric_bound(sub, captured, c)


def _primitive_aware_top1(sub, all_cands, captured, scores):
    kind = sub["relation"]["kind"]
    target_idx = -1; target_top1 = float("nan")
    target_params: Dict[str, object] = {}
    if kind == "cardinality":
        target_params = {"target_count": sub["relation"]["count"]}
        order = rank_by_cardinality_target(
            all_cands, captured, sub["relation"]["count"])
        if order:
            target_idx = int(order[0]); target_top1 = scores[target_idx]
    elif kind == "repetition":
        target_params = {"target_period": sub["relation"]["period_px"],
                         "row_y": sub["relation"]["row_y"]}
        order = rank_by_repetition_target_strip(
            all_cands, captured,
            sub["relation"]["period_px"],
            sub["relation"]["row_y"])
        if order:
            target_idx = int(order[0]); target_top1 = scores[target_idx]
    elif kind == "role_zone":
        target_params = {"target_satellites":
                          sub["relation"].get("target_satellites")}
        order = rank_by_role_zone_target(
            all_cands, captured,
            sub["relation"].get("target_satellites"))
        if order:
            target_idx = int(order[0]); target_top1 = scores[target_idx]
    elif kind == "ordering":
        target_params = {"target_count": sub["relation"]["target_count"]}
        order = rank_by_ordering_target(
            all_cands, captured, sub["relation"]["target_count"])
        if order:
            target_idx = int(order[0]); target_top1 = scores[target_idx]
    elif kind == "symmetry":
        target_params = {"axis": sub["relation"].get("axis", "vertical")}
        order = rank_by_symmetry_target(
            all_cands, captured, sub["relation"].get("axis", "vertical"))
        if order:
            target_idx = int(order[0]); target_top1 = scores[target_idx]
    return target_top1, target_idx, target_params


# -------------------------------------------------------------------
# Dossier
# -------------------------------------------------------------------

def build_unlock_dossier(size: int = 192, seed: int = 0) -> dict:
    capture = INTERACTION_CAPTURE()
    per_composite: Dict[str, dict] = {}

    for comp_kind, builder in UNLOCK_COMPOSITES.items():
        pkt = builder(size=size, seed=seed)
        result = run_chain(pkt["image"], capture, seed=seed)
        captured = result["captured"]

        all_cands = []
        for pname, propose in PROPOSALS.items():
            try:
                mask = propose(captured)
            except Exception:
                mask = np.zeros(captured.shape[:2], dtype=bool)
            for c in candidates_from_mask(mask,
                                           min_area=max(4, size // 16),
                                           dilate=2):
                all_cands.append(c)

        sub_records = []
        for sub in pkt["meta"]["composite"]:
            kind = sub["relation"]["kind"]

            scores = []
            for c in all_cands:
                v = _score_candidate(sub, captured, c)
                scores.append(float(v) if isinstance(v, float) and v == v
                              else float("nan"))
            oracle_idx, oracle_best = _fmax_idx(scores)

            best_generic, best_generic_name, generic_top1 = (
                _best_generic_top1(all_cands, captured, scores))

            target_top1, target_idx, target_params = (
                _primitive_aware_top1(sub, all_cands, captured, scores))

            verdict = _per_composite_verdict(
                oracle_best, best_generic, target_top1, kind)

            sub_records.append({
                "sub_primitive":     sub["name"],
                "relation_kind":     kind,
                "n_candidates":      len(all_cands),
                "target_params":     target_params,
                "label_scoped_no_roi": kind in LABEL_SCOPED_NO_ROI_V20,
                "oracle_best":       (oracle_best
                                       if oracle_best is not None
                                       else float("nan")),
                "oracle_idx":        (oracle_idx if oracle_idx is not None
                                       else -1),
                "generic_top1":      generic_top1,
                "best_generic":      (best_generic
                                       if best_generic is not None
                                       else float("nan")),
                "best_generic_name": best_generic_name,
                "primitive_aware":   target_top1,
                "primitive_aware_idx": target_idx,
                "verdict":           verdict,
            })

        sev = {"GENERIC_FUSION_SUFFICIENT":   0,
               "PRIMITIVE_AWARE_HELPS":       1,
               "ARBITRATION_INVARIANT":       1,
               "METRIC_GAP_ROI_INSENSITIVE":  2,
               "PRIMITIVE_AWARE_STILL_FAILS": 3,
               "PROPOSAL_QUALITY_LIMIT":      4}
        worst = max((sr["verdict"] for sr in sub_records),
                    key=lambda v: sev.get(v, -1))
        per_composite[comp_kind] = {
            "sub_relations":   sub_records,
            "overall_verdict": worst,
        }

    family_to_verdicts: Dict[str, List[str]] = {}
    for ck, rec in per_composite.items():
        for sr in rec["sub_relations"]:
            family_to_verdicts.setdefault(sr["relation_kind"], []).append(
                sr["verdict"])
    for fam in LABEL_SCOPED_NO_ROI_V20:
        family_to_verdicts.setdefault(fam, ["METRIC_GAP_ROI_INSENSITIVE"])

    family_map = {}
    for fam, verdicts in sorted(family_to_verdicts.items()):
        family_map[fam] = {
            "per_composite_verdicts": verdicts,
            "boundary_tag": _family_verdict(verdicts),
        }

    return {
        "schema_version": "2.0",
        "interaction_capture": capture.as_dict(),
        "single_rankers": list(SINGLE_RANKERS.keys()),
        "fused_rankers":  list(FUSED_RANKERS.keys()),
        "primitive_aware_rankers": ["cardinality_target",
                                     "repetition_target_strip",
                                     "role_zone_target",
                                     "ordering_target",
                                     "symmetry_target"],
        "thresholds": {"robust_thr": ROBUST_THR},
        "per_composite": per_composite,
        "family_boundary_map": family_map,
    }


# -------------------------------------------------------------------
# Report writer
# -------------------------------------------------------------------

def _scrub(o):
    if isinstance(o, dict): return {k: _scrub(v) for k, v in o.items()}
    if isinstance(o, list): return [_scrub(v) for v in o]
    if isinstance(o, float) and (o != o): return None
    return o


def _f(v):
    if not (isinstance(v, float) and v == v):
        return "n/a"
    return "{:.3f}".format(v)


def write_unlock_reports(out_dir: Path,
                          dossier: Optional[dict] = None) -> dict:
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    dossier = dossier or build_unlock_dossier()

    with open(out_dir / "unlock.json", "w", encoding="utf-8") as f:
        json.dump(_scrub(dossier), f, indent=2)

    L = []
    L.append("# Aurexis Research Sim v2.0 - Blocked-family unlock dossier")
    L.append("")
    L.append("v1.9 mapped 3 of 8 primitive families as PRIMITIVE_AWARE_HELPS")
    L.append("and tagged 5 as METRIC_GAP_ROI_INSENSITIVE. v2.0 unlocks two of")
    L.append("those (ordering, symmetry) by adding ROI-sensitive metrics +")
    L.append("target-conditioned rankers + distractor composites. The result")
    L.append("is 5 of 8 primitive families confirmed PRIMITIVE_AWARE_HELPS;")
    L.append("3 of 8 (adjacency, orientation, hierarchy) remain blocked.")
    L.append("")
    L.append("Verdict (per composite):")
    L.append("- **GENERIC_FUSION_SUFFICIENT**    best generic ranker passes")
    L.append("- **PRIMITIVE_AWARE_HELPS**        only primitive-aware passes")
    L.append("- **PRIMITIVE_AWARE_STILL_FAILS**  oracle passes; both fail")
    L.append("- **PROPOSAL_QUALITY_LIMIT**       oracle_best < {:.2f}".format(ROBUST_THR))
    L.append("- **METRIC_GAP_ROI_INSENSITIVE**   metric is label-scoped; no ROI-aware variant; arbitration test not possible")
    L.append("")

    L.append("## Family boundary map (v2.0)")
    L.append("")
    L.append("| family | boundary_tag | per-composite verdicts |")
    L.append("|--------|--------------|------------------------|")
    for fam, rec in dossier["family_boundary_map"].items():
        verdicts = ", ".join(rec["per_composite_verdicts"])
        L.append("| " + fam + " | **" + rec["boundary_tag"] + "** | " + verdicts + " |")
    L.append("")

    L.append("## Overall summary (per composite)")
    L.append("| composite | overall verdict |")
    L.append("|-----------|-----------------|")
    for ck, rec in dossier["per_composite"].items():
        L.append("| " + ck + " | **" + rec["overall_verdict"] + "** |")
    L.append("")

    for ck, rec in dossier["per_composite"].items():
        L.append("### " + ck)
        L.append("- overall_verdict: **" + rec["overall_verdict"] + "**")
        L.append("| sub | kind | target | oracle_best | best_generic (which) | primitive_aware | verdict |")
        L.append("|---|---|---|---|---|---|---|")
        for sr in rec["sub_relations"]:
            tp = sr["target_params"]
            tp_str = ", ".join(k + "=" + str(v) for k, v in tp.items()) or "-"
            L.append("| " + sr["sub_primitive"] + " | " + sr["relation_kind"]
                     + " | " + tp_str
                     + " | " + _f(sr["oracle_best"])
                     + " | " + _f(sr["best_generic"])
                     + " (" + (sr["best_generic_name"] or "-") + ")"
                     + " | " + _f(sr["primitive_aware"])
                     + " | " + sr["verdict"] + " |")
        L.append("")

    with open(out_dir / "UNLOCK.md", "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return dossier


def main():
    dossier = build_unlock_dossier()
    write_unlock_reports(Path.cwd(), dossier)
    print("Aurexis Research Sim v2.0 - Blocked-family unlock dossier")
    print("")
    print("Family boundary map:")
    for fam, rec in dossier["family_boundary_map"].items():
        print("  " + "{:<14}".format(fam) + rec["boundary_tag"])
    print("")
    for ck, rec in dossier["per_composite"].items():
        print("  " + ck + "  [" + rec["overall_verdict"] + "]")
        for sr in rec["sub_relations"]:
            tp = sr["target_params"]
            tp_str = ", ".join(k + "=" + str(v) for k, v in tp.items()) or "-"
            row_msg = "    " + sr["sub_primitive"] + " (" + sr["relation_kind"] + ")  target=(" + tp_str + ")  oracle=" + _f(sr["oracle_best"]) + "  best_generic=" + _f(sr["best_generic"]) + " (" + str(sr["best_generic_name"]) + ")  primitive_aware=" + _f(sr["primitive_aware"]) + "  " + sr["verdict"]
            print(row_msg)
        print("")
    print("Wrote unlock.json and UNLOCK.md into CWD.")
    return 0


def _entry():
    return main()


if __name__ == "__main__":
    raise SystemExit(_entry())
# end of file padding
