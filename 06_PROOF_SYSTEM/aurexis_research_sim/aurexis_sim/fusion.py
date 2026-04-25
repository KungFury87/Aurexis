"""Arbitration redesign / evidence-fusion guidance (v1.6).

v1.5 reported per-ranker top-1 outcomes and verdicts SURVIVES_UNDER_
DISTRACTORS / RANKER_BRITTLE / DISTRACTOR_DOMINATED / FAILS_EVEN_ORACLE.
That tells us a ranker failed but not WHY in actionable terms. v1.6
closes the gap with two ingredients:

  1. Per-feature attribution: for each single-feature ranker that
     disagreed with oracle-best, we report which feature most pushed
     the ranker toward the wrong candidate (largest positive z-score
     difference). compactness sign is inverted so '+' always means
     'pushed picker AWAY from oracle.'

  2. Two label-blind fused rankers, both deterministic:
       - rank_by_normalized_sum
           sum of z-score normalized features
           (area + mean_intensity + edge_density - compactness).
       - rank_by_borda
           Borda count across the four single rankers; lowest sum of
           rank positions wins. Resilient to a single rogue ranker.

We also report a per-ranker confidence margin (top-1 raw feature
score over top-2 raw feature score) - low margin means the pick was
ambiguous.

Per sub-primitive verdict:
    PROPOSAL_QUALITY_LIMIT   oracle_best < 0.80
    FUSION_ROBUST            all fused rankers' top1 >= 0.80
    FUSION_PARTIAL           some fused pass, some fail
    FUSION_INSUFFICIENT      oracle passes but no fused ranker passes

Honest scope (v1.6 still NOT claiming):
  - Two fusion strategies; no learned ranker, no proposal-confidence
    abstain, no multi-scale candidate generation.
  - Attribution is a 1-step z-score diff against oracle-best.
  - Reuses v1.5's two distractor composites + adds one fusion-friendly
    composite designed so 3 of 4 single rankers agree on the intended
    region. This is an arbitration redesign pass, not a probe-coverage
    pass.
  - Still not a decoder, not E/D, not a runtime, not a camera app.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, List, Dict, Callable

import numpy as np

from .simulate import SimParams, run_chain
from .interaction import INTERACTION_CAPTURE
from .binding import compute_relation_metric_bound, ROBUST_THR
from .inferred_binding import PROPOSALS
from .arbitration import candidates_from_mask
from .distractor_arbitration import (
    DISTRACTOR_COMPOSITES, RANKERS as SINGLE_RANKERS,
    _area_scores, _mean_intensity_scores,
    _edge_density_scores, _compactness_scores,
)


# -------------------------------------------------------------------
# Fusion-friendly composite (3 of 4 single rankers pick intended).
# -------------------------------------------------------------------

# v1.6 reuses v1.5's distractor composites unchanged; this is an
# arbitration redesign pass, not a probe-coverage pass.
FUSION_COMPOSITES: Dict[str, Callable[..., dict]] = dict(DISTRACTOR_COMPOSITES)


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _zscore(values):
    arr = np.asarray(values, dtype=np.float64)
    if arr.size == 0:
        return arr
    mu = float(arr.mean()); sd = float(arr.std())
    if sd < 1e-12:
        return np.zeros_like(arr)
    return (arr - mu) / sd


def _fmax_idx(scores):
    best = None; best_idx = None
    for i, v in enumerate(scores):
        if isinstance(v, float) and v == v:
            if best is None or v > best:
                best = v; best_idx = i
    return best_idx, best


def _all_feature_scores(cands, captured):
    return {
        "area":           _area_scores(cands),
        "mean_intensity": _mean_intensity_scores(cands, captured),
        "edge_density":   _edge_density_scores(cands, captured),
        "compactness":    _compactness_scores(cands),
    }


# -------------------------------------------------------------------
# Fused rankers
# -------------------------------------------------------------------

def rank_by_normalized_sum(cands, captured):
    if not cands:
        return []
    f = _all_feature_scores(cands, captured)
    fused = (_zscore(f["area"])
             + _zscore(f["mean_intensity"])
             + _zscore(f["edge_density"])
             - _zscore(f["compactness"]))
    return sorted(range(len(cands)), key=lambda i: -float(fused[i]))


def rank_by_borda(cands, captured):
    if not cands:
        return []
    n = len(cands)
    rank_sum = np.zeros(n, dtype=np.float64)
    for rname, ranker in SINGLE_RANKERS.items():
        try:
            order = ranker(cands, captured)
        except TypeError:
            order = ranker(cands)
        for pos, idx in enumerate(order):
            rank_sum[idx] += float(pos)
    return sorted(range(n), key=lambda i: float(rank_sum[i]))


FUSED_RANKERS: Dict[str, Callable] = {
    "normalized_sum": rank_by_normalized_sum,
    "borda":          rank_by_borda,
}


# -------------------------------------------------------------------
# Attribution + confidence
# -------------------------------------------------------------------

def attribute_failure(cands, captured, oracle_idx, picker_idx):
    if oracle_idx is None or picker_idx is None or oracle_idx == picker_idx:
        return None
    f = _all_feature_scores(cands, captured)
    z = {k: _zscore(v) for k, v in f.items()}
    diffs = {
        "area":           float(z["area"][picker_idx]
                                - z["area"][oracle_idx]),
        "mean_intensity": float(z["mean_intensity"][picker_idx]
                                - z["mean_intensity"][oracle_idx]),
        "edge_density":   float(z["edge_density"][picker_idx]
                                - z["edge_density"][oracle_idx]),
        # compactness inverted: lower preferred, so picker preferring
        # lower compactness (negative diff) = pulled TOWARD the wrong
        # blob. Flip sign so '+' always means 'pushed picker away'.
        "compactness":   -float(z["compactness"][picker_idx]
                                - z["compactness"][oracle_idx]),
    }
    dominant = max(diffs.keys(), key=lambda k: diffs[k])
    return {"per_feature_z_diff": diffs, "dominant_misleading": dominant}


def confidence_margin(cands, captured, ranker_fn):
    if not cands or len(cands) < 2:
        return None
    try:
        order = ranker_fn(cands, captured)
    except TypeError:
        order = ranker_fn(cands)
    if len(order) < 2:
        return None
    name_map = {
        "rank_by_area":           ("area",           lambda c, _x: _area_scores(c)),
        "rank_by_mean_intensity": ("mean_intensity", _mean_intensity_scores),
        "rank_by_edge_density":   ("edge_density",   _edge_density_scores),
        "rank_by_compactness":    ("compactness",    lambda c, _x: _compactness_scores(c)),
    }
    fname = ranker_fn.__name__
    if fname not in name_map:
        return None
    feature, scorer = name_map[fname]
    scores = scorer(cands, captured)
    top1 = scores[order[0]]; top2 = scores[order[1]]
    if feature == "compactness":
        if top1 <= 0:
            return None
        return float(top2 / top1)
    if abs(top1) < 1e-12 or abs(top2) < 1e-12:
        return None
    return float(top1 / top2)


# -------------------------------------------------------------------
# Verdict
# -------------------------------------------------------------------

def _verdict(oracle_best, fused_top1):
    ok = lambda x: isinstance(x, float) and x == x
    if not ok(oracle_best) or oracle_best < ROBUST_THR:
        return "PROPOSAL_QUALITY_LIMIT"
    total = sum(1 for v in fused_top1.values() if ok(v))
    passes = sum(1 for v in fused_top1.values()
                 if ok(v) and v >= ROBUST_THR)
    if total == 0:
        return "FUSION_INSUFFICIENT"
    if passes == total:
        return "FUSION_ROBUST"
    if passes == 0:
        return "FUSION_INSUFFICIENT"
    return "FUSION_PARTIAL"


# -------------------------------------------------------------------
# Dossier
# -------------------------------------------------------------------

def build_fusion_dossier(size: int = 192, seed: int = 0) -> dict:
    capture = INTERACTION_CAPTURE()
    per_composite: Dict[str, dict] = {}

    for comp_kind, builder in FUSION_COMPOSITES.items():
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
                    "sub_primitive":   sub["name"],
                    "relation_kind":   sub["relation"]["kind"],
                    "n_candidates":    0,
                    "oracle_best":     float("nan"),
                    "oracle_idx":      -1,
                    "single_top1":     {}, "single_top1_idx": {},
                    "fused_top1":      {}, "fused_top1_idx":  {},
                    "attributions":    {}, "confidence":      {},
                    "verdict":         "PROPOSAL_QUALITY_LIMIT",
                })
                continue

            scores = []
            for c in all_cands:
                v = compute_relation_metric_bound(sub, captured, c)
                scores.append(float(v) if isinstance(v, float) and v == v
                              else float("nan"))
            oracle_idx, oracle_best = _fmax_idx(scores)

            single_top1 = {}; single_top1_idx = {}
            attributions = {}; confidence = {}
            for rname, ranker in SINGLE_RANKERS.items():
                try:
                    order = ranker(all_cands, captured)
                except TypeError:
                    order = ranker(all_cands)
                if not order:
                    single_top1[rname] = float("nan")
                    single_top1_idx[rname] = -1
                    continue
                top = order[0]
                single_top1[rname] = scores[top]
                single_top1_idx[rname] = int(top)
                ok_pass = (isinstance(scores[top], float)
                           and scores[top] == scores[top]
                           and scores[top] >= ROBUST_THR)
                attributions[rname] = (None if ok_pass
                                       else attribute_failure(
                                           all_cands, captured,
                                           oracle_idx, top))
                confidence[rname] = confidence_margin(
                    all_cands, captured, ranker)

            fused_top1 = {}; fused_top1_idx = {}
            for fname, fr in FUSED_RANKERS.items():
                order = fr(all_cands, captured)
                if not order:
                    fused_top1[fname] = float("nan")
                    fused_top1_idx[fname] = -1
                    continue
                top = order[0]
                fused_top1[fname] = scores[top]
                fused_top1_idx[fname] = int(top)

            verdict = _verdict(oracle_best, fused_top1)

            sub_records.append({
                "sub_primitive":   sub["name"],
                "relation_kind":   sub["relation"]["kind"],
                "n_candidates":    len(all_cands),
                "oracle_best":     (oracle_best
                                     if oracle_best is not None
                                     else float("nan")),
                "oracle_idx":      (oracle_idx if oracle_idx is not None
                                     else -1),
                "single_top1":     single_top1,
                "single_top1_idx": single_top1_idx,
                "fused_top1":      fused_top1,
                "fused_top1_idx":  fused_top1_idx,
                "attributions":    attributions,
                "confidence":      confidence,
                "verdict":         verdict,
            })

        sev = {"FUSION_ROBUST":          0,
               "FUSION_PARTIAL":         1,
               "FUSION_INSUFFICIENT":    2,
               "PROPOSAL_QUALITY_LIMIT": 3}
        worst = max((sr["verdict"] for sr in sub_records),
                    key=lambda v: sev.get(v, -1))
        per_composite[comp_kind] = {
            "sub_relations":   sub_records,
            "overall_verdict": worst,
        }

    return {
        "schema_version": "1.6",
        "interaction_capture": capture.as_dict(),
        "single_rankers": list(SINGLE_RANKERS.keys()),
        "fused_rankers":  list(FUSED_RANKERS.keys()),
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


def _fs(v):
    if not (isinstance(v, float) and v == v):
        return "n/a"
    return "{:+.2f}".format(v)


def _conf(v):
    if not (isinstance(v, float) and v == v):
        return "n/a"
    return "{:.2f}".format(v)


def write_fusion_reports(out_dir: Path,
                          dossier: Optional[dict] = None) -> dict:
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    dossier = dossier or build_fusion_dossier()

    with open(out_dir / "fusion.json", "w", encoding="utf-8") as f:
        json.dump(_scrub(dossier), f, indent=2)

    singles = dossier["single_rankers"]
    fuseds = dossier["fused_rankers"]
    L = []
    L.append("# Aurexis Research Sim v1.6 - Fusion / arbitration redesign dossier")
    L.append("")
    L.append("Per sub-primitive: single-ranker top-1, fused-ranker top-1, oracle-best,")
    L.append("plus per-feature attribution for every failed single ranker.")
    L.append("")
    L.append("Single rankers: " + ", ".join("`" + r + "`" for r in singles) + ".")
    L.append("Fused rankers:  " + ", ".join("`" + r + "`" for r in fuseds) + ".")
    L.append("")
    L.append("- `oracle_best` = max survival across ALL candidates")
    L.append("- `single_top1[r]` = survival under each single-feature ranker top-1")
    L.append("- `fused_top1[f]` = survival under each fused ranker top-1")
    L.append("- `attributions[r]` = z-score difference (picker - oracle) per feature")
    L.append("  for failed rankers; `+` means pushed AWAY from oracle. compactness")
    L.append("  is sign-inverted (lower compactness preferred).")
    L.append("- `confidence[r]` = top1/top2 raw feature score; >1 = decisive")
    L.append("")
    L.append("Verdict:")
    L.append("- **FUSION_ROBUST**         oracle passes AND all fused top1 >= " + "{:.2f}".format(ROBUST_THR))
    L.append("- **FUSION_PARTIAL**        oracle passes; some fused pass, some fail")
    L.append("- **FUSION_INSUFFICIENT**   oracle passes; no fused ranker passes")
    L.append("- **PROPOSAL_QUALITY_LIMIT** oracle_best < " + "{:.2f}".format(ROBUST_THR))
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
        header = (["sub", "kind", "oracle_best"]
                  + [r + ".top1" for r in singles]
                  + [f + ".top1" for f in fuseds]
                  + ["verdict"])
        L.append("| " + " | ".join(header) + " |")
        L.append("|" + "|".join(["---"] * len(header)) + "|")
        for sr in rec["sub_relations"]:
            row = [sr["sub_primitive"], sr["relation_kind"], _f(sr["oracle_best"])]
            for r in singles:
                row.append(_f(sr["single_top1"].get(r, float("nan"))))
            for fname in fuseds:
                row.append(_f(sr["fused_top1"].get(fname, float("nan"))))
            row.append(sr["verdict"])
            L.append("| " + " | ".join(row) + " |")
        L.append("")
        L.append("Failed-ranker attribution and confidence:")
        L.append("")
        L.append("| sub | ranker | dominant | area dz | mean_intensity dz | edge_density dz | compactness dz | conf top1/top2 |")
        L.append("|---|---|---|---|---|---|---|---|")
        for sr in rec["sub_relations"]:
            for r in singles:
                a = sr["attributions"].get(r)
                conf = sr["confidence"].get(r)
                cs = _conf(conf) if conf is not None else "n/a"
                if a is None:
                    L.append("| " + sr["sub_primitive"] + " | " + r
                             + " | (passed) | - | - | - | - | " + cs + " |")
                    continue
                d = a["per_feature_z_diff"]
                L.append("| " + sr["sub_primitive"] + " | " + r
                         + " | **" + a["dominant_misleading"] + "** | "
                         + _fs(d["area"]) + " | "
                         + _fs(d["mean_intensity"]) + " | "
                         + _fs(d["edge_density"]) + " | "
                         + _fs(d["compactness"]) + " | "
                         + cs + " |")
        L.append("")

    with open(out_dir / "FUSION.md", "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return dossier


def main():
    dossier = build_fusion_dossier()
    write_fusion_reports(Path.cwd(), dossier)
    print("Aurexis Research Sim v1.6 - Fusion dossier")
    print("")
    for ck, rec in dossier["per_composite"].items():
        print("  " + ck + "  [" + rec["overall_verdict"] + "]")
        for sr in rec["sub_relations"]:
            print("    " + sr["sub_primitive"]
                  + "  oracle=" + _f(sr["oracle_best"])
                  + "  verdict=" + sr["verdict"])
            for r, v in sr["single_top1"].items():
                print("      single  " + r + " = " + _f(v))
            for fname, v in sr["fused_top1"].items():
                print("      fused   " + fname + " = " + _f(v))
            for r, a in sr["attributions"].items():
                if a is None:
                    continue
                d = a["per_feature_z_diff"]
                print("      attribution[" + r + "] dominant="
                      + a["dominant_misleading"]
                      + "  (a=" + _fs(d["area"])
                      + " i=" + _fs(d["mean_intensity"])
                      + " e=" + _fs(d["edge_density"])
                      + " c=" + _fs(d["compactness"]) + ")")
        print("")
    print("Wrote fusion.json and FUSION.md into CWD.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
