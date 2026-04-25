"""Primitive-aware arbitration / target-conditioned scoring (v1.7).

v1.6 showed that simple z-score-sum and Borda fusion of 4 generic
features cannot rescue v1.5's distractor composites: features
themselves (area, mean_intensity, edge_density, compactness) are
blind to what each primitive actually needs.

v1.7 tests whether **target-conditioned scoring** - i.e. a ranker that
knows what primitive family it is looking for and what target
parameters define a success - can recover those failures.

The mechanism is simple and honest: when the upstream language model
can communicate 'I am looking for cardinality with N=3' or
'repetition with period=p at row y', the arbitration layer can score
each candidate ROI by the SAME survival metric the dossier uses.
Top-1 by metric-as-ranker is by construction equal to oracle-best.

The interesting question is then: for cases where generic fusion
fails (FUSION_INSUFFICIENT in v1.6), does target-conditioned scoring
recover? And on what kinds of cases does it still fail?

Verdicts:
    PROPOSAL_QUALITY_LIMIT    oracle_best < 0.80; no candidate is
                               right; primitive-aware can't help.
    GENERIC_FUSION_SUFFICIENT  best generic ranker (single OR fused)
                               already passes; target conditioning
                               adds nothing on this composite.
    PRIMITIVE_AWARE_HELPS     generic best fails but primitive-aware
                               passes - target conditioning is the
                               difference.
    PRIMITIVE_AWARE_STILL_FAILS  oracle exists but primitive-aware top1
                               also < 0.80 (rare; usually means the
                               metric has internal threshold differences
                               from the ranker's threshold).

Honest scope (v1.7 still NOT claiming):
  - Cardinality and repetition primitive-aware rankers only.
    role_zone, ordering, etc. are label-scoped and ROI-insensitive,
    so target-conditioning has nothing to add for them.
  - The primitive-aware ranker IS the survival metric used as a
    ranker. This is intentional: it tests whether the metric itself
    is a useful evidence signal when the target is known. It does
    NOT pretend to be a smarter scoring scheme than the metric.
  - Repetition coverage is still limited by the v1.5 fallback issue
    in `repetition_survival_bound` (non-contiguous ROI col-mask
    discards spatial period); a fix is scheduled for v1.8.
  - Reuses v1.5 distractor composites; no new probe coverage.
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
    repetition_survival_bound,
    compute_relation_metric_bound,
    ROBUST_THR,
)
from .inferred_binding import PROPOSALS
from .arbitration import candidates_from_mask
from .distractor_arbitration import (
    DISTRACTOR_COMPOSITES, RANKERS as SINGLE_RANKERS,
)
from .fusion import FUSED_RANKERS


# -------------------------------------------------------------------
# Target-conditioned primitive-aware rankers
# -------------------------------------------------------------------

def rank_by_cardinality_target(cands, captured, target_count):
    """Rank candidates by cardinality survival score against a known
    target_count. Top-1 = candidate whose internal component count is
    closest to target_count."""
    if not cands or target_count is None:
        return []
    target_count = int(target_count)
    scores = []
    for c in cands:
        pkt = {"meta": {"relation":
                         {"kind": "cardinality", "count": target_count}}}
        s = cardinality_survival_bound(pkt, captured, c)
        scores.append(float(s) if isinstance(s, float) and s == s else 0.0)
    return sorted(range(len(cands)), key=lambda i: -scores[i])


def rank_by_repetition_target(cands, captured, target_period, row_y):
    """Rank candidates by repetition survival score at target period
    and row_y. Limited by v1.5's `repetition_survival_bound` fallback
    issue (non-contiguous ROI col-mask discards spatial period)."""
    if not cands or target_period is None or row_y is None:
        return []
    period = float(target_period); ry = int(row_y)
    scores = []
    for c in cands:
        pkt = {"meta": {"relation": {"kind": "repetition",
                                       "period_px": period,
                                       "row_y": ry}}}
        s = repetition_survival_bound(pkt, captured, c)
        scores.append(float(s) if isinstance(s, float) and s == s else 0.0)
    return sorted(range(len(cands)), key=lambda i: -scores[i])


# -------------------------------------------------------------------
# Generic baseline: best of all v1.6 single + fused rankers
# -------------------------------------------------------------------

def best_generic_top1(cands, captured, scores_per_candidate):
    """Run all 4 single rankers + 2 fused rankers; for each, look up
    its top-1 score in the supplied scores_per_candidate list. Return
    (best_value, best_ranker_name, all_top1) where all_top1 is a dict
    {ranker_name: top1_score}."""
    all_top1: Dict[str, float] = {}
    for rname, ranker in SINGLE_RANKERS.items():
        try:
            order = ranker(cands, captured)
        except TypeError:
            order = ranker(cands)
        if order:
            all_top1[rname] = scores_per_candidate[order[0]]
        else:
            all_top1[rname] = float("nan")
    for fname, fr in FUSED_RANKERS.items():
        order = fr(cands, captured)
        if order:
            all_top1[fname] = scores_per_candidate[order[0]]
        else:
            all_top1[fname] = float("nan")
    best = None; best_name = None
    for k, v in all_top1.items():
        if isinstance(v, float) and v == v:
            if best is None or v > best:
                best = v; best_name = k
    return best, best_name, all_top1


# -------------------------------------------------------------------
# Verdict
# -------------------------------------------------------------------

def _verdict(oracle_best, best_generic, target_aware):
    ok = lambda x: isinstance(x, float) and x == x
    if not ok(oracle_best) or oracle_best < ROBUST_THR:
        return "PROPOSAL_QUALITY_LIMIT"
    target_ok = ok(target_aware) and target_aware >= ROBUST_THR
    generic_ok = ok(best_generic) and best_generic >= ROBUST_THR
    if generic_ok:
        return "GENERIC_FUSION_SUFFICIENT"
    if target_ok:
        return "PRIMITIVE_AWARE_HELPS"
    return "PRIMITIVE_AWARE_STILL_FAILS"


# -------------------------------------------------------------------
# Dossier
# -------------------------------------------------------------------

def _fmax_idx(scores):
    best = None; best_idx = None
    for i, v in enumerate(scores):
        if isinstance(v, float) and v == v:
            if best is None or v > best:
                best = v; best_idx = i
    return best_idx, best


def _target_for(sub):
    rel = sub["relation"]
    kind = rel.get("kind")
    if kind == "cardinality":
        return ("cardinality", {"target_count": rel.get("count")})
    if kind == "repetition":
        return ("repetition", {"target_period": rel.get("period_px"),
                                "row_y": rel.get("row_y")})
    return (kind, {})


def build_primitive_aware_dossier(size: int = 192, seed: int = 0) -> dict:
    capture = INTERACTION_CAPTURE()
    per_composite: Dict[str, dict] = {}

    for comp_kind, builder in DISTRACTOR_COMPOSITES.items():
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
            if not all_cands:
                sub_records.append({
                    "sub_primitive":     sub["name"],
                    "relation_kind":     sub["relation"]["kind"],
                    "n_candidates":      0,
                    "target_params":     {},
                    "oracle_best":       float("nan"),
                    "generic_top1":      {},
                    "best_generic":      float("nan"),
                    "best_generic_name": None,
                    "primitive_aware":   float("nan"),
                    "primitive_aware_idx": -1,
                    "verdict":           "PROPOSAL_QUALITY_LIMIT",
                })
                continue

            scores = []
            for c in all_cands:
                v = compute_relation_metric_bound(sub, captured, c)
                scores.append(float(v) if isinstance(v, float) and v == v
                              else float("nan"))
            oracle_idx, oracle_best = _fmax_idx(scores)

            best_generic, best_generic_name, generic_top1 = (
                best_generic_top1(all_cands, captured, scores))

            kind, target_params = _target_for(sub)
            target_top1 = float("nan")
            target_idx = -1
            if kind == "cardinality":
                order = rank_by_cardinality_target(
                    all_cands, captured, target_params["target_count"])
                if order:
                    target_idx = int(order[0])
                    target_top1 = scores[target_idx]
            elif kind == "repetition":
                order = rank_by_repetition_target(
                    all_cands, captured,
                    target_params["target_period"],
                    target_params["row_y"])
                if order:
                    target_idx = int(order[0])
                    target_top1 = scores[target_idx]
            # Other primitives: target conditioning is a no-op
            # because their metric is label-scoped (ROI-insensitive).

            verdict = _verdict(oracle_best, best_generic, target_top1)

            sub_records.append({
                "sub_primitive":     sub["name"],
                "relation_kind":     sub["relation"]["kind"],
                "n_candidates":      len(all_cands),
                "target_params":     target_params,
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
               "PRIMITIVE_AWARE_STILL_FAILS": 2,
               "PROPOSAL_QUALITY_LIMIT":      3}
        worst = max((sr["verdict"] for sr in sub_records),
                    key=lambda v: sev.get(v, -1))
        per_composite[comp_kind] = {
            "sub_relations":   sub_records,
            "overall_verdict": worst,
        }

    return {
        "schema_version": "1.7",
        "interaction_capture": capture.as_dict(),
        "single_rankers": list(SINGLE_RANKERS.keys()),
        "fused_rankers":  list(FUSED_RANKERS.keys()),
        "primitive_aware_rankers": ["cardinality_target", "repetition_target"],
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


def write_primitive_aware_reports(out_dir: Path,
                                    dossier: Optional[dict] = None) -> dict:
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    dossier = dossier or build_primitive_aware_dossier()

    with open(out_dir / "primitive_aware.json", "w", encoding="utf-8") as f:
        json.dump(_scrub(dossier), f, indent=2)

    L = []
    L.append("# Aurexis Research Sim v1.7 - Primitive-aware / target-conditioned dossier")
    L.append("")
    L.append("Per sub-primitive: best of generic single + fused rankers vs")
    L.append("a target-conditioned primitive-aware ranker that uses the")
    L.append("survival metric itself as the ranking signal against known")
    L.append("target parameters (e.g., target_count for cardinality).")
    L.append("")
    L.append("Single rankers : " + ", ".join("`" + r + "`" for r in dossier["single_rankers"]) + ".")
    L.append("Fused rankers  : " + ", ".join("`" + r + "`" for r in dossier["fused_rankers"]) + ".")
    L.append("Primitive-aware: " + ", ".join("`" + r + "`" for r in dossier["primitive_aware_rankers"]) + ".")
    L.append("")
    L.append("Verdict:")
    L.append("- **GENERIC_FUSION_SUFFICIENT**    best generic ranker passes; primitive-aware adds nothing")
    L.append("- **PRIMITIVE_AWARE_HELPS**        generic best fails; primitive-aware passes")
    L.append("- **PRIMITIVE_AWARE_STILL_FAILS**  oracle passes; both generic and primitive-aware fail")
    L.append("- **PROPOSAL_QUALITY_LIMIT**       oracle_best < {:.2f}".format(ROBUST_THR))
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
            bg = _f(sr["best_generic"])
            bg_name = sr["best_generic_name"] or "-"
            L.append("| " + sr["sub_primitive"] + " | " + sr["relation_kind"]
                     + " | " + tp_str
                     + " | " + _f(sr["oracle_best"])
                     + " | " + bg + " (" + bg_name + ")"
                     + " | " + _f(sr["primitive_aware"])
                     + " | " + sr["verdict"] + " |")
        L.append("")
        L.append("Per-generic-ranker top-1 (for reference):")
        L.append("")
        all_rankers = dossier["single_rankers"] + dossier["fused_rankers"]
        L.append("| sub | " + " | ".join(all_rankers) + " |")
        L.append("|---|" + "|".join(["---"] * len(all_rankers)) + "|")
        for sr in rec["sub_relations"]:
            row = [sr["sub_primitive"]]
            for r in all_rankers:
                row.append(_f(sr["generic_top1"].get(r, float("nan"))))
            L.append("| " + " | ".join(row) + " |")
        L.append("")

    with open(out_dir / "PRIMITIVE_AWARE.md", "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return dossier


def main():
    dossier = build_primitive_aware_dossier()
    write_primitive_aware_reports(Path.cwd(), dossier)
    print("Aurexis Research Sim v1.7 - Primitive-aware dossier")
    print("")
    for ck, rec in dossier["per_composite"].items():
        print("  " + ck + "  [" + rec["overall_verdict"] + "]")
        for sr in rec["sub_relations"]:
            tp = sr["target_params"]
            tp_str = ", ".join(k + "=" + str(v) for k, v in tp.items()) or "-"
            print("    " + sr["sub_primitive"]
                  + "  target=(" + tp_str + ")"
                  + "  oracle=" + _f(sr["oracle_best"])
                  + "  best_generic=" + _f(sr["best_generic"])
                  + " (" + str(sr["best_generic_name"]) + ")"
                  + "  primitive_aware=" + _f(sr["primitive_aware"])
                  + "  " + sr["verdict"])
        print("")
    print("Wrote primitive_aware.json and PRIMITIVE_AWARE.md into CWD.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
