"""Compositional / interference evaluation (v1.0).

v0.1 - v0.9 evaluated each primitive in isolation. v1.0 adds composite
probes where two primitive families share the same field, and an
interaction evaluator that compares each constituent primitive's
survival in-composite vs alone.

Honest scope:
  - Three composite combinations are shipped. These are an initial
    set chosen to exercise crowding, binding, and contextual ambiguity;
    they are not a complete combinatorial cover.
  - "Interference" here is the numeric drop in a sub-relation's
    survival when it sits inside a composite vs alone; it is not a
    causal attribution.
  - We do not claim to have solved binding. We claim to have shipped
    a first measurement of how much two primitives interfere.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np

from . import truth as truth_mod
from .simulate import SimParams, run_chain
from .sensor import SensorParams
from .relations import compute_relation_metrics


# =========================================================================
# Composite probes
#
# Each composite returns the standard truth-packet shape (image, labels,
# meta) with an additional meta["composite"] entry: a list of
# sub-packets that each describe one constituent primitive's label
# subset + relation meta.
# =========================================================================

def composite_ordering_role_zone(size=256, seed=0):
    """Horizontal ranked markers in upper half (ordering, labels 1..6)
    AND a central anchor with companions in the lower half (role_zone,
    labels 101 anchor / 102..105 secondaries)."""
    rng = np.random.default_rng(seed)
    img = np.full((size, size), 0.15, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    yy, xx = np.mgrid[0:size, 0:size]

    # Ordering (upper half, row at y = size * 0.28)
    n_ord = 6
    ord_y = int(size * 0.28)
    r_ord = max(3, size // 50)
    ord_rank = {}
    for i in range(n_ord):
        frac = (i + 1) / (n_ord + 1)
        cx = int(size * (0.1 + 0.8 * frac))
        intensity = 0.25 + 0.65 * (i / max(1, n_ord - 1))
        m = (yy - ord_y) ** 2 + (xx - cx) ** 2 <= r_ord * r_ord
        img[m] = intensity
        lab[m] = i + 1
        ord_rank[i + 1] = i + 1
    ord_labels = np.where((lab >= 1) & (lab <= n_ord), lab, 0).astype(np.int32)

    # Role_zone (lower half, center around y = size * 0.72)
    anchor_y = int(size * 0.72)
    anchor_x = size // 2
    r_rz = max(3, size // 45)
    m_a = (yy - anchor_y) ** 2 + (xx - anchor_x) ** 2 <= r_rz * r_rz
    img[m_a] = 0.92
    lab[m_a] = 101
    R = max(r_rz * 4, size // 7)
    for i in range(4):
        theta = 2.0 * np.pi * i / 4
        sy = int(anchor_y + R * np.sin(theta) * 0.6)
        sx = int(anchor_x + R * np.cos(theta))
        m_s = (yy - sy) ** 2 + (xx - sx) ** 2 <= r_rz * r_rz
        img[m_s] = 0.55
        lab[m_s] = 102 + i
    rz_labels = np.where(lab >= 101, lab, 0).astype(np.int32)

    img += rng.normal(0.0, 0.005, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)

    return {
        "image": img, "labels": lab,
        "meta": {
            "kind": "composite_ordering_role_zone",
            "size": size, "seed": seed,
            "composite": [
                {"name": "ordering",  "labels": ord_labels,
                 "relation": {"kind": "ordering",
                              "rank_by_label": ord_rank}},
                {"name": "role_zone", "labels": rz_labels,
                 "relation": {"kind": "role_zone",
                              "anchor_label": 101,
                              "secondary_labels": [102, 103, 104, 105]}},
            ],
        },
    }


def composite_repetition_cardinality(size=256, seed=0):
    """Periodic markers on a row (repetition, labels 1..7) in the upper
    third AND a handful of random-placed markers in the lower half
    (cardinality, labels 201..)."""
    rng = np.random.default_rng(seed)
    img = np.full((size, size), 0.15, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    yy, xx = np.mgrid[0:size, 0:size]

    # Repetition row
    n_rep = 7
    row_y = int(size * 0.30)
    r_rep = max(3, size // 48)
    left = int(size * 0.1); right = int(size * 0.9)
    span = right - left
    period_px = span / max(1, n_rep - 1)
    for i in range(n_rep):
        cx = int(left + i * period_px)
        m = (yy - row_y) ** 2 + (xx - cx) ** 2 <= r_rep * r_rep
        img[m] = 0.88
        lab[m] = i + 1

    # Cardinality markers (lower half)
    n_card = 5
    r_card = max(3, size // 42)
    lower_pad = int(size * 0.55)
    placed = []; attempts = 0
    while len(placed) < n_card and attempts < 1000:
        attempts += 1
        cy = int(rng.integers(lower_pad + r_card + 2, size - r_card - 2))
        cx = int(rng.integers(r_card + 2, size - r_card - 2))
        if any(((cy - py) ** 2 + (cx - px) ** 2) < (2 * r_card + 6) ** 2
               for (py, px) in placed):
            continue
        placed.append((cy, cx))
    for i, (cy, cx) in enumerate(placed):
        m = (yy - cy) ** 2 + (xx - cx) ** 2 <= r_card * r_card
        img[m] = 0.88
        lab[m] = 201 + i

    img += rng.normal(0.0, 0.005, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)

    rep_labels = np.where((lab >= 1) & (lab <= n_rep), lab, 0).astype(np.int32)
    card_labels = np.where(lab >= 201, lab, 0).astype(np.int32)

    return {
        "image": img, "labels": lab,
        "meta": {
            "kind": "composite_repetition_cardinality",
            "size": size, "seed": seed,
            "composite": [
                {"name": "repetition",  "labels": rep_labels,
                 "relation": {"kind": "repetition",
                              "period_px": float(period_px),
                              "row_y": int(row_y)}},
                {"name": "cardinality", "labels": card_labels,
                 "relation": {"kind": "cardinality",
                              "count": int(len(placed))}},
            ],
        },
    }


def composite_ordering_crowded_by_adjacency(size=256, seed=0):
    """Ordered row of markers with paired-adjacency markers packed
    between them. Tests whether either primitive survives the
    crowding."""
    rng = np.random.default_rng(seed)
    img = np.full((size, size), 0.15, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    yy, xx = np.mgrid[0:size, 0:size]

    # Ordering row (labels 1..6)
    n_ord = 6
    ord_y = size // 2
    r_ord = max(3, size // 50)
    ord_rank = {}
    for i in range(n_ord):
        frac = (i + 1) / (n_ord + 1)
        cx = int(size * (0.1 + 0.8 * frac))
        intensity = 0.30 + 0.60 * (i / max(1, n_ord - 1))
        m = (yy - ord_y) ** 2 + (xx - cx) ** 2 <= r_ord * r_ord
        img[m] = intensity
        lab[m] = i + 1
        ord_rank[i + 1] = i + 1
    ord_labels = np.where((lab >= 1) & (lab <= n_ord), lab, 0).astype(np.int32)

    # Adjacency pairs (labels 11,12 / 13,14) placed between ordering markers
    r_adj = max(3, size // 52)
    pair_specs = [
        (int(size * 0.23), int(size * 0.45),    # cx pair center A, y pair center
         (11, 12), 0.55),
        (int(size * 0.57), int(size * 0.55),    # cx, y, labels, val
         (13, 14), 0.75),
    ]
    pair_gap = max(2 * r_adj + 3, size // 30)
    for (cx, cy, labels, val) in pair_specs:
        ax = cx - pair_gap // 2
        bx = cx + pair_gap // 2
        mA = (yy - cy) ** 2 + (xx - ax) ** 2 <= r_adj * r_adj
        mB = (yy - cy) ** 2 + (xx - bx) ** 2 <= r_adj * r_adj
        img[mA] = val
        img[mB] = val
        lab[mA] = labels[0]
        lab[mB] = labels[1]
    adj_labels = np.where((lab >= 11) & (lab <= 14), lab, 0).astype(np.int32)

    img += rng.normal(0.0, 0.005, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)

    return {
        "image": img, "labels": lab,
        "meta": {
            "kind": "composite_ordering_crowded_by_adjacency",
            "size": size, "seed": seed,
            "composite": [
                {"name": "ordering",  "labels": ord_labels,
                 "relation": {"kind": "ordering",
                              "rank_by_label": ord_rank}},
                {"name": "adjacency", "labels": adj_labels,
                 "relation": {"kind": "adjacency",
                              "pairs": [(11, 12), (13, 14)]}},
            ],
        },
    }


COMPOSITES = {
    "composite_ordering_role_zone":              composite_ordering_role_zone,
    "composite_repetition_cardinality":          composite_repetition_cardinality,
    "composite_ordering_crowded_by_adjacency":   composite_ordering_crowded_by_adjacency,
}


# =========================================================================
# Evaluation
# =========================================================================

def _eval_sub(captured, sub_entry: dict) -> float:
    """Evaluate one sub-relation's survival on the captured image using
    the sub-entry's labels + relation meta."""
    pkt = {
        "image": captured,     # required by metric shape but unused for these relations
        "labels": sub_entry["labels"],
        "meta": {"relation": sub_entry["relation"]},
    }
    m = compute_relation_metrics(pkt, captured)
    v = m.get("relation_survival", float("nan"))
    return float(v) if isinstance(v, float) and v == v else float("nan")


