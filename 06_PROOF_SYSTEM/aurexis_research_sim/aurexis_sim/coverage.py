"""Primitive-aware coverage expansion / repetition-fix (v1.8).

v1.7 demonstrated target-conditioned cardinality arbitration on
`composite_cardinality_with_decoy`. Repetition was wired but limited
by `binding.repetition_survival_bound`'s fallback: when the candidate
ROI's column-mask at `row_y` is non-contiguous, the metric concatenates
disjoint columns and the spatial period is destroyed; when the
column-mask is empty, the metric falls back to the full row and any
ROI silently 'wins'. That made repetition target scoring nominal.

v1.8 ships a fixed strip-based repetition metric and a new repetition
distractor composite, so primitive-aware arbitration is tested across
two primitive families (cardinality and repetition) instead of one.
A new ARBITRATION_INVARIANT verdict is added for label-scoped
primitives so the dossier tells you when target conditioning has
nothing to do.

Verdicts:

    PROPOSAL_QUALITY_LIMIT      oracle_best < 0.80; no candidate is
                                 right; primitive-aware can't help.
    ARBITRATION_INVARIANT       primitive's metric is ROI-insensitive
                                 (label-scoped); target conditioning
                                 has nothing to add by construction.
    GENERIC_FUSION_SUFFICIENT   best generic ranker (single OR fused)
                                 already passes; target conditioning
                                 adds nothing on this composite.
    PRIMITIVE_AWARE_HELPS       generic best fails but primitive-aware
                                 passes - target conditioning is the
                                 difference.
    PRIMITIVE_AWARE_STILL_FAILS oracle exists but primitive-aware
                                 top1 also < 0.80.

Honest scope (v1.8 still NOT claiming):
  - The strip-based repetition metric is intentionally simple: largest
    contiguous strip of col_mask at row_y, autocorrelation on that
    strip alone, requires at least 2*period columns. No multi-strip
    aggregation, no period inference, no abstain.
  - role_zone is still NOT covered by an ROI-aware target metric.
    It will appear in the dossier (if tested) as ARBITRATION_INVARIANT
    because the existing role_zone metric is label-scoped.
  - Reuses v1.5 distractor composites + adds one new repetition
    composite.
  - Still not a decoder, not E/D, not a runtime, not a camera app.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, List, Dict, Callable, Tuple

import numpy as np

from .simulate import SimParams, run_chain
from .interaction import INTERACTION_CAPTURE
from .binding import (
    cardinality_survival_bound,
    compute_relation_metric_bound,
    ROBUST_THR,
)
from .inferred_binding import PROPOSALS
from .arbitration import candidates_from_mask
from .distractor_arbitration import (
    DISTRACTOR_COMPOSITES, RANKERS as SINGLE_RANKERS,
)
from .fusion import FUSED_RANKERS
from .primitive_aware import (
    rank_by_cardinality_target,
    best_generic_top1 as _best_generic_top1,
)
from .relations import _lum


# -------------------------------------------------------------------
# Strip-based repetition fix
# -------------------------------------------------------------------

def _largest_contiguous_strip(mask_1d) -> Tuple[int, int]:
    """Return (start, end) of the longest run of True in a 1-D bool
    array. end is exclusive. (0, 0) if there are no True values."""
    n = int(mask_1d.size)
    best_s, best_e = 0, 0
    cur_s = None
    for i in range(n):
        v = bool(mask_1d[i])
        if v and cur_s is None:
            cur_s = i
        elif not v and cur_s is not None:
            length = i - cur_s
            if length > best_e - best_s:
                best_s, best_e = cur_s, i
            cur_s = None
    if cur_s is not None:
        length = n - cur_s
        if length > best_e - best_s:
            best_s, best_e = cur_s, n
    return best_s, best_e


def repetition_survival_bound_strip(truth_pkt, captured, roi_mask):
    """Strip-based fixed variant of binding.repetition_survival_bound.

    Differences from the v1.5 metric:
      - Uses the LARGEST CONTIGUOUS strip of `roi_mask[row_y]` instead
        of concatenating non-contiguous columns (which destroys the
        spatial period).
      - Requires the strip to span at least 2 * period_px columns; if
        not, returns 0.0 (instead of falling back to the full row,
        which silently lets any ROI claim the right answer).
    """
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
    if col_mask.dtype != bool:
        col_mask = col_mask.astype(bool)
    s, e = _largest_contiguous_strip(col_mask)
    n = e - s
    if n < int(2 * period):
        return 0.0
    prof = row[s:e].copy()
    prof = prof - prof.mean()
    if prof.std() < 1e-9:
        return 0.0
    ac = np.correlate(prof, prof, mode="full")[n - 1:]
    max_lag = n // 2
    if max_lag < 5:
        return 0.0
    nontrivial = ac[1:max_lag + 1]
    if nontrivial.max() <= 0:
        return 0.0
    nt = nontrivial / nontrivial.max()
    target = int(round(period))
    if target < 1 or target > max_lag:
        return 0.0
    lo = max(1, target - 2); hi = min(max_lag, target + 2)
    return float(np.clip(nt[lo - 1:hi].max(), 0.0, 1.0))


# -------------------------------------------------------------------
# Strip-based primitive-aware repetition ranker
# -------------------------------------------------------------------

def rank_by_repetition_target_strip(cands, captured, target_period, row_y):
    """Rank candidates by `repetition_survival_bound_strip` against
    known target period and row_y. Top-1 = candidate whose largest
    contiguous strip at row_y has the strongest autocorrelation peak
    near `target_period`."""
    if not cands or target_period is None or row_y is None:
        return []
    period = float(target_period); ry = int(row_y)
    scores = []
    for c in cands:
        pkt = {"meta": {"relation": {"kind": "repetition",
                                       "period_px": period,
                                       "row_y": ry}}}
        s = repetition_survival_bound_strip(pkt, captured, c)
        scores.append(float(s) if isinstance(s, float) and s == s else 0.0)
    return sorted(range(len(cands)), key=lambda i: -scores[i])


# -------------------------------------------------------------------
# New repetition distractor composite (v1.8)
# -------------------------------------------------------------------

def composite_repetition_distractor(size: int = 192, seed: int = 0) -> dict:
    """Intended: periodic row of 5 markers (period = size/8) at the
    middle row, brightness 0.85. Decoy: 2 brighter non-periodic discs
    at different y. The decoys are bigger and brighter, so generic
    rankers (area, intensity, edge_density) will pick them; they will
    score 0 under the strip-based repetition metric because the
    candidate's contiguous strip at row_y is too short or empty.
    Primitive-aware repetition target ranker should pick the intended
    row's candidate -> PRIMITIVE_AWARE_HELPS."""
    img = np.full((size, size), 0.15, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    yy, xx = np.mgrid[0:size, 0:size]

    row_y = size // 2
    p_int = max(20, size // 9)
    r = max(3, size // 40)
    n_int = 4
    x0 = int(size * 0.05)
    for i in range(n_int):
        cx = x0 + i * p_int
        if cx >= size:
            break
        m = (yy - row_y) ** 2 + (xx - cx) ** 2 <= r * r
        img[m] = 0.85
        lab[m] = 1 + i
    rep_labels = np.where((lab >= 1) & (lab <= n_int), lab, 0).astype(np.int32)

    # Decoy: ONE brighter non-periodic large disc at a different y
    # so it dominates area / intensity / compactness rankers but has
    # no contiguous column strip at row_y -> strip metric returns 0.
    r_dec = max(20, size // 7)
    dec_y = int(size * 0.20)
    dec_x = int(size * 0.75)
    m_dec = (yy - dec_y) ** 2 + (xx - dec_x) ** 2 <= r_dec * r_dec
    img[m_dec] = 0.95
    lab[m_dec & (lab == 0)] = 101

    img = np.clip(img, 0.0, 1.0)
    return {
        "image": img,
        "labels": lab,
        "meta": {
            "relation": {"kind": "composite", "parts": ["repetition"]},
            "composite": [
                {"name": "repetition",
                 "labels": rep_labels,
                 "relation": {"kind": "repetition",
                              "period_px": float(p_int),
                              "row_y": row_y}},
            ],
        },
    }


COVERAGE_COMPOSITES: Dict[str, Callable[..., dict]] = {
    **DISTRACTOR_COMPOSITES,
    "composite_repetition_distractor": composite_repetition_distractor,
}


# -------------------------------------------------------------------
# Verdict
# -------------------------------------------------------------------

LABEL_SCOPED_KINDS = {"ordering", "adjacency", "symmetry", "orientation",
                       "hierarchy", "role_zone"}


def _verdict(oracle_best, best_generic, target_aware, label_scoped=False):
    ok = lambda x: isinstance(x, float) and x == x
    if not ok(oracle_best) or oracle_best < ROBUST_THR:
        return "PROPOSAL_QUALITY_LIMIT"
    if label_scoped:
        return "ARBITRATION_INVARIANT"
    target_ok = ok(target_aware) and target_aware >= ROBUST_THR
    generic_ok = ok(best_generic) and best_generic >= ROBUST_THR
    if generic_ok:
        return "GENERIC_FUSION_SUFFICIENT"
    if target_ok:
        return "PRIMITIVE_AWARE_HELPS"
    return "PRIMITIVE_AWARE_STILL_FAILS"


def _fmax_idx(scores):
    best = None; best_idx = None
    for i, v in enumerate(scores):
        if isinstance(v, float) and v == v:
            if best is None or v > best:
                best = v; best_idx = i
    return best_idx, best


# -------------------------------------------------------------------
# Dossier
# -------------------------------------------------------------------

def _score_with_repetition_strip(sub, captured, c):
    """Score a candidate by the strip-based repetition metric."""
    pkt = {"meta": {"relation": sub["relation"]}}
    return repetition_survival_bound_strip(pkt, captured, c)


def build_coverage_dossier(size: int = 192, seed: int = 0) -> dict:
    capture = INTERACTION_CAPTURE()
    per_composite: Dict[str, dict] = {}

    for comp_kind, builder in COVERAGE_COMPOSITES.items():
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

            # Score every candidate. For repetition we use the FIXED
            # strip-based metric so the dossier's oracle reflects the
            # real ROI-discriminating behavior we want to test.
            scores = []
            for c in all_cands:
                if kind == "repetition":
                    v = _score_with_repetition_strip(sub, captured, c)
                else:
                    v = compute_relation_metric_bound(sub, captured, c)
                scores.append(float(v) if isinstance(v, float) and v == v
                              else float("nan"))
            oracle_idx, oracle_best = _fmax_idx(scores)

            best_generic, best_generic_name, generic_top1 = (
                _best_generic_top1(all_cands, captured, scores))

            target_top1 = float("nan"); target_idx = -1
            target_params: Dict[str, object] = {}
            if kind == "cardinality":
                target_params = {"target_count": sub["relation"]["count"]}
                order = rank_by_cardinality_target(
                    all_cands, captured, sub["relation"]["count"])
                if order:
                    target_idx = int(order[0])
                    target_top1 = scores[target_idx]
            elif kind == "repetition":
                target_params = {"target_period": sub["relation"]["period_px"],
                                 "row_y": sub["relation"]["row_y"]}
                order = rank_by_repetition_target_strip(
                    all_cands, captured,
                    sub["relation"]["period_px"],
                    sub["relation"]["row_y"])
                if order:
                    target_idx = int(order[0])
                    target_top1 = scores[target_idx]
            # Other kinds: no target-conditioned ranker; primitive-aware
            # is left as nan and verdict comes out ARBITRATION_INVARIANT.

            label_scoped = kind in LABEL_SCOPED_KINDS
            verdict = _verdict(oracle_best, best_generic, target_top1,
                               label_scoped=label_scoped)

            sub_records.append({
                "sub_primitive":     sub["name"],
                "relation_kind":     kind,
                "n_candidates":      len(all_cands),
                "target_params":     target_params,
                "label_scoped":      label_scoped,
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
               "ARBITRATION_INVARIANT":       0,
               "PRIMITIVE_AWARE_HELPS":       1,
               "PRIMITIVE_AWARE_STILL_FAILS": 2,
               "PROPOSAL_QUALITY_LIMIT":      3}
        worst = max((sr["verdict"] for sr in sub_records),
                    key=lambda v: sev.get(v, -1))
        per_composite[comp_kind] = {
            "sub_relations":   sub_records,
            "overall_verdict": worst,
        }

    return {
        "schema_version": "1.8",
        "interaction_capture": capture.as_dict(),
        "single_rankers": list(SINGLE_RANKERS.keys()),
        "fused_rankers":  list(FUSED_RANKERS.keys()),
        "primitive_aware_rankers": ["cardinality_target",
                                     "repetition_target_strip"],
        "thresholds": {"robust_thr": ROBUST_THR},
        "per_composite": per_composite,
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


def write_coverage_reports(out_dir: Path,
                            dossier: Optional[dict] = None) -> dict:
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    dossier = dossier or build_coverage_dossier()

    with open(out_dir / "coverage.json", "w", encoding="utf-8") as f:
        json.dump(_scrub(dossier), f, indent=2)

    L = []
    L.append("# Aurexis Research Sim v1.8 - Primitive-aware coverage / repetition-fix dossier")
    L.append("")
    L.append("v1.7 demonstrated target-conditioned cardinality scoring on the")
    L.append("v1.5 distractor composites. v1.8 adds a fixed strip-based repetition")
    L.append("metric, a new repetition distractor composite, and an")
    L.append("ARBITRATION_INVARIANT verdict for label-scoped primitives.")
    L.append("")
    L.append("Single rankers : " + ", ".join("`" + r + "`" for r in dossier["single_rankers"]) + ".")
    L.append("Fused rankers  : " + ", ".join("`" + r + "`" for r in dossier["fused_rankers"]) + ".")
    L.append("Primitive-aware: " + ", ".join("`" + r + "`" for r in dossier["primitive_aware_rankers"]) + ".")
    L.append("")
    L.append("Verdict:")
    L.append("- **GENERIC_FUSION_SUFFICIENT**    best generic passes; primitive-aware adds nothing")
    L.append("- **PRIMITIVE_AWARE_HELPS**        generic best fails; primitive-aware passes")
    L.append("- **PRIMITIVE_AWARE_STILL_FAILS**  oracle passes; both generic and primitive-aware fail")
    L.append("- **PROPOSAL_QUALITY_LIMIT**       oracle_best < {:.2f}".format(ROBUST_THR))
    L.append("- **ARBITRATION_INVARIANT**        primitive's metric is ROI-insensitive (label-scoped)")
    L.append("")
    L.append("## Overall summary")
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

    with open(out_dir / "COVERAGE.md", "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return dossier


def main():
    dossier = build_coverage_dossier()
    write_coverage_reports(Path.cwd(), dossier)
    print("Aurexis Research Sim v1.8 - Coverage dossier")
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
    print("Wrote coverage.json and COVERAGE.md into CWD.")
    return 0


def _entry():
    raise SystemExit(main())


if __name__ == "__main__":
    _entry()
# end of file padding to keep tail simple
