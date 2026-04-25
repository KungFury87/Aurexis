"""Scene-scoped binding / ROI-aware evaluation (v1.1).

v1.0 measured interference in composites but couldn't tell whether a
primitive was fundamentally broken in context or just the metric was
scene-blind (counting markers outside the intended region, reading
repetition across the wrong band, etc.).

v1.1 adds ROI-aware variants of the metrics that actually benefit
(cardinality, repetition) plus a bound-vs-unbound dossier:

    SURVIVES_GLOBAL    both bound and unbound survive: primitive is
                       robust even without explicit region binding
    NEEDS_BINDING      unbound fails but bound survives: metric was
                       scene-blind, primitive is fine with an ROI
    FAILS_EVEN_BOUND   even with ROI the primitive fails: primitive
                       is the problem, not the metric scope
    SCENE_AMBIGUITY    (bound - unbound) >= 0.30 tag: flags that
                       scene scope dominates the difference
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np

from . import truth as truth_mod
from .simulate import SimParams, run_chain
from .sensor import SensorParams
from .relations import (
    compute_relation_metrics,
    _count_components,
    _lum,
)
from .interaction import COMPOSITES, INTERACTION_CAPTURE


ROBUST_THR = 0.80
BINDING_BOOST = 0.30


# =========================================================================
# ROI extraction
# =========================================================================

def roi_from_labels(labels: np.ndarray, dilate: int = 4) -> np.ndarray:
    """Return a boolean mask covering the labeled region plus a small
    dilation (4-connected). 0 labels are background."""
    mask = labels > 0
    for _ in range(max(0, int(dilate))):
        up = np.zeros_like(mask);    up[:-1] = mask[1:]
        dn = np.zeros_like(mask);    dn[1:] = mask[:-1]
        lf = np.zeros_like(mask);    lf[:, :-1] = mask[:, 1:]
        rt = np.zeros_like(mask);    rt[:, 1:] = mask[:, :-1]
        mask = mask | up | dn | lf | rt
    return mask


# =========================================================================
# ROI-aware metrics
# =========================================================================

def cardinality_survival_bound(truth_pkt, captured, roi_mask):
    """Count connected components above threshold ONLY within the
    ROI mask. Compare to truth count."""
    rel = truth_pkt["meta"].get("relation", {})
    if rel.get("kind") != "cardinality":
        return float("nan")
    n = int(rel.get("count", 0))
    if n <= 0:
        return float("nan")
    c = _lum(captured)
    thr = float(c.mean() + 2.0 * c.std())
    binary = (c > max(thr, float(c.mean()) + 0.15)) & roi_mask
    detected = _count_components(binary)
    err = abs(detected - n) / float(n)
    return float(max(0.0, 1.0 - err))


def repetition_survival_bound(truth_pkt, captured, roi_mask):
    """Autocorrelate the captured-luma row only across ROI columns at
    row_y. If the peak near the declared period dominates the nontrivial
    lags, the relation survives."""
    rel = truth_pkt["meta"].get("relation", {})
    if rel.get("kind") != "repetition":
        return float("nan")
    row_y = int(rel.get("row_y", 0))
    period = float(rel.get("period_px", 0.0))
    if period <= 1.0:
        return float("nan")
    c = _lum(captured)
    if row_y < 0 or row_y >= c.shape[0]:
        return float("nan")
    row = c[row_y].astype(np.float64)
    col_mask = roi_mask[row_y] if roi_mask.ndim == 2 else roi_mask
    if col_mask.sum() < 8:
        # Fall back to full row if ROI is too narrow
        prof = row.copy()
    else:
        prof = row[col_mask]
    prof = prof - prof.mean()
    if prof.std() < 1e-9:
        return 0.0
    n = prof.size
    ac = np.correlate(prof, prof, mode="full")[n - 1:]
    max_lag = n // 2
    if max_lag < 5:
        return float("nan")
    nontrivial = ac[1:max_lag + 1]
    if nontrivial.max() <= 0:
        return 0.0
    nt = nontrivial / nontrivial.max()
    target = int(round(period))
    if target < 1 or target > max_lag:
        return 0.0
    lo = max(1, target - 2); hi = min(max_lag, target + 2)
    return float(np.clip(nt[lo - 1:hi].max(), 0.0, 1.0))


# =========================================================================
# Bound dispatcher
# =========================================================================

def compute_relation_metric_bound(sub_pkt: dict, captured: np.ndarray,
                                    roi_mask: np.ndarray) -> float:
    """ROI-aware relation metric. For label-scoped relations (ordering,
    adjacency, orientation, hierarchy, role_zone) binding doesn't
    change anything because the metric already scopes by labels; we
    fall through to the unbound path. For cardinality and repetition
    we use the bound variants."""
    rel = sub_pkt.get("meta", {}).get("relation") or \
          sub_pkt.get("relation", {})
    kind = rel.get("kind")
    if kind == "cardinality":
        pkt = {"image": captured, "labels": sub_pkt.get("labels"),
               "meta": {"relation": rel}}
        return cardinality_survival_bound(pkt, captured, roi_mask)
    if kind == "repetition":
        pkt = {"image": captured, "labels": sub_pkt.get("labels"),
               "meta": {"relation": rel}}
        return repetition_survival_bound(pkt, captured, roi_mask)
    # All other kinds are already ROI-scoped via labels.
    pkt = {"image": captured, "labels": sub_pkt.get("labels"),
           "meta": {"relation": rel}}
    m = compute_relation_metrics(pkt, captured)
    v = m.get("relation_survival", float("nan"))
    return float(v) if isinstance(v, float) and v == v else float("nan")


def compute_relation_metric_unbound(sub_pkt: dict,
                                      captured: np.ndarray) -> float:
    """v1.0 path: no ROI. Use global metric."""
    rel = sub_pkt.get("meta", {}).get("relation") or \
          sub_pkt.get("relation", {})
    pkt = {"image": captured, "labels": sub_pkt.get("labels"),
           "meta": {"relation": rel}}
    m = compute_relation_metrics(pkt, captured)
    v = m.get("relation_survival", float("nan"))
    return float(v) if isinstance(v, float) and v == v else float("nan")


# =========================================================================
# Verdicts
# =========================================================================

def _verdict(unbound: float, bound: float) -> str:
    ok = lambda x: isinstance(x, float) and x == x
    if not (ok(unbound) and ok(bound)):
        return "UNKNOWN"
    if unbound >= ROBUST_THR and bound >= ROBUST_THR:
        return "SURVIVES_GLOBAL"
    if unbound < ROBUST_THR and bound >= ROBUST_THR:
        return "NEEDS_BINDING"
    if bound < ROBUST_THR:
        return "FAILS_EVEN_BOUND"
    return "UNKNOWN"


def _scene_ambiguity(unbound: float, bound: float) -> bool:
    ok = lambda x: isinstance(x, float) and x == x
    if not (ok(unbound) and ok(bound)):
        return False
    return (bound - unbound) >= BINDING_BOOST


# =========================================================================
# Dossier build
# =========================================================================

def build_binding_dossier(size: int = 128, seed: int = 0) -> dict:
    capture = INTERACTION_CAPTURE()
    per_composite = {}
    for comp_kind, builder in COMPOSITES.items():
        pkt = builder(size=size, seed=seed)
        result = run_chain(pkt["image"], capture, seed=seed)
        captured = result["captured"]
        sub_records = []
        for sub in pkt["meta"]["composite"]:
            roi = roi_from_labels(sub["labels"], dilate=max(2, size // 32))
            unbound = compute_relation_metric_unbound(sub, captured)
            bound = compute_relation_metric_bound(sub, captured, roi)
            verdict = _verdict(unbound, bound)
            tags = []
            if _scene_ambiguity(unbound, bound):
                tags.append("SCENE_AMBIGUITY")
            sub_records.append({
                "sub_primitive": sub["name"],
                "relation_kind": sub["relation"]["kind"],
                "unbound_survival": unbound,
                "bound_survival":   bound,
                "binding_boost":    (float(bound - unbound)
                                      if isinstance(bound, float) and bound == bound
                                      and isinstance(unbound, float) and unbound == unbound
                                      else float("nan")),
                "verdict": verdict,
                "tags":    tags,
            })
        # Overall: worst verdict across sub_records
        severities = {"SURVIVES_GLOBAL": 0, "NEEDS_BINDING": 1,
                      "FAILS_EVEN_BOUND": 2, "UNKNOWN": -1}
        worst = max((sr["verdict"] for sr in sub_records),
                    key=lambda v: severities.get(v, -1))
        per_composite[comp_kind] = {
            "sub_relations": sub_records,
            "overall_verdict": worst,
        }
    return {
        "schema_version": "1.1",
        "interaction_capture": capture.as_dict(),
        "thresholds": {
            "robust_thr": ROBUST_THR,
            "binding_boost_tag_threshold": BINDING_BOOST,
        },
        "per_composite": per_composite,
    }


def write_binding_reports(out_dir: Path,
                           dossier: Optional[dict] = None) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dossier = dossier or build_binding_dossier()

    with open(out_dir / "binding.json", "w", encoding="utf-8") as f:
        json.dump(dossier, f, indent=2)

    lines = ["# Aurexis Research Sim v1.1 - Scene-scoped binding dossier", ""]
    lines.append("For each composite sub-primitive we report survival")
    lines.append("WITHOUT ROI binding (v1.0 global metric) and WITH ROI")
    lines.append("binding (mask derived from sub-labels). Verdict:")
    lines.append("")
    lines.append("- **SURVIVES_GLOBAL** both pass: primitive is robust even unbound.")
    lines.append("- **NEEDS_BINDING** unbound fails, bound passes: metric was scene-blind.")
    lines.append("- **FAILS_EVEN_BOUND** primitive fails even with ROI: primitive is the problem.")
    lines.append("- Tag **SCENE_AMBIGUITY** when bound - unbound >= {:.2f}.".format(BINDING_BOOST))
    lines.append("")

    lines.append("## Overall summary")
    lines.append("| composite | overall verdict |")
    lines.append("|-----------|-----------------|")
    for ck, rec in dossier["per_composite"].items():
        lines.append("| {} | **{}** |".format(ck, rec["overall_verdict"]))
    lines.append("")

    for ck, rec in dossier["per_composite"].items():
        lines.append("### " + ck)
        lines.append("- overall_verdict: **" + rec["overall_verdict"] + "**")
        lines.append("| sub_primitive | kind | unbound | bound | binding_boost | verdict | tags |")
        lines.append("|---------------|------|---------|-------|---------------|---------|------|")
        for sr in rec["sub_relations"]:
            def _f(v):
                return "n/a" if not (isinstance(v, float) and v == v) else "{:.3f}".format(v)
            def _fs(v):
                return "n/a" if not (isinstance(v, float) and v == v) else "{:+.3f}".format(v)
            lines.append("| {} | {} | {} | {} | {} | {} | {} |".format(
                sr["sub_primitive"], sr["relation_kind"],
                _f(sr["unbound_survival"]), _f(sr["bound_survival"]),
                _fs(sr["binding_boost"]), sr["verdict"],
                ", ".join(sr["tags"]) if sr["tags"] else ""))
        lines.append("")

    with open(out_dir / "BINDING.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return dossier


def main():
    dossier = build_binding_dossier()
    out = Path.cwd()
    write_binding_reports(out, dossier)
    print("Aurexis Research Sim v1.1 - Scene-scoped binding dossier\n")
    for ck, rec in dossier["per_composite"].items():
        print("  " + ck + "  [overall: " + rec["overall_verdict"] + "]")
        for sr in rec["sub_relations"]:
            u = sr["unbound_survival"]; b = sr["bound_survival"]
            bb = sr["binding_boost"]
            us = "n/a" if not (isinstance(u, float) and u == u) else "{:.3f}".format(u)
            bs = "n/a" if not (isinstance(b, float) and b == b) else "{:.3f}".format(b)
            bbs = "n/a" if not (isinstance(bb, float) and bb == bb) else "{:+.3f}".format(bb)
            tagstr = (" [" + ",".join(sr["tags"]) + "]") if sr["tags"] else ""
            print("      {:<12} ({:<11}) unbound={}  bound={}  boost={}  {}{}".format(
                sr["sub_primitive"], sr["relation_kind"],
                us, bs, bbs, sr["verdict"], tagstr))
        print()
    print("Wrote binding.json and BINDING.md into CWD.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