def _eval_alone(name: str, sub_entry: dict, params: SimParams,
                size: int = 128, seed: int = 0) -> float:
    """Evaluate the same relation on its isolated baseline probe for
    comparison."""
    # Map composite sub-name to a baseline probe kind
    baseline_map = {
        "ordering":    ("ordering_probe_hard", {"size": size, "n": 6}),
        "role_zone":   ("role_zone_probe",      {"size": size, "n_secondary": 4}),
        "repetition":  ("repetition_probe",     {"size": size, "n": 7}),
        "cardinality": ("cardinality_probe",    {"size": size, "n": 5}),
        "adjacency":   ("adjacency_probe",      {"size": size, "n_pairs": 2}),
    }
    if name not in baseline_map:
        return float("nan")
    kind, kw = baseline_map[name]
    pkt = truth_mod.generate(kind, **kw)
    result = run_chain(pkt["image"], params, seed=seed)
    m = compute_relation_metrics(pkt, result["captured"])
    v = m.get("relation_survival", float("nan"))
    return float(v) if isinstance(v, float) and v == v else float("nan")


def _flag(interference: float) -> str:
    if not (isinstance(interference, float) and interference == interference):
        return "UNKNOWN"
    if interference < 0.05:
        return "BINDING_OK"
    if interference < 0.30:
        return "CROWDING"
    return "BINDING_FAILURE"


