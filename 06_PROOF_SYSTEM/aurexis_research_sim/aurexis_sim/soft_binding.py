"""Soft-binding / inferred-ROI evaluation (v1.2).

v1.1 measured primitives under a PERFECT ROI mask derived by dilating
truth labels. That is an oracle; a real language decoder would have to
*infer* the ROI, which is bound to be imperfect. v1.2 adds several
imperfect-ROI mode generators and evaluates each composite sub-primitive
under each, producing a robustness verdict:

    ROBUST_TO_SOFT_BINDING   all soft modes >= 0.80
    NEEDS_TIGHT_BINDING      perfect >= 0.80 but >= 1 soft mode < 0.80
    FAILS_EVEN_PERFECT       perfect < 0.80 (inherited from v1.1)

Honest scope:
  - Four soft modes: dilate_extra, erode, shift_px, noisy_mask.
  - Only cardinality and repetition change under ROI; for label-scoped
    relations (ordering, adjacency, role_zone, orientation, hierarchy,
    symmetry) the ROI is ignored by the metric, so bound == soft == unbound
    by construction and is reported as such.
  - Soft modes are deterministic given a seed; noisy_mask uses a fixed
    numpy random generator.
  - "Inference" here is NOT a learned segmenter. It is a synthetic
    corruption of the perfect mask so we can measure metric robustness.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np

from .simulate import SimParams, run_chain
from .sensor import SensorParams
from .interaction import COMPOSITES, INTERACTION_CAPTURE
from .binding import (
    roi_from_labels,
    compute_relation_metric_unbound,
    compute_relation_metric_bound,
    ROBUST_THR,
)


# =========================================================================
# Imperfect ROI mode generators. Each takes the perfect mask and returns
# a modified boolean mask of the same shape.
# =========================================================================

def _dilate(mask: np.ndarray, steps: int) -> np.ndarray:
    m = mask.copy()
    for _ in range(max(0, int(steps))):
        up = np.zeros_like(m);  up[:-1] = m[1:]
        dn = np.zeros_like(m);  dn[1:] = m[:-1]
        lf = np.zeros_like(m);  lf[:, :-1] = m[:, 1:]
        rt = np.zeros_like(m);  rt[:, 1:] = m[:, :-1]
        m = m | up | dn | lf | rt
    return m


def _erode(mask: np.ndarray, steps: int) -> np.ndarray:
    # Erode = NOT(dilate(NOT)) but we do it directly: a pixel stays True
    # only if all 4 neighbors are also True.
    m = mask.copy()
    for _ in range(max(0, int(steps))):
        up = np.ones_like(m);  up[:-1] = m[1:]
        dn = np.ones_like(m);  dn[1:]  = m[:-1]
        lf = np.ones_like(m);  lf[:, :-1] = m[:, 1:]
        rt = np.ones_like(m);  rt[:, 1:]  = m[:, :-1]
        m = m & up & dn & lf & rt
    return m


def _shift(mask: np.ndarray, dy: int, dx: int) -> np.ndarray:
    m = np.zeros_like(mask)
    h, w = mask.shape
    y0 = max(0,  dy); y1 = min(h, h + dy)
    x0 = max(0,  dx); x1 = min(w, w + dx)
    sy0 = max(0, -dy); sy1 = sy0 + (y1 - y0)
    sx0 = max(0, -dx); sx1 = sx0 + (x1 - x0)
    if y1 > y0 and x1 > x0:
        m[y0:y1, x0:x1] = mask[sy0:sy1, sx0:sx1]
    return m


def _noisy(mask: np.ndarray, pct: float, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    flips = rng.random(mask.shape) < float(pct)
    return mask ^ flips


def build_soft_modes(perfect_mask: np.ndarray,
                      size_hint: int = 128,
                      seed: int = 0) -> dict:
    """Return {mode_name: mask} covering perfect + four soft variants."""
    shift_px = max(2, size_hint // 24)
    extra_dilate = max(2, size_hint // 24)
    return {
        "perfect":         perfect_mask,
        "dilate_extra":    _dilate(perfect_mask, extra_dilate),
        "erode":           _erode(perfect_mask, 1),
        "shift_px":        _shift(perfect_mask, 0, shift_px),
        "noisy_10pct":     _noisy(perfect_mask, 0.10, seed=seed),
    }


# =========================================================================
# Verdict
# =========================================================================

def _verdict(unbound: float, perfect: float, soft_scores: dict) -> str:
    ok = lambda x: isinstance(x, float) and x == x
    if not ok(perfect) or perfect < ROBUST_THR:
        return "FAILS_EVEN_PERFECT"
    soft_vals = [v for k, v in soft_scores.items() if k != "perfect" and ok(v)]
    if soft_vals and all(v >= ROBUST_THR for v in soft_vals):
        return "ROBUST_TO_SOFT_BINDING"
    return "NEEDS_TIGHT_BINDING"


# =========================================================================
# Dossier build
# =========================================================================

def build_soft_binding_dossier(size: int = 128, seed: int = 0) -> dict:
    capture = INTERACTION_CAPTURE()
    per_composite = {}
    for comp_kind, builder in COMPOSITES.items():
        pkt = builder(size=size, seed=seed)
        result = run_chain(pkt["image"], capture, seed=seed)
        captured = result["captured"]
        sub_records = []
        for sub in pkt["meta"]["composite"]:
            perfect_mask = roi_from_labels(sub["labels"],
                                             dilate=max(2, size // 32))
            modes = build_soft_modes(perfect_mask, size_hint=size, seed=seed)

            unbound = compute_relation_metric_unbound(sub, captured)
            mode_scores = {
                m: compute_relation_metric_bound(sub, captured, msk)
                for m, msk in modes.items()
            }
            v = _verdict(unbound, mode_scores["perfect"], mode_scores)
            worst_soft = None
            worst_val = None
            for m, val in mode_scores.items():
                if m == "perfect":
                    continue
                if isinstance(val, float) and val == val:
                    if worst_val is None or val < worst_val:
                        worst_val = val; worst_soft = m

            sub_records.append({
                "sub_primitive": sub["name"],
                "relation_kind": sub["relation"]["kind"],
                "unbound_survival": unbound,
                "mode_survival":    mode_scores,
                "worst_soft_mode":  worst_soft,
                "worst_soft_score": worst_val,
                "verdict":          v,
            })

        # Overall: severest verdict (FAILS > NEEDS_TIGHT > ROBUST)
        sev = {"ROBUST_TO_SOFT_BINDING": 0,
               "NEEDS_TIGHT_BINDING": 1,
               "FAILS_EVEN_PERFECT": 2}
        worst = max((sr["verdict"] for sr in sub_records),
                    key=lambda t: sev.get(t, -1))
        per_composite[comp_kind] = {
            "sub_relations": sub_records,
            "overall_verdict": worst,
        }
    return {
        "schema_version": "1.2",
        "interaction_capture": capture.as_dict(),
        "thresholds": {"robust_thr": ROBUST_THR},
        "soft_modes": ["perfect", "dilate_extra", "erode",
                       "shift_px", "noisy_10pct"],
        "per_composite": per_composite,
    }


def write_soft_binding_reports(out_dir: Path,
                                dossier: Optional[dict] = None) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dossier = dossier or build_soft_binding_dossier()

    with open(out_dir / "soft_binding.json", "w", encoding="utf-8") as f:
        json.dump(dossier, f, indent=2)

    modes = dossier["soft_modes"]
    lines = ["# Aurexis Research Sim v1.2 - Soft-binding dossier", ""]
    lines.append("For each composite sub-primitive we evaluate under the")
    lines.append("perfect ROI (v1.1) plus four imperfect-ROI modes:")
    lines.append("")
    for m in modes:
        lines.append("- `" + m + "`")
    lines.append("")
    lines.append("Verdict:")
    lines.append("- **ROBUST_TO_SOFT_BINDING**  all soft modes >= {:.2f}".format(ROBUST_THR))
    lines.append("- **NEEDS_TIGHT_BINDING**     perfect passes, at least one soft mode < {:.2f}".format(ROBUST_THR))
    lines.append("- **FAILS_EVEN_PERFECT**      perfect < {:.2f} (from v1.1)".format(ROBUST_THR))
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
        header = ["sub", "kind", "unbound"] + modes + \
                 ["worst_soft_mode", "worst_soft_score", "verdict"]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join(["---"] * len(header)) + "|")
        for sr in rec["sub_relations"]:
            def _f(v):
                return "n/a" if not (isinstance(v, float) and v == v) \
                       else "{:.3f}".format(v)
            row = [sr["sub_primitive"], sr["relation_kind"],
                   _f(sr["unbound_survival"])]
            for m in modes:
                row.append(_f(sr["mode_survival"].get(m, float("nan"))))
            row.append(str(sr["worst_soft_mode"]))
            row.append(_f(sr["worst_soft_score"]))
            row.append(sr["verdict"])
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")

    with open(out_dir / "SOFT_BINDING.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return dossier


def main():
    dossier = build_soft_binding_dossier()
    out = Path.cwd()
    write_soft_binding_reports(out, dossier)
    print("Aurexis Research Sim v1.2 - Soft-binding dossier\n")
    for ck, rec in dossier["per_composite"].items():
        print("  " + ck + "  [overall: " + rec["overall_verdict"] + "]")
        for sr in rec["sub_relations"]:
            u = sr["unbound_survival"]; perfect = sr["mode_survival"].get("perfect")
            us = "n/a" if not (isinstance(u, float) and u == u) else "{:.3f}".format(u)
            ps = "n/a" if not (isinstance(perfect, float) and perfect == perfect) else "{:.3f}".format(perfect)
            worst_m = sr["worst_soft_mode"]; worst_v = sr["worst_soft_score"]
            ws = "n/a" if not (isinstance(worst_v, float) and worst_v == worst_v) else "{:.3f}".format(worst_v)
            print("      {:<12} ({:<11}) unbound={}  perfect={}  worst_soft={}@{}  {}".format(
                sr["sub_primitive"], sr["relation_kind"],
                us, ps, ws, str(worst_m), sr["verdict"]))
        print()
    print("Wrote soft_binding.json and SOFT_BINDING.md into CWD.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
