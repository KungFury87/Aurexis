"""Inferred-binding / proposal-realism evaluation (v1.3).

v1.2 corrupted a truth-derived ROI. v1.3 goes one step closer to the
real thing: two tiny image-only proposal generators that do NOT see
the truth labels. They compute an ROI mask from the captured image
alone. The suite then evaluates each composite sub-primitive under:

    unbound           v1.0 global metric, no ROI
    perfect           v1.1 ROI from truth labels (dilated)
    soft_worst        v1.2 worst-soft corruption of the perfect mask
    propose_threshold v1.3 image-only luma-threshold proposal
    propose_edges     v1.3 image-only Sobel-gradient proposal

Per sub-primitive verdict:

    SURVIVES_WITH_INFERENCE    best_inferred >= 0.80
    NEEDS_TIGHT_INFERENCE      perfect >= 0.80 but best_inferred < 0.80
    FAILS_EVEN_PERFECT         perfect < 0.80 (inherited)

Honest scope:
  - Two proposals, both deterministic, image-only, no learning.
  - Dilation is fixed-radius; no adaptive region merging.
  - Label-scoped relations (ordering, adjacency, role_zone, ...)
    are unaffected by ROI and are reported unchanged for reference.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np

from .simulate import SimParams, run_chain, _convolve2d
from .sensor import SensorParams
from .interaction import COMPOSITES, INTERACTION_CAPTURE
from .binding import (
    roi_from_labels,
    compute_relation_metric_unbound,
    compute_relation_metric_bound,
    ROBUST_THR,
)
from .soft_binding import build_soft_modes
from .relations import _lum


# =========================================================================
# Image-only ROI proposal generators.
# These take ONLY the captured image and return a boolean mask.
# =========================================================================

def _dilate_bool(mask: np.ndarray, steps: int) -> np.ndarray:
    m = mask.copy()
    for _ in range(max(0, int(steps))):
        up = np.zeros_like(m);  up[:-1] = m[1:]
        dn = np.zeros_like(m);  dn[1:]  = m[:-1]
        lf = np.zeros_like(m);  lf[:, :-1] = m[:, 1:]
        rt = np.zeros_like(m);  rt[:, 1:]  = m[:, :-1]
        m = m | up | dn | lf | rt
    return m


def propose_threshold(captured: np.ndarray, thr_k: float = 1.5,
                       dilate: int = 3) -> np.ndarray:
    """Bright-region proposal: luma > mean + thr_k * std, then dilate."""
    c = _lum(captured)
    thr = float(c.mean() + thr_k * c.std())
    mask = c > max(thr, float(c.mean()) + 0.1)
    return _dilate_bool(mask, dilate)


def propose_edges(captured: np.ndarray, thr_k: float = 1.0,
                   dilate: int = 5) -> np.ndarray:
    """Edge-region proposal: Sobel gradient magnitude thresholded, dilated."""
    c = _lum(captured)
    kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
    ky = kx.T
    gx = _convolve2d(c, kx)
    gy = _convolve2d(c, ky)
    g = np.sqrt(gx * gx + gy * gy)
    if g.max() <= 1e-9:
        return np.zeros_like(c, dtype=bool)
    thr = float(g.mean() + thr_k * g.std())
    mask = g > thr
    return _dilate_bool(mask, dilate)


PROPOSALS = {
    "propose_threshold": propose_threshold,
    "propose_edges":     propose_edges,
}


# =========================================================================
# Verdict
# =========================================================================

def _verdict(perfect: float, inferred_scores: dict) -> str:
    ok = lambda x: isinstance(x, float) and x == x
    if not ok(perfect) or perfect < ROBUST_THR:
        return "FAILS_EVEN_PERFECT"
    best = None
    for v in inferred_scores.values():
        if ok(v):
            best = v if best is None else max(best, v)
    if best is not None and best >= ROBUST_THR:
        return "SURVIVES_WITH_INFERENCE"
    return "NEEDS_TIGHT_INFERENCE"


# =========================================================================
# Dossier build
# =========================================================================

def build_inferred_binding_dossier(size: int = 128, seed: int = 0) -> dict:
    capture = INTERACTION_CAPTURE()
    per_composite = {}
    for comp_kind, builder in COMPOSITES.items():
        pkt = builder(size=size, seed=seed)
        result = run_chain(pkt["image"], capture, seed=seed)
        captured = result["captured"]

        sub_records = []
        for sub in pkt["meta"]["composite"]:
            # v1.0 unbound
            unbound = compute_relation_metric_unbound(sub, captured)

            # v1.1 perfect ROI
            perfect_mask = roi_from_labels(sub["labels"],
                                             dilate=max(2, size // 32))
            perfect = compute_relation_metric_bound(sub, captured, perfect_mask)

            # v1.2 worst-soft score
            soft_modes = build_soft_modes(perfect_mask, size_hint=size, seed=seed)
            soft_worst = None
            for mname, msk in soft_modes.items():
                if mname == "perfect":
                    continue
                v = compute_relation_metric_bound(sub, captured, msk)
                if isinstance(v, float) and v == v:
                    soft_worst = v if soft_worst is None else min(soft_worst, v)

            # v1.3 image-only proposals
            inferred_scores = {}
            for pname, propose in PROPOSALS.items():
                try:
                    mask = propose(captured)
                except Exception:
                    mask = np.ones_like(perfect_mask)
                inferred_scores[pname] = compute_relation_metric_bound(
                    sub, captured, mask)

            best_inferred = None
            best_proposal = None
            for pname, v in inferred_scores.items():
                if isinstance(v, float) and v == v:
                    if best_inferred is None or v > best_inferred:
                        best_inferred = v; best_proposal = pname

            verdict = _verdict(perfect, inferred_scores)

            sub_records.append({
                "sub_primitive":   sub["name"],
                "relation_kind":   sub["relation"]["kind"],
                "unbound":         unbound,
                "perfect":         perfect,
                "soft_worst":      soft_worst,
                "inferred":        inferred_scores,
                "best_inferred":   best_inferred,
                "best_proposal":   best_proposal,
                "verdict":         verdict,
            })

        severities = {"SURVIVES_WITH_INFERENCE": 0,
                      "NEEDS_TIGHT_INFERENCE":   1,
                      "FAILS_EVEN_PERFECT":      2}
        worst = max((sr["verdict"] for sr in sub_records),
                    key=lambda v: severities.get(v, -1))
        per_composite[comp_kind] = {
            "sub_relations":   sub_records,
            "overall_verdict": worst,
        }

    return {
        "schema_version": "1.3",
        "interaction_capture": capture.as_dict(),
        "proposals": list(PROPOSALS.keys()),
        "thresholds": {"robust_thr": ROBUST_THR},
        "per_composite": per_composite,
    }


def write_inferred_binding_reports(out_dir: Path,
                                    dossier: Optional[dict] = None) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dossier = dossier or build_inferred_binding_dossier()

    with open(out_dir / "inferred_binding.json", "w", encoding="utf-8") as f:
        json.dump(dossier, f, indent=2)

    proposals = dossier["proposals"]
    lines = ["# Aurexis Research Sim v1.3 - Inferred-binding dossier", ""]
    lines.append("Each composite sub-primitive is evaluated under:")
    lines.append("- `unbound` (v1.0 global metric)")
    lines.append("- `perfect` (v1.1 ROI from truth labels, dilated)")
    lines.append("- `soft_worst` (v1.2 worst imperfect mode)")
    for p in proposals:
        lines.append("- `" + p + "` (v1.3 image-only proposal)")
    lines.append("")
    lines.append("Verdict:")
    lines.append("- **SURVIVES_WITH_INFERENCE** best inferred >= {:.2f}".format(ROBUST_THR))
    lines.append("- **NEEDS_TIGHT_INFERENCE** perfect passes but inferred < {:.2f}".format(ROBUST_THR))
    lines.append("- **FAILS_EVEN_PERFECT** perfect < {:.2f}".format(ROBUST_THR))
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
        header = ["sub", "kind", "unbound", "perfect", "soft_worst"] + proposals + \
                 ["best_proposal", "best_inferred", "verdict"]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join(["---"] * len(header)) + "|")
        for sr in rec["sub_relations"]:
            def _f(v):
                return "n/a" if not (isinstance(v, float) and v == v) \
                       else "{:.3f}".format(v)
            row = [sr["sub_primitive"], sr["relation_kind"],
                   _f(sr["unbound"]), _f(sr["perfect"]), _f(sr["soft_worst"])]
            for p in proposals:
                row.append(_f(sr["inferred"].get(p, float("nan"))))
            row.append(str(sr["best_proposal"]))
            row.append(_f(sr["best_inferred"]))
            row.append(sr["verdict"])
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")

    with open(out_dir / "INFERRED_BINDING.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return dossier


def main():
    dossier = build_inferred_binding_dossier()
    out = Path.cwd()
    write_inferred_binding_reports(out, dossier)
    print("Aurexis Research Sim v1.3 - Inferred-binding dossier\n")
    for ck, rec in dossier["per_composite"].items():
        print("  " + ck + "  [overall: " + rec["overall_verdict"] + "]")
        for sr in rec["sub_relations"]:
            def _s(v):
                return "n/a" if not (isinstance(v, float) and v == v) else "{:.3f}".format(v)
            p_str = ", ".join(k + "=" + _s(v)
                              for k, v in sr["inferred"].items())
            print("      {:<12} ({:<11}) unbound={}  perfect={}  soft_worst={}  {}  best={}@{}  {}".format(
                sr["sub_primitive"], sr["relation_kind"],
                _s(sr["unbound"]), _s(sr["perfect"]), _s(sr["soft_worst"]),
                p_str, _s(sr["best_inferred"]), str(sr["best_proposal"]),
                sr["verdict"]))
        print()
    print("Wrote inferred_binding.json and INFERRED_BINDING.md into CWD.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