# Shared moderate hostile capture for interaction evaluation
def INTERACTION_CAPTURE():
    return SimParams(
        blur_sigma=1.5, gauss_noise=0.02,
        sensor=SensorParams(enabled=True, pattern="RGGB",
                            noise_r=0.02, noise_g=0.015, noise_b=0.02),
    )


def build_interaction_dossier(size: int = 128, seed: int = 0) -> dict:
    capture = INTERACTION_CAPTURE()
    per_composite = {}
    for comp_kind, builder in COMPOSITES.items():
        pkt = builder(size=size, seed=seed)
        result = run_chain(pkt["image"], capture, seed=seed)
        captured = result["captured"]
        sub_records = []
        for sub in pkt["meta"]["composite"]:
            in_composite = _eval_sub(captured, sub)
            alone = _eval_alone(sub["name"], sub, capture,
                                 size=size, seed=seed)
            interference = (alone - in_composite
                            if isinstance(alone, float) and alone == alone
                            and isinstance(in_composite, float) and in_composite == in_composite
                            else float("nan"))
            sub_records.append({
                "sub_primitive":       sub["name"],
                "survival_in_composite": in_composite,
                "survival_alone":        alone,
                "interference":          interference,
                "flag":                  _flag(interference),
            })
        per_composite[comp_kind] = {
            "sub_relations": sub_records,
            "overall_flag":  _worst_flag([r["flag"] for r in sub_records]),
        }
    return {
        "schema_version": "1.0",
        "interaction_capture": capture.as_dict(),
        "per_composite": per_composite,
    }


