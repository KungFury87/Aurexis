"""Arbitration-boundary mapping / ROI-sensitive role-zone (v1.9).

v1.8 confirmed primitive-aware target-conditioned arbitration helps
for two primitive families (cardinality, repetition). Label-scoped
primitives - ordering, adjacency, role_zone, orientation, hierarchy,
symmetry - were tagged ARBITRATION_INVARIANT, but that single tag
hid an important distinction:

  - ARBITRATION_INVARIANT: this primitive's metric is genuinely
    ROI-insensitive (no ROI choice changes the score) AND we believe
    that's correct (the primitive doesn't depend on ROI selection).
  - METRIC_GAP_ROI_INSENSITIVE: this primitive's metric is currently
    label-scoped and ignores ROI, but a real arbitration test could
    matter - we just have not built an ROI-aware variant of the
    metric yet, so we cannot answer.

v1.9 introduces an ROI-sensitive role_zone metric, a role_zone
distractor composite, and a cross-family boundary map that uses the
clearer verdict scheme above. role_zone moves from
METRIC_GAP_ROI_INSENSITIVE in v1.8 to PRIMITIVE_AWARE_HELPS in v1.9.
The other label-scoped families remain METRIC_GAP_ROI_INSENSITIVE
because their metrics are still ROI-insensitive - that is now an
honest, surgical bottleneck description.

Verdicts (per composite):

    PROPOSAL_QUALITY_LIMIT           oracle_best < 0.80
    ARBITRATION_INVARIANT             primitive metric is genuinely
                                       ROI-insensitive by construction
    METRIC_GAP_ROI_INSENSITIVE        metric is currently label-scoped;
                                       ROI-aware variant not built yet;
                                       arbitration test not possible
    GENERIC_FUSION_SUFFICIENT         best generic ranker passes
    PRIMITIVE_AWARE_HELPS             only primitive-aware passes
    PRIMITIVE_AWARE_STILL_FAILS       oracle passes; both fail

Family-level boundary map aggregates per-composite verdicts to give
a single arbitration-sensitivity tag per primitive family.

Honest scope (v1.9 still NOT claiming):
  - role_zone is the ONLY label-scoped family that gains an ROI-aware
    metric in this pass. ordering / adjacency / symmetry / orientation
    / hierarchy remain METRIC_GAP_ROI_INSENSITIVE.
  - The role_zone ROI metric is intentionally simple: threshold inside
    ROI, find components, anchor = brightest component (>= 10% above
    next-brightest mean), satellites = others, score by satellite
    count vs target. No spatial-arrangement scoring, no anchor-radius
    inference, no abstain.
  - The strip-based repetition fix from v1.8 carries forward
    unchanged.
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
from .distractor_arbitration import (
    DISTRACTOR_COMPOSITES, RANKERS as SINGLE_RANKERS,
)
from .fusion import FUSED_RANKERS
from .primitive_aware import (
    rank_by_cardinality_target,
    best_generic_top1 as _best_generic_top1,
)
from .coverage import (
    COVERAGE_COMPOSITES,
    repetition_survival_bound_strip,
    rank_by_repetition_target_strip,
)
from .relations import _lum


# -------------------------------------------------------------------
# ROI-sensitive role_zone metric
# -------------------------------------------------------------------

def role_zone_survival_bound(truth_pkt, captured, roi_mask,
                              target_satellites=None):
    """Score a candidate ROI as a role_zone scene.

    Within the ROI, threshold the captured image and find components.
    The brightest component is the anchor candidate. It must be at
    least 10% brighter than the next-brightest component to count as a
    clear anchor. The remaining components are satellites. Score is
    `1 - |satellites - target|/max(1, target)`, clamped to [0, 1].

    Returns 0.0 if the ROI does not contain a clear anchor or has no
    components above threshold.
    """
    rel = truth_pkt["meta"].get("relation", {})
    target = rel.get("target_satellites", target_satellites)
    if target is None:
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
    if not components:
        return 0.0

    means = [float(lum[c].mean()) for c in components]
    anchor_idx = int(np.argmax(means))
    anchor_mean = means[anchor_idx]
    others = [m for i, m in enumerate(means) if i != anchor_idx]

    if not others:
        # Only one component -> no satellites
        return 1.0 if target == 0 else 0.0

    if anchor_mean < max(others) * 1.10:
        # Anchor is not clearly brightest
        return 0.0

    n_satellites = len(components) - 1
    return float(max(0.0, 1.0 - abs(n_satellites - target) / max(1, target)))


def rank_by_role_zone_target(cands, captured, target_satellites):
    """Rank candidates by role_zone_survival_bound against a known
    target_satellites count."""
    if not cands or target_satellites is None:
        return []
    target = int(target_satellites)
    scores = []
    for c in cands:
        pkt = {"meta": {"relation": {"kind": "role_zone",
                                       "target_satellites": target}}}
        s = role_zone_survival_bound(pkt, captured, c,
                                       target_satellites=target)
        scores.append(float(s) if isinstance(s, float) and s == s else 0.0)
    return sorted(range(len(cands)), key=lambda i: -scores[i])


# -------------------------------------------------------------------
# Role-zone distractor composite
# -------------------------------------------------------------------

def composite_role_zone_decoy(size: int = 192, seed: int = 0) -> dict:
    """Intended: 1 bright anchor at center of a small region with 4
    dimmer satellites at compass points. Decoy: 5 markers of the SAME
    brightness arranged in a row elsewhere - no anchor structure.
    Generic rankers favor the decoy (more total bright pixels, larger
    merged candidate); the ROI-aware role_zone metric demands a clear
    anchor and rejects the decoy."""
    img = np.full((size, size), 0.15, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    yy, xx = np.mgrid[0:size, 0:size]

    # Intended: anchor + 4 satellites
    anc_y = int(size * 0.70)
    anc_x = int(size * 0.30)
    r_anc = max(5, size // 28)
    r_sat = max(4, size // 36)
    radius = max(20, size // 8)
    # Anchor (bright)
    m = (yy - anc_y) ** 2 + (xx - anc_x) ** 2 <= r_anc * r_anc
    img[m] = 0.85
    lab[m] = 1
    # 4 satellites at N, S, E, W (dimmer)
    for i, (dy, dx) in enumerate([(-radius, 0), (radius, 0),
                                    (0, -radius), (0, radius)]):
        cy = anc_y + dy; cx = anc_x + dx
        m = (yy - cy) ** 2 + (xx - cx) ** 2 <= r_sat * r_sat
        img[m] = 0.50
        lab[m] = 2 + i
    rz_labels = np.where((lab >= 1) & (lab <= 5), lab, 0).astype(np.int32)

    # Decoy: 5 markers, all SAME brightness, in a row
    dec_y = int(size * 0.25)
    r_dec = max(7, size // 22)
    n_dec = 5
    p_dec = max(15, size // 12)
    x0 = int(size * 0.40)
    for i in range(n_dec):
        cx = x0 + i * p_dec
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
            "relation": {"kind": "composite", "parts": ["role_zone"]},
            "composite": [
                {"name": "role_zone",
                 "labels": rz_labels,
                 "relation": {"kind": "role_zone",
                              "target_satellites": 4}},
            ],
        },
    }


BOUNDARY_COMPOSITES: Dict[str, Callable[..., dict]] = {
    **COVERAGE_COMPOSITES,
    "composite_role_zone_decoy": composite_role_zone_decoy,
}


# -------------------------------------------------------------------
# Verdicts
# -------------------------------------------------------------------

# Label-scoped families whose existing metric is ROI-insensitive AND
# for which v1.9 has NOT introduced an ROI-aware variant. role_zone
# is intentionally NOT in this set in v1.9 - it has the new ROI-aware
# metric.
LABEL_SCOPED_NO_ROI = {"ordering", "adjacency", "symmetry",
                        "orientation", "hierarchy"}


def _per_composite_verdict(oracle_best, best_generic, target_aware,
                            relation_kind):
    ok = lambda x: isinstance(x, float) and x == x
    if not ok(oracle_best) or oracle_best < ROBUST_THR:
        return "PROPOSAL_QUALITY_LIMIT"
    if relation_kind in LABEL_SCOPED_NO_ROI:
        return "METRIC_GAP_ROI_INSENSITIVE"
    target_ok = ok(target_aware) and target_aware >= ROBUST_THR
    generic_ok = ok(best_generic) and best_generic >= ROBUST_THR
    if generic_ok:
        return "GENERIC_FUSION_SUFFICIENT"
    if target_ok:
        return "PRIMITIVE_AWARE_HELPS"
    return "PRIMITIVE_AWARE_STILL_FAILS"


def _family_verdict(per_composite_verdicts):
    """Aggregate per-composite verdicts for one family into a single
    family-level boundary tag.
    Order of preference (best news first):
      PRIMITIVE_AWARE_HELPS > GENERIC_FUSION_SUFFICIENT >
      PRIMITIVE_AWARE_STILL_FAILS > PROPOSAL_QUALITY_LIMIT >
      METRIC_GAP_ROI_INSENSITIVE > ARBITRATION_INVARIANT
    """
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
# Per-candidate scoring helpers
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
    return target_top1, target_idx, target_params


# -------------------------------------------------------------------
# Dossier
# -------------------------------------------------------------------

def build_boundary_dossier(size: int = 192, seed: int = 0) -> dict:
    capture = INTERACTION_CAPTURE()
    per_composite: Dict[str, dict] = {}

    for comp_kind, builder in BOUNDARY_COMPOSITES.items():
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
                "label_scoped":      kind in LABEL_SCOPED_NO_ROI,
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

    # Cross-family boundary map
    family_to_verdicts: Dict[str, List[str]] = {}
    for ck, rec in per_composite.items():
        for sr in rec["sub_relations"]:
            family_to_verdicts.setdefault(sr["relation_kind"], []).append(
                sr["verdict"])
    # Add label-scoped families that have no composite tested in v1.9
    for fam in LABEL_SCOPED_NO_ROI:
        family_to_verdicts.setdefault(fam, ["METRIC_GAP_ROI_INSENSITIVE"])

    family_map = {}
    for fam, verdicts in sorted(family_to_verdicts.items()):
        family_map[fam] = {
            "per_composite_verdicts": verdicts,
            "boundary_tag": _family_verdict(verdicts),
        }

    return {
        "schema_version": "1.9",
        "interaction_capture": capture.as_dict(),
        "single_rankers": list(SINGLE_RANKERS.keys()),
        "fused_rankers":  list(FUSED_RANKERS.keys()),
        "primitive_aware_rankers": ["cardinality_target",
                                     "repetition_target_strip",
                                     "role_zone_target"],
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


def write_boundary_reports(out_dir: Path,
                            dossier: Optional[dict] = None) -> dict:
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    dossier = dossier or build_boundary_dossier()

    with open(out_dir / "boundary.json", "w", encoding="utf-8") as f:
        json.dump(_scrub(dossier), f, indent=2)

    L = []
    L.append("# Aurexis Research Sim v1.9 - Arbitration-boundary mapping dossier")
    L.append("")
    L.append("v1.7 demonstrated target-conditioned cardinality scoring.")
    L.append("v1.8 added a strip-based fix and showed primitive-aware arbitration")
    L.append("helps for repetition too. v1.9 introduces an ROI-sensitive role_zone")
    L.append("metric and maps where target conditioning helps, where it does not,")
    L.append("and where the metric itself is the bottleneck.")
    L.append("")
    L.append("Verdict (per composite):")
    L.append("- **GENERIC_FUSION_SUFFICIENT**    best generic ranker passes")
    L.append("- **PRIMITIVE_AWARE_HELPS**        only primitive-aware passes")
    L.append("- **PRIMITIVE_AWARE_STILL_FAILS**  oracle passes; both fail")
    L.append("- **PROPOSAL_QUALITY_LIMIT**       oracle_best < {:.2f}".format(ROBUST_THR))
    L.append("- **METRIC_GAP_ROI_INSENSITIVE**   metric is label-scoped; no ROI-aware variant; arbitration test not possible")
    L.append("- **ARBITRATION_INVARIANT**        primitive metric is genuinely ROI-insensitive (not used in v1.9)")
    L.append("")

    # Family boundary map (top-level summary)
    L.append("## Family boundary map")
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

    with open(out_dir / "BOUNDARY.md", "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return dossier


def main():
    dossier = build_boundary_dossier()
    write_boundary_reports(Path.cwd(), dossier)
    print("Aurexis Research Sim v1.9 - Boundary dossier")
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
            print("    " + sr["sub_primitive"]
                  + " (" + sr["relation_kind"] + ")"
                  + "  target=(" + tp_str + ")"
                  + "  oracle=" + _f(sr["oracle_best"])
                  + "  best_generic=" + _f(sr["best_generic"])
                  + " (" + str(sr["best_generic_name"]) + ")"
                  + "  primitive_aware=" + _f(sr["primitive_aware"])
                  + "  " + sr["verdict"])
        print("")
    print("Wrote boundary.json and BOUNDARY.md into CWD.")
    return 0


def _entry():
    return main()


if __name__ == "__main__":
    raise SystemExit(_entry())
# end of file padding
