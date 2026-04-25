"""Distractor realism / ranking brittleness evaluation (v1.5).

v1.4 split each proposal mask into connected-component candidates and
picked the top-1 by largest area. On the shipped composites the
intended region was conveniently bright and large, so top1 lined up
with oracle-best almost by construction.

v1.5 asks a harder question: when a wrong-but-plausible region
competes with the intended region, does the primitive still survive,
and do different reasonable ranking rules agree?

Two new ingredients:

  1. Distractor-rich composite probes where a decoy region is
     brighter / bigger / more-compact than the intended one:
       - composite_cardinality_with_decoy     (salience decoy)
       - composite_cardinality_ranker_split   (area vs salience vs compactness)
     (Label-scoped relations - ordering, adjacency, role_zone,
      orientation, hierarchy, symmetry - are ROI-insensitive and are
      NOT repeated here; v1.4 already trivially passes them.
      Repetition is NOT included either: `repetition_survival_bound`
      discards the spatial period when the ROI row-mask is not
      contiguous, which makes multi-band-at-same-row ROI-competition
      tests spurious. A metric fix is scheduled for v1.6.)

  2. Four label-blind rankers, all deterministic:
       - rank_by_area             (v1.4-compatible)
       - rank_by_mean_intensity   (salience)
       - rank_by_edge_density     (detail density)
       - rank_by_compactness      (blob-like first; perim^2/area)

Per sub-primitive we report:
  - oracle_best            max survival across ALL candidates
  - per_ranker_top1        top-1 survival under each ranker
  - ranker_disagreement    number of distinct top-1 indices across
                            rankers (>= 1)
  - distractor_burden      oracle_best - min(per_ranker_top1)
                            (bigger = more punishment for picking
                             the wrong candidate)
  - verdict:
      SURVIVES_UNDER_DISTRACTORS   all rankers' top1 >= 0.80
      RANKER_BRITTLE               oracle >= 0.80 and some but not
                                    all rankers pass
      DISTRACTOR_DOMINATED         oracle >= 0.80 but NO ranker passes
      FAILS_EVEN_ORACLE            oracle_best < 0.80 (inherited)

Honest scope (v1.5 still NOT claiming):
  - Four deterministic rankers. No learning, no geometry priors,
    no hierarchical grouping.
  - Two distractor composites only. A small, deliberate set meant to
    exercise salience-vs-correctness conflict, not a cover.
  - Still not a decoder, not E/D, not a runtime, not a camera app.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, List, Dict, Callable

import numpy as np

from .simulate import SimParams, run_chain, _convolve2d
from .sensor import SensorParams
from .interaction import INTERACTION_CAPTURE
from .binding import compute_relation_metric_bound, ROBUST_THR
from .inferred_binding import PROPOSALS
from .arbitration import candidates_from_mask
from .relations import _lum


# -------------------------------------------------------------------
# Distractor-rich composite probes
# -------------------------------------------------------------------

def composite_cardinality_with_decoy(size: int = 128, seed: int = 0) -> dict:
    """Intended: 3 moderate-brightness markers in the lower half.
    Decoy: 5 brighter, bigger markers tightly clustered in the upper
    half. Under area/intensity/edge ranking the decoy wins; under
    compactness the decoy blob is usually still preferred because of
    its lower aspect ratio.
    """
    img = np.full((size, size), 0.15, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    yy, xx = np.mgrid[0:size, 0:size]

    # Intended cluster: 3 markers packed tight so the proposal mask
    # yields one candidate spanning all 3.
    r_int = max(3, size // 32)
    int_y = int(size * 0.75)
    int_xs = [int(size * f) for f in (0.22, 0.32, 0.42)]
    for i, cx in enumerate(int_xs):
        m = (yy - int_y) ** 2 + (xx - cx) ** 2 <= r_int * r_int
        img[m] = 0.65
        lab[m] = 1 + i
    card_labels = np.where((lab >= 1) & (lab <= 3), lab, 0).astype(np.int32)

    # Decoy cluster: 5 bigger brighter markers tightly packed.
    r_dec = max(4, size // 22)
    dec_y = int(size * 0.25)
    dec_xs = [int(size * f) for f in (0.48, 0.56, 0.64, 0.72, 0.80)]
    for i, cx in enumerate(dec_xs):
        m = (yy - dec_y) ** 2 + (xx - cx) ** 2 <= r_dec * r_dec
        img[m] = 0.95
        lab[m] = 101 + i

    img = np.clip(img, 0.0, 1.0)
    return {
        "image": img,
        "labels": lab,
        "meta": {
            "relation": {"kind": "composite", "parts": ["cardinality"]},
            "composite": [
                {"name": "cardinality",
                 "labels": card_labels,
                 "relation": {"kind": "cardinality", "count": 3}},
            ],
        },
    }


def composite_cardinality_ranker_split(size: int = 128, seed: int = 0) -> dict:
    """Intended: 3 moderate-brightness markers spread into an elongated
    horizontal band (large merged area, less compact). Decoy: 4
    brighter tight-cluster markers (smaller total area, more compact,
    higher intensity). This exercises size vs salience vs compactness.
    """
    img = np.full((size, size), 0.15, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    yy, xx = np.mgrid[0:size, 0:size]

    # Intended: 3 markers close enough to merge under proposal dilation
    # but wide enough that the merged candidate is a long band.
    r_int = max(6, size // 28)
    int_y = int(size * 0.75)
    int_xs = [int(size * f) for f in (0.08, 0.20, 0.32)]
    for i, cx in enumerate(int_xs):
        m = (yy - int_y) ** 2 + (xx - cx) ** 2 <= r_int * r_int
        img[m] = 0.72
        lab[m] = 1 + i
    card_labels = np.where((lab >= 1) & (lab <= 3), lab, 0).astype(np.int32)

    # Decoy: 4 tight bright small markers (compact cluster).
    r_dec = max(5, size // 36)
    dec_y = int(size * 0.25)
    dec_xs = [int(size * f) for f in (0.62, 0.68, 0.74, 0.80)]
    for i, cx in enumerate(dec_xs):
        m = (yy - dec_y) ** 2 + (xx - cx) ** 2 <= r_dec * r_dec
        img[m] = 0.95
        lab[m] = 101 + i

    img = np.clip(img, 0.0, 1.0)
    return {
        "image": img,
        "labels": lab,
        "meta": {
            "relation": {"kind": "composite", "parts": ["cardinality"]},
            "composite": [
                {"name": "cardinality",
                 "labels": card_labels,
                 "relation": {"kind": "cardinality", "count": 3}},
            ],
        },
    }


DISTRACTOR_COMPOSITES: Dict[str, Callable[..., dict]] = {
    "composite_cardinality_with_decoy":    composite_cardinality_with_decoy,
    "composite_cardinality_ranker_split":  composite_cardinality_ranker_split,
}


# -------------------------------------------------------------------
# Label-blind rankers.
# -------------------------------------------------------------------

def _area_scores(cands: List[np.ndarray]) -> List[float]:
    return [float(c.sum()) for c in cands]


def _mean_intensity_scores(cands, captured):
    lum = _lum(captured); out = []
    for c in cands:
        out.append(float(lum[c].mean()) if int(c.sum()) > 0 else 0.0)
    return out


def _edge_density_scores(cands, captured):
    lum = _lum(captured)
    kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
    ky = kx.T
    gx = _convolve2d(lum, kx); gy = _convolve2d(lum, ky)
    g = np.sqrt(gx * gx + gy * gy)
    out = []
    for c in cands:
        out.append(float(g[c].mean()) if int(c.sum()) > 0 else 0.0)
    return out


def _compactness_scores(cands):
    out = []
    for c in cands:
        area = int(c.sum())
        if area <= 0:
            out.append(float("inf")); continue
        up = np.zeros_like(c);  up[:-1] = c[1:]
        dn = np.zeros_like(c);  dn[1:]  = c[:-1]
        lf = np.zeros_like(c);  lf[:, :-1] = c[:, 1:]
        rt = np.zeros_like(c);  rt[:, 1:]  = c[:, :-1]
        interior = c & up & dn & lf & rt
        perim = int((c & ~interior).sum())
        out.append((perim * perim) / float(max(1, area)))
    return out


def rank_by_area(cands, captured=None):
    if not cands: return []
    s = _area_scores(cands)
    return sorted(range(len(cands)), key=lambda i: -s[i])


def rank_by_mean_intensity(cands, captured):
    if not cands: return []
    s = _mean_intensity_scores(cands, captured)
    return sorted(range(len(cands)), key=lambda i: -s[i])


def rank_by_edge_density(cands, captured):
    if not cands: return []
    s = _edge_density_scores(cands, captured)
    return sorted(range(len(cands)), key=lambda i: -s[i])


def rank_by_compactness(cands, captured=None):
    if not cands: return []
    s = _compactness_scores(cands)
    return sorted(range(len(cands)), key=lambda i: s[i])


RANKERS: Dict[str, Callable] = {
    "area":           rank_by_area,
    "mean_intensity": rank_by_mean_intensity,
    "edge_density":   rank_by_edge_density,
    "compactness":    rank_by_compactness,
}


# -------------------------------------------------------------------
# Verdict + dossier
# -------------------------------------------------------------------

def _verdict(oracle_best, per_ranker_top1):
    ok = lambda x: isinstance(x, float) and x == x
    if not ok(oracle_best) or oracle_best < ROBUST_THR:
        return "FAILS_EVEN_ORACLE"
    total = sum(1 for v in per_ranker_top1.values() if ok(v))
    passes = sum(1 for v in per_ranker_top1.values()
                 if ok(v) and v >= ROBUST_THR)
    if total == 0:
        return "FAILS_EVEN_ORACLE"
    if passes == total:
        return "SURVIVES_UNDER_DISTRACTORS"
    if passes == 0:
        return "DISTRACTOR_DOMINATED"
    return "RANKER_BRITTLE"


def _fmax(values):
    best = None
    for v in values:
        if isinstance(v, float) and v == v:
            best = v if best is None else max(best, v)
    return best


def build_distractor_arbitration_dossier(size: int = 192,
                                          seed: int = 0) -> dict:
    capture = INTERACTION_CAPTURE()
    per_composite: Dict[str, dict] = {}

    for comp_kind, builder in DISTRACTOR_COMPOSITES.items():
        pkt = builder(size=size, seed=seed)
        result = run_chain(pkt["image"], capture, seed=seed)
        captured = result["captured"]

        all_cands: List[np.ndarray] = []
        method_tags: List[str] = []
        for pname, propose in PROPOSALS.items():
            try:
                mask = propose(captured)
            except Exception:
                mask = np.zeros(captured.shape[:2], dtype=bool)
            for c in candidates_from_mask(mask,
                                           min_area=max(4, size // 16),
                                           dilate=2):
                all_cands.append(c); method_tags.append(pname)

        sub_records = []
        for sub in pkt["meta"]["composite"]:
            if not all_cands:
                sub_records.append({
                    "sub_primitive": sub["name"],
                    "relation_kind": sub["relation"]["kind"],
                    "n_candidates":  0,
                    "oracle_best":   float("nan"),
                    "per_ranker_top1":     {},
                    "ranker_top1_idx":     {},
                    "ranker_disagreement": 0,
                    "distractor_burden":   None,
                    "verdict":             "FAILS_EVEN_ORACLE",
                })
                continue

            scores = []
            for c in all_cands:
                v = compute_relation_metric_bound(sub, captured, c)
                scores.append(float(v) if isinstance(v, float) and v == v
                              else float("nan"))
            oracle_best = _fmax(scores)

            per_ranker_top1: Dict[str, float] = {}
            ranker_top1_idx: Dict[str, int] = {}
            for rname, ranker in RANKERS.items():
                try:
                    order = ranker(all_cands, captured)
                except TypeError:
                    order = ranker(all_cands)
                if not order:
                    per_ranker_top1[rname] = float("nan")
                    ranker_top1_idx[rname] = -1
                    continue
                top = order[0]
                per_ranker_top1[rname] = scores[top]
                ranker_top1_idx[rname] = int(top)

            disagreement = len(set(ranker_top1_idx.values()))
            ok_vals = [v for v in per_ranker_top1.values()
                       if isinstance(v, float) and v == v]
            burden = None
            if ok_vals and isinstance(oracle_best, float) and oracle_best == oracle_best:
                burden = float(oracle_best - min(ok_vals))
            verdict = _verdict(oracle_best, per_ranker_top1)

            sub_records.append({
                "sub_primitive":       sub["name"],
                "relation_kind":       sub["relation"]["kind"],
                "n_candidates":        len(all_cands),
                "candidate_methods":   list(method_tags),
                "oracle_best":         oracle_best,
                "per_ranker_top1":     per_ranker_top1,
                "ranker_top1_idx":     ranker_top1_idx,
                "ranker_disagreement": disagreement,
                "distractor_burden":   burden,
                "verdict":             verdict,
            })

        sev = {"SURVIVES_UNDER_DISTRACTORS": 0,
               "RANKER_BRITTLE":             1,
               "DISTRACTOR_DOMINATED":       2,
               "FAILS_EVEN_ORACLE":          3}
        worst = max((sr["verdict"] for sr in sub_records),
                    key=lambda v: sev.get(v, -1))
        per_composite[comp_kind] = {
            "sub_relations":   sub_records,
            "overall_verdict": worst,
        }

    return {
        "schema_version": "1.5",
        "interaction_capture": capture.as_dict(),
        "rankers":   list(RANKERS.keys()),
        "proposals": list(PROPOSALS.keys()),
        "thresholds": {"robust_thr": ROBUST_THR},
        "per_composite": per_composite,
    }


def write_distractor_arbitration_reports(out_dir: Path,
                                          dossier: Optional[dict] = None) -> dict:
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    dossier = dossier or build_distractor_arbitration_dossier()

    def _scrub(o):
        if isinstance(o, dict):  return {k: _scrub(v) for k, v in o.items()}
        if isinstance(o, list):  return [_scrub(v) for v in o]
        if isinstance(o, float) and (o != o): return None
        return o

    with open(out_dir / "distractor_arbitration.json", "w", encoding="utf-8") as f:
        json.dump(_scrub(dossier), f, indent=2)

    rankers = dossier["rankers"]
    L = ["# Aurexis Research Sim v1.5 - Distractor-arbitration / ranking-brittleness dossier",
         "",
         "Two distractor-rich composites are evaluated. Per sub-primitive",
         "we union connected-component candidates across both image-only",
         "proposal methods and measure survival under four label-blind",
         "rankers: " + ", ".join("`" + r + "`" for r in rankers) + ".",
         "",
         "- `oracle_best`         max survival across all candidates",
         "- `per_ranker_top1`     survival at each ranker's top-1 pick",
         "- `ranker_disagreement` number of distinct top-1 indices across rankers",
         "- `distractor_burden`   oracle_best - min(per_ranker_top1)",
         "",
         "Verdict:",
         "- **SURVIVES_UNDER_DISTRACTORS**  all rankers' top1 >= {:.2f}".format(ROBUST_THR),
         "- **RANKER_BRITTLE**              oracle passes, some rankers fail",
         "- **DISTRACTOR_DOMINATED**        oracle passes, NO ranker passes",
         "- **FAILS_EVEN_ORACLE**           oracle_best < {:.2f}".format(ROBUST_THR),
         "",
         "## Overall summary",
         "| composite | overall verdict |",
         "|-----------|-----------------|"]
    for ck, rec in dossier["per_composite"].items():
        L.append("| {} | **{}** |".format(ck, rec["overall_verdict"]))
    L.append("")

    def _f(v):
        return "n/a" if not (isinstance(v, float) and v == v) else "{:.3f}".format(v)

    for ck, rec in dossier["per_composite"].items():
        L.append("### " + ck)
        L.append("- overall_verdict: **" + rec["overall_verdict"] + "**")
        header = ["sub", "kind", "n_cands", "oracle_best"] + \
                 [r + ".top1" for r in rankers] + ["disagree", "burden", "verdict"]
        L.append("| " + " | ".join(header) + " |")
        L.append("|" + "|".join(["---"] * len(header)) + "|")
        for sr in rec["sub_relations"]:
            row = [sr["sub_primitive"], sr["relation_kind"],
                   str(sr["n_candidates"]), _f(sr["oracle_best"])]
            for r in rankers:
                row.append(_f(sr["per_ranker_top1"].get(r, float("nan"))))
            row.append(str(sr["ranker_disagreement"]))
            row.append(_f(sr["distractor_burden"])
                       if sr["distractor_burden"] is not None else "n/a")
            row.append(sr["verdict"])
            L.append("| " + " | ".join(row) + " |")
        L.append("")

    with open(out_dir / "DISTRACTOR_ARBITRATION.md", "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return dossier


def main():
    dossier = build_distractor_arbitration_dossier()
    out = Path.cwd()
    write_distractor_arbitration_reports(out, dossier)
    tag = "Aurexis Research Sim v1.5 - Distractor-arbitration dossier"
    print(tag + "\n")
    for ck, rec in dossier["per_composite"].items():
        print("  " + ck + "  [overall: " + rec["overall_verdict"] + "]")
        for sr in rec["sub_relations"]:
            def _s(v):
                return ("n/a" if not (isinstance(v, float) and v == v)
                        else "{:.3f}".format(v))
            rtops = ", ".join(r + "=" + _s(sr["per_ranker_top1"].get(r))
                              for r in dossier["rankers"])
            bs = ("n/a" if sr["distractor_burden"] is None
                  else _s(sr["distractor_burden"]))
            msg = ("      {:<12} ({:<11}) n={}  oracle={}  {}  "
                   "disagree={}  burden={}  {}").format(
                sr["sub_primitive"], sr["relation_kind"],
                sr["n_candidates"], _s(sr["oracle_best"]),
                rtops, sr["ranker_disagreement"], bs, sr["verdict"])
            print(msg)
        print()
    print("Wrote distractor_arbitration.json and DISTRACTOR_ARBITRATION.md into CWD.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