_FLAG_SEVERITY = {
    "BINDING_OK": 0,
    "CROWDING": 1,
    "BINDING_FAILURE": 2,
    "UNKNOWN": -1,
}


def _worst_flag(flags):
    if not flags:
        return "UNKNOWN"
    ranked = sorted(flags, key=lambda f: _FLAG_SEVERITY.get(f, -1), reverse=True)
    return ranked[0]


def write_interaction_reports(out_dir: Path,
                               dossier: Optional[dict] = None) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dossier = dossier or build_interaction_dossier()

    # Labels arrays aren't JSON-serializable, but we already avoid writing
    # them out because sub_records don't carry them. Write structured JSON.
    with open(out_dir / "interaction.json", "w", encoding="utf-8") as f:
        json.dump(dossier, f, indent=2)

    lines = ["# Aurexis Research Sim v1.0 - Composite / interaction dossier", ""]
    lines.append("For each composite probe we evaluate each constituent "
                 "primitive's survival in-composite vs alone, under a "
                 "shared moderate hostile capture. Interference = "
                 "alone - in_composite. Flags: "
                 "BINDING_OK (< 0.05), CROWDING (< 0.30), BINDING_FAILURE (>= 0.30).")
    lines.append("")
    lines.append("## Overall summary")
    lines.append("| composite | overall flag |")
    lines.append("|-----------|--------------|")
    for ck, rec in dossier["per_composite"].items():
        lines.append("| {} | **{}** |".format(ck, rec["overall_flag"]))
    lines.append("")

    for ck, rec in dossier["per_composite"].items():
        lines.append("### " + ck)
        lines.append("- overall_flag: **" + rec["overall_flag"] + "**")
        lines.append("| sub_primitive | in_composite | alone | interference | flag |")
        lines.append("|---------------|--------------|-------|--------------|------|")
        for sr in rec["sub_relations"]:
            def _fmt(v):
                return ("n/a" if not (isinstance(v, float) and v == v)
                        else "{:+.3f}".format(v) if v < 0 or v > 0
                        else "{:.3f}".format(v))
            ic = sr["survival_in_composite"]; al = sr["survival_alone"]; it = sr["interference"]
            def _f(v):
                return "n/a" if not (isinstance(v, float) and v == v) else "{:.3f}".format(v)
            def _fi(v):
                return "n/a" if not (isinstance(v, float) and v == v) else "{:+.3f}".format(v)
            lines.append("| {} | {} | {} | {} | {} |".format(
                sr["sub_primitive"], _f(ic), _f(al), _fi(it), sr["flag"]))
        lines.append("")

    with open(out_dir / "INTERACTION.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return dossier


def main():
    dossier = build_interaction_dossier()
    out = Path.cwd()
    write_interaction_reports(out, dossier)
    print("Aurexis Research Sim v1.0 - Composite / interaction dossier\n")
    for ck, rec in dossier["per_composite"].items():
        print("  " + ck + "  [overall: " + rec["overall_flag"] + "]")
        for sr in rec["sub_relations"]:
            ic = sr["survival_in_composite"]; al = sr["survival_alone"]
            it = sr["interference"]
            ics = "n/a" if not (isinstance(ic, float) and ic == ic) else "{:.3f}".format(ic)
            als = "n/a" if not (isinstance(al, float) and al == al) else "{:.3f}".format(al)
            its = "n/a" if not (isinstance(it, float) and it == it) else "{:+.3f}".format(it)
            print("      {:<12} in_composite={}  alone={}  interference={}  {}".format(
                sr["sub_primitive"], ics, als, its, sr["flag"]))
        print()
    print("Wrote interaction.json and INTERACTION.md into CWD.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# Self-register composites into truth.REGISTRY
def _self_register():
    from . import truth as _t
    for name, fn in COMPOSITES.items():
        _t.REGISTRY[name] = fn
_self_register()
