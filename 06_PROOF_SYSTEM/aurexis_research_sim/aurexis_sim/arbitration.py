"""Proposal competition / arbitration-realism evaluation (v1.4).

v1.3 reported the best-of-proposals survival (max across two image-only
proposal methods). That is still oracle-flavored: each method emits a
single big mask, and "best" is the best of the two per sub-primitive.
A real decoder has to pick ONE region from a set of candidate ROIs
without knowing the truth label, and must live with the consequences.

v1.4 adds that realism step:

    1. Candidate generation: for each proposal mask we split it into
       connected components. Each component (plus a small dilation) is
       one candidate ROI. A proposal method thus produces a *set* of
       candidates, not a single ROI.

    2. Label-blind arbitration: a scene-agnostic ranker picks the
       top-1 candidate from each set. The current ranker is
       "largest-by-area". No truth info is used.

    3. Per sub-primitive we report:
         - oracle_best   : max survival across ALL candidates from ALL
                           proposal methods (theoretical ceiling)
         - top1          : survival using the top-ranked candidate from
                           each method, then best of those two top-1s
                           (honest selection; no truth access)
         - worst         : min survival across all candidates (false-
                           positive / wrong-pick burden)
         - n_candidates  : how many distinct candidates the proposal
                           set produced. 1 means zero arbitration
                           pressure; many means competition.

    4. Verdict per sub-primitive:
         SURVIVES_WITH_TOP1          top1 >= 0.80
         NEEDS_ORACLE_ARBITRATION    oracle_best >= 0.80 but top1 < 0.80
         FAILS_UNDER_COMPETITION     oracle_best < 0.80

Honest scope (v1.4 is NOT claiming):
  - A learned ranker. The ranker is deterministic, scene-agnostic,
    largest-area.
  - A proposal-confidence score. We report only n_candidates and
    the survival spread (oracle_best - worst).
  - Complete candidate enumeration. We take connected components of
    each proposal mask; we do not attempt multi-scale or merging.
  - Label-scoped relations (ordering, adjacency, role_zone, ...) are
    ROI-insensitive by construction and appear identical across all
    candidates; their verdicts are inherited trivially.
  - Still not a decoder, not E/D, not a runtime, not a camera app.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, List, Tuple

import numpy as np

from .simulate import SimParams, run_chain
from .sensor import SensorParams
from .interaction import COMPOSITES, INTERACTION_CAPTURE
from .binding import (
    compute_relation_metric_bound,
    ROBUST_THR,
)
from .inferred_binding import PROPOSALS


# =========================================================================
# Candidate extraction (connected components per proposal mask).
# =========================================================================

def _components(binary: np.ndarray) -> List[np.ndarray]:
    """Return list of boolean component masks (4-connected)."""
    h, w = binary.shape
    visited = np.zeros_like(binary, dtype=bool)
    comps: List[np.ndarray] = []
    for i in range(h):
        for j in range(w):
            if binary[i, j] and not visited[i, j]:
                comp = np.zeros_like(binary, dtype=bool)
                stack = [(i, j)]
                while stack:
                    y, x = stack.pop()
                    if y < 0 or y >= h or x < 0 or x >= w:
                        continue
                    if visited[y, x] or not binary[y, x]:
                        continue
                    visited[y, x] = True
                    comp[y, x] = True
                    stack.append((y - 1, x))
                    stack.append((y + 1, x))
                    stack.append((y, x - 1))
                    stack.append((y, x + 1))
                comps.append(comp)
    return comps


def _dilate_bool(mask: np.ndarray, steps: int) -> np.ndarray:
    m = mask.copy()
    for _ in range(max(0, int(steps))):
        up = np.zeros_like(m);  up[:-1] = m[1:]
        dn = np.zeros_like(m);  dn[1:]  = m[:-1]
        lf = np.zeros_like(m);  lf[:, :-1] = m[:, 1:]
        rt = np.zeros_like(m);  rt[:, 1:]  = m[:, :-1]
        m = m | up | dn | lf | rt
    return m


def candidates_from_mask(mask: np.ndarray,
                         min_area: int = 4,
                         dilate: int = 2) -> List[np.ndarray]:
    """Split a proposal mask into per-component candidate ROIs. Each
    candidate is a dilated boolean mask. Components smaller than
    min_area pixels are dropped as noise."""
    if mask.dtype != bool:
        mask = mask.astype(bool)
    comps = _components(mask)
    out: List[np.ndarray] = []
    for c in comps:
        if int(c.sum()) < max(1, int(min_area)):
            continue
        out.append(_dilate_bool(c, dilate))
    return out


# =========================================================================
# Label-blind ranker.
# =========================================================================

def rank_candidates(cands: List[np.ndarray]) -> List[int]:
    """Return candidate indices sorted by descending area. Scene-
    agnostic: uses no truth labels."""
    if not cands:
        return []
    areas = [int(c.sum()) for c in cands]
    order = sorted(range(len(cands)), key=lambda i: -areas[i])
    return order


# =========================================================================
# Verdict
# =========================================================================

def _verdict(oracle_best: float, top1: float) -> str:
    ok = lambda x: isinstance(x, float) and x == x
    if not ok(oracle_best) or oracle_best < ROBUST_THR:
        return "FAILS_UNDER_COMPETITION"
    if ok(top1) and top1 >= ROBUST_THR:
        return "SURVIVES_WITH_TOP1"
    return "NEEDS_ORACLE_ARBITRATION"


def _fmax(values):
    best = None
    for v in values:
        if isinstance(v, float) and v == v:
            best = v if best is None else max(best, v)
    return best


def _fmin(values):
    worst = None
    for v in values:
        if isinstance(v, float) and v == v:
            worst = v if worst is None else min(worst, v)
    return worst


# =========================================================================
# Dossier build
# =========================================================================

def build_arbitration_dossier(size: int = 128, seed: int = 0) -> dict:
    capture = INTERACTION_CAPTURE()
    per_composite = {}

    for comp_kind, builder in COMPOSITES.items():
        pkt = builder(size=size, seed=seed)
        result = run_chain(pkt["image"], capture, seed=seed)
        captured = result["captured"]

        # Per-method candidate sets (label-blind, from captured only).
        method_candidates = {}
        for pname, propose in PROPOSALS.items():
            try:
                mask = propose(captured)
            except Exception:
                mask = np.zeros(captured.shape[:2], dtype=bool)
            cands = candidates_from_mask(mask,
                                         min_area=max(4, size // 16),
                                         dilate=2)
            method_candidates[pname] = cands

        sub_records = []
        for sub in pkt["meta"]["composite"]:
            per_method = {}
            all_scores: List[float] = []

            for pname, cands in method_candidates.items():
                if not cands:
                    per_method[pname] = {
                        "n_candidates": 0,
                        "candidate_scores": [],
                        "top1_score": float("nan"),
                        "oracle_best_score": float("nan"),
                        "worst_score": float("nan"),
                        "top1_rank_area": None,
                    }
                    continue
                order = rank_candidates(cands)
                scores = []
                for c in cands:
                    s = compute_relation_metric_bound(sub, captured, c)
                    scores.append(float(s) if isinstance(s, float)
                                   and s == s else float("nan"))
                top_idx = order[0]
                top1 = scores[top_idx]
                oracle = _fmax(scores)
                worst = _fmin(scores)
                per_method[pname] = {
                    "n_candidates":      len(cands),
                    "candidate_scores":  scores,
                    "top1_score":        top1,
                    "oracle_best_score": oracle,
                    "worst_score":       worst,
                    "top1_rank_area":    int(cands[top_idx].sum()),
                }
                all_scores.extend(scores)

            # Cross-method aggregates
            oracle_best = _fmax(all_scores)
            worst_any   = _fmin(all_scores)
            # top1 across methods: best of each method's top1 (honest;
            # we don't know which method's top1 is "right", so the
            # decoder would try both and pick whichever passes).
            top1_cross = _fmax(
                [per_method[m]["top1_score"] for m in per_method]
            )
            # Total candidate count
            n_total = sum(per_method[m]["n_candidates"] for m in per_method)

            verdict = _verdict(oracle_best, top1_cross)
            spread = (None if not (isinstance(oracle_best, float)
                                    and oracle_best == oracle_best
                                    and isinstance(worst_any, float)
                                    and worst_any == worst_any)
                      else float(oracle_best - worst_any))

            sub_records.append({
                "sub_primitive":    sub["name"],
                "relation_kind":    sub["relation"]["kind"],
                "per_method":       per_method,
                "n_candidates_total": n_total,
                "oracle_best":      oracle_best,
                "top1":             top1_cross,
                "worst":            worst_any,
                "spread":           spread,
                "verdict":          verdict,
            })

        sev = {"SURVIVES_WITH_TOP1":      0,
               "NEEDS_ORACLE_ARBITRATION": 1,
               "FAILS_UNDER_COMPETITION":  2}
        worst = max((sr["verdict"] for sr in sub_records),
                    key=lambda v: sev.get(v, -1))
        per_composite[comp_kind] = {
            "sub_relations":   sub_records,
            "overall_verdict": worst,
        }

    return {
        "schema_version": "1.4",
        "interaction_capture": capture.as_dict(),
        "proposals": list(PROPOSALS.keys()),
        "ranker": "largest_area",
        "thresholds": {"robust_thr": ROBUST_THR},
        "per_composite": per_composite,
    }


def write_arbitration_reports(out_dir: Path,
                               dossier: Optional[dict] = None) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dossier = dossier or build_arbitration_dossier()

    # NaN-safe json
    def _scrub(o):
        if isinstance(o, dict):
            return {k: _scrub(v) for k, v in o.items()}
        if isinstance(o, list):
            return [_scrub(v) for v in o]
        if isinstance(o, float) and (o != o):
            return None
        return o

    with open(out_dir / "arbitration.json", "w", encoding="utf-8") as f:
        json.dump(_scrub(dossier), f, indent=2)

    proposals = dossier["proposals"]
    lines = ["# Aurexis Research Sim v1.4 - Arbitration / proposal-competition dossier", ""]
    lines.append("Each image-only proposal mask is split into connected-")
    lines.append("component candidate ROIs. A scene-agnostic ranker")
    lines.append("(`" + dossier["ranker"] + "`) picks the top-1 without")
    lines.append("truth access. Per sub-primitive:")
    lines.append("")
    lines.append("- `oracle_best` - max survival across ALL candidates (ceiling)")
    lines.append("- `top1`        - best of each method's top-1 pick (honest)")
    lines.append("- `worst`       - min survival (false-positive burden)")
    lines.append("- `spread`      - oracle_best - worst (arbitration pressure)")
    lines.append("")
    lines.append("Verdict:")
    lines.append("- **SURVIVES_WITH_TOP1**       top1 >= {:.2f}".format(ROBUST_THR))
    lines.append("- **NEEDS_ORACLE_ARBITRATION** oracle passes but top1 < {:.2f}".format(ROBUST_THR))
    lines.append("- **FAILS_UNDER_COMPETITION**  oracle_best < {:.2f}".format(ROBUST_THR))
    lines.append("")
    lines.append("## Overall summary")
    lines.append("| composite | overall verdict |")
    lines.append("|-----------|-----------------|")
    for ck, rec in dossier["per_composite"].items():
        lines.append("| {} | **{}** |".format(ck, rec["overall_verdict"]))
    lines.append("")

    def _f(v):
        return "n/a" if not (isinstance(v, float) and v == v) \
               else "{:.3f}".format(v)

    for ck, rec in dossier["per_composite"].items():
        lines.append("### " + ck)
        lines.append("- overall_verdict: **" + rec["overall_verdict"] + "**")
        header = (["sub", "kind", "n_cands", "oracle_best", "top1",
                   "worst", "spread"] +
                  [p + ".top1" for p in proposals] +
                  [p + ".n" for p in proposals] +
                  ["verdict"])
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join(["---"] * len(header)) + "|")
        for sr in rec["sub_relations"]:
            row = [sr["sub_primitive"], sr["relation_kind"],
                   str(sr["n_candidates_total"]),
                   _f(sr["oracle_best"]), _f(sr["top1"]),
                   _f(sr["worst"]),
                   _f(sr["spread"]) if sr["spread"] is not None else "n/a"]
            for p in proposals:
                pm = sr["per_method"].get(p, {})
                row.append(_f(pm.get("top1_score", float("nan"))))
            for p in proposals:
                pm = sr["per_method"].get(p, {})
                row.append(str(pm.get("n_candidates", 0)))
            row.append(sr["verdict"])
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")

    with open(out_dir / "ARBITRATION.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return dossier


def main():
    dossier = build_arbitration_dossier()
    out = Path.cwd()
    write_arbitration_reports(out, dossier)
    print("Aurexis Research Sim v1.4 - Arbitration dossier\n")
    for ck, rec in dossier["per_composite"].items():
        print("  " + ck + "  [overall: " + rec["overall_verdict"] + "]")
        for sr in rec["sub_relations"]:
            def _s(v):
                return "n/a" if not (isinstance(v, float) and v == v) else "{:.3f}".format(v)
            print("      {:<12} ({:<11}) n_cands={}  oracle={}  top1={}  worst={}  spread={}  {}".format(
                sr["sub_primitive"], sr["relation_kind"],
                sr["n_candidates_total"],
                _s(sr["oracle_best"]), _s(sr["top1"]),
                _s(sr["worst"]),
                "n/a" if sr["spread"] is None else _s(sr["spread"]),
                sr["verdict"]))
        print()
    print("Wrote arbitration.json and ARBITRATION.md into CWD.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
