"""Primitive survivability atlas + stage attribution (v0.6).

Consumes the v0.3 per-stage relation report, the v0.4 sweep machinery,
and the v0.5 2D grids / confusion tables, and synthesizes a research-
facing report:

  - classification per relation: ROBUST / CONDITIONAL / FRAGILE /
    HIGH-CONFUSION
  - stage_of_first_major_failure: earliest chain stage where the
    relation's survival drops below 0.8 (soft) and 0.5 (hard)
  - frontier per probe: right-axis collapse threshold + 2D grid
    collapse fraction where available
  - ranked fragility order under a shared hostile capture

Honest scope:
  - Thresholds are explicit numbers, not learned.
  - "HIGH-CONFUSION" flags a *near-tie* against at least one other
    relation under hostile capture (within a tolerance). It does not
    prove those relations are perceptually indistinguishable.
  - Atlas consumes existing reports; it does not rerun the whole chain
    from scratch beyond the per-probe relation report under one shared
    moderate capture.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .simulate import SimParams
from .sensor import SensorParams
from . import truth as truth_mod
from .relations import relation_report, compute_relation_metrics
from .stress import (
    SHIPPED_SWEEPS, SHIPPED_GRIDS,
    stress_sweep, stress_grid_2d, collapse_threshold,
    relation_confusion_table,
    DEFAULT_PROBE_KINDS_HARD, DEFAULT_PROBE_KINDS_EASY,
)


# =========================================================================
# Thresholds (explicit, documented)
# =========================================================================

MILD_ROBUST = 0.90
MILD_CONDITIONAL = 0.80
HOSTILE_ROBUST = 0.70
HOSTILE_CONDITIONAL = 0.40
CONFUSION_NEAR_TIE = 0.05         # |a - b| < this counts as a near-tie
SOFT_FAILURE = 0.80
HARD_FAILURE = 0.50


def _classify(mild: float, hostile: float) -> str:
    """Per-relation bucket based on mild + hostile hard-probe survival.

    Returns one of: ROBUST, CONDITIONAL, FRAGILE.
    HIGH-CONFUSION is a separate tag added by the caller.
    """
    if not (isinstance(mild, float) and mild == mild
            and isinstance(hostile, float) and hostile == hostile):
        return "UNKNOWN"
    if mild >= MILD_ROBUST and hostile >= HOSTILE_ROBUST:
        return "ROBUST"
    if mild >= MILD_CONDITIONAL and hostile >= HOSTILE_CONDITIONAL:
        return "CONDITIONAL"
    return "FRAGILE"


def _find_first_failure(trace: dict, threshold: float):
    """Return (stage_name, survival) for the first stage whose survival
    drops at/below threshold. None if it never does."""
    for stage, surv in trace.items():
        if isinstance(surv, float) and surv == surv and surv <= threshold:
            return (stage, float(surv))
    return None


# =========================================================================
# Per-probe right-axis collapse lookup
# =========================================================================

def _right_axis_collapses(seed: int = 0) -> dict:
    """Run every shipped 1D sweep once and return:
        { probe_kind: {axis, collapse_0_5, collapse_0_8, curve_tail} }
    Only the first (non-info-only) sweep entry per probe_kind is kept.
    """
    out = {}
    for (name, kind, kwargs, builder, values, seed_, axis) in SHIPPED_SWEEPS:
        if "info_only" in name:
            continue
        if kind in out:
            continue
        curve = stress_sweep(kind, kwargs, builder, values, seed=seed)
        out[kind] = {
            "axis": axis,
            "sweep_name": name,
            "collapse_at_0_5": collapse_threshold(curve, 0.5),
            "collapse_at_0_8": collapse_threshold(curve, 0.8),
            "curve_tail_survival": float(curve[-1][1]) if curve else float("nan"),
        }
    return out


def _grid_collapse_frac(seed: int = 0) -> dict:
    """Run each shipped 2D grid once, return {probe_kind: collapse_fraction}."""
    out = {}
    for (name, kind, kwargs, builder, a_vals, b_vals, axis_a, axis_b, seed_) in SHIPPED_GRIDS:
        g = stress_grid_2d(kind, kwargs, builder, a_vals, b_vals, seed=seed)
        out[kind] = {
            "grid_name": name,
            "axis_a": axis_a, "axis_b": axis_b,
            "collapse_fraction_below_0_5": g.get("collapse_fraction_below_0_5", float("nan")),
        }
    return out


# =========================================================================
# Shared moderate + hostile reference captures for stage attribution
# =========================================================================

def _moderate_capture():
    return SimParams(
        blur_sigma=1.5, gauss_noise=0.02,
        sensor=SensorParams(enabled=True, pattern="RGGB",
                            noise_r=0.02, noise_g=0.015, noise_b=0.02),
    )


def _mild_capture():
    return SimParams(
        blur_sigma=1.2, gauss_noise=0.015,
        sensor=SensorParams(enabled=True, pattern="RGGB",
                            noise_r=0.015, noise_g=0.010, noise_b=0.015),
    )


def _hostile_capture():
    return SimParams(
        blur_sigma=3.0, gauss_noise=0.05, rotate_deg=4.0,
        sensor=SensorParams(enabled=True, pattern="RGGB",
                            noise_r=0.04, noise_g=0.03, noise_b=0.04),
    )


# =========================================================================
# Atlas build
# =========================================================================

def build_atlas(seed: int = 0) -> dict:
    """Synthesize stress + confusion + per-stage data into an atlas dict."""
    mild = _mild_capture()
    hostile = _hostile_capture()
    moderate = _moderate_capture()

    mild_conf = relation_confusion_table(mild, DEFAULT_PROBE_KINDS_HARD, seed=seed)
    hostile_conf = relation_confusion_table(hostile, DEFAULT_PROBE_KINDS_HARD, seed=seed)

    right_axis = _right_axis_collapses(seed=seed)
    grid_frac = _grid_collapse_frac(seed=seed)

    # Near-tie confusion tags under hostile capture
    tags = {kind: [] for kind in DEFAULT_PROBE_KINDS_HARD}
    items = list(hostile_conf.items())
    for i, (ki, vi) in enumerate(items):
        for j, (kj, vj) in enumerate(items):
            if j <= i:
                continue
            if (isinstance(vi, float) and vi == vi
                and isinstance(vj, float) and vj == vj
                and abs(vi - vj) < CONFUSION_NEAR_TIE):
                tags[ki].append("HIGH-CONFUSION-vs:" + kj)
                tags[kj].append("HIGH-CONFUSION-vs:" + ki)

    # Per-relation record
    per_relation = {}
    for kind in DEFAULT_PROBE_KINDS_HARD:
        mild_s = mild_conf.get(kind, float("nan"))
        host_s = hostile_conf.get(kind, float("nan"))
        bucket = _classify(mild_s, host_s)

        # Stage attribution under moderate capture
        try:
            pkt = truth_mod.generate(kind, size=128)
            trace = relation_report(pkt, moderate, seed=seed)
        except Exception as _e:
            trace = {}
        soft = _find_first_failure(trace, SOFT_FAILURE)
        hard = _find_first_failure(trace, HARD_FAILURE)

        rec = {
            "classification": bucket,
            "tags": list(tags.get(kind, [])),
            "mild_hard_survival": float(mild_s) if mild_s == mild_s else None,
            "hostile_hard_survival": float(host_s) if host_s == host_s else None,
            "stage_first_below_0_8": (soft[0] if soft else None),
            "stage_first_below_0_5": (hard[0] if hard else None),
            "stage_trace_moderate": {
                k: (None if isinstance(v, float) and v != v else float(v))
                for k, v in trace.items()
            },
            "right_axis_frontier": right_axis.get(kind, {}),
            "grid_collapse_fraction": grid_frac.get(kind, {}),
        }
        per_relation[kind] = rec

    # Ranked fragility under hostile capture (lowest survival first)
    ranked = sorted(
        [(k, v["hostile_hard_survival"]) for k, v in per_relation.items()
         if v["hostile_hard_survival"] is not None],
        key=lambda kv: kv[1],
    )

    atlas = {
        "schema_version": "0.6",
        "thresholds": {
            "mild_robust": MILD_ROBUST,
            "mild_conditional": MILD_CONDITIONAL,
            "hostile_robust": HOSTILE_ROBUST,
            "hostile_conditional": HOSTILE_CONDITIONAL,
            "confusion_near_tie": CONFUSION_NEAR_TIE,
            "soft_failure": SOFT_FAILURE,
            "hard_failure": HARD_FAILURE,
        },
        "captures_used": {
            "mild":     mild.as_dict(),
            "moderate": moderate.as_dict(),
            "hostile":  hostile.as_dict(),
        },
        "per_relation": per_relation,
        "ranked_fragility_under_hostile": ranked,
        "mild_confusion":    mild_conf,
        "hostile_confusion": hostile_conf,
    }
    return atlas


# =========================================================================
# Atlas reports
# =========================================================================

def write_atlas_reports(out_dir: Path, atlas: Optional[dict] = None) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    atlas = atlas or build_atlas()

    with open(out_dir / "atlas.json", "w", encoding="utf-8") as f:
        json.dump(atlas, f, indent=2)

    # Human-readable markdown
    lines = ["# Aurexis Research Sim v0.6 - Primitive Survivability Atlas", ""]
    lines.append("Thresholds: mild>={:.2f}/hostile>={:.2f} -> ROBUST; "
                 "mild>={:.2f}/hostile>={:.2f} -> CONDITIONAL; else FRAGILE. "
                 "Near-tie < {:.2f} tagged HIGH-CONFUSION.".format(
                     MILD_ROBUST, HOSTILE_ROBUST,
                     MILD_CONDITIONAL, HOSTILE_CONDITIONAL,
                     CONFUSION_NEAR_TIE))
    lines.append("")
    lines.append("## Ranked fragility under hostile capture")
    lines.append("| rank | probe | hostile_hard_survival | classification |")
    lines.append("|------|-------|-----------------------|----------------|")
    for i, (kind, surv) in enumerate(atlas["ranked_fragility_under_hostile"]):
        rec = atlas["per_relation"][kind]
        lines.append("| {} | {} | {:.3f} | {} |".format(
            i + 1, kind, surv, rec["classification"]))
    lines.append("")
    lines.append("## Per-relation record")
    for kind, rec in atlas["per_relation"].items():
        lines.append("### " + kind)
        lines.append("- classification: **" + rec["classification"] + "**")
        if rec["tags"]:
            lines.append("- tags: " + ", ".join(rec["tags"]))
        ms = rec["mild_hard_survival"]; hs = rec["hostile_hard_survival"]
        lines.append("- mild_hard_survival: "
                     + ("n/a" if ms is None else "{:.3f}".format(ms)))
        lines.append("- hostile_hard_survival: "
                     + ("n/a" if hs is None else "{:.3f}".format(hs)))
        lines.append("- stage_first_below_0_8: "
                     + str(rec["stage_first_below_0_8"]))
        lines.append("- stage_first_below_0_5: "
                     + str(rec["stage_first_below_0_5"]))
        ra = rec["right_axis_frontier"]
        if ra:
            c5 = ra.get("collapse_at_0_5")
            lines.append("- right_axis ({}) collapse@0.5: {}".format(
                ra.get("axis", "?"),
                ("not reached" if not c5
                 else "val={:.3g} surv={:.3f}".format(c5[0], c5[1]))))
        gc = rec["grid_collapse_fraction"]
        if gc:
            lines.append("- grid ({}, {}) collapse fraction <0.5: {:.2f}".format(
                gc.get("axis_a", "?"), gc.get("axis_b", "?"),
                gc.get("collapse_fraction_below_0_5", float("nan"))))
        lines.append("")

    with open(out_dir / "ATLAS.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return atlas


def main():
    atlas = build_atlas()
    out = Path.cwd()
    write_atlas_reports(out, atlas)
    print("Aurexis Research Sim v0.6 - Primitive Survivability Atlas\n")
    print("Ranked fragility under hostile capture:")
    for i, (kind, surv) in enumerate(atlas["ranked_fragility_under_hostile"]):
        rec = atlas["per_relation"][kind]
        tag_s = (" [" + ",".join(rec["tags"]) + "]") if rec["tags"] else ""
        print("  {}. {:<24} {:.3f}  {}{}".format(
            i + 1, kind, surv, rec["classification"], tag_s))
    print("\nStage of first major failure (survival <= 0.5) under moderate capture:")
    for kind, rec in atlas["per_relation"].items():
        print("  {:<24} {}".format(kind, rec["stage_first_below_0_5"]))
    print("\nWrote atlas.json and ATLAS.md into CWD.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# =========================================================================
# v0.7 - scenario-conditioned atlas + language-relevant primitive coverage
#
# The v0.6 atlas used a single (mild, hostile) reference pair. v0.7 adds
# a scenario atlas that runs every probe under multiple named capture
# scenarios and reports whether a probe's classification stays stable
# across them or flips.
# =========================================================================

# Shipped named scenarios. Chosen to span "phone-like" and a couple of
# harder regimes without pretending to be real devices.
def scenario_phone_mild():
    return SimParams(
        blur_sigma=1.0, gauss_noise=0.01,
        sensor=SensorParams(enabled=True, pattern="RGGB",
                            noise_r=0.010, noise_g=0.008, noise_b=0.010),
    )


def scenario_phone_moderate():
    return SimParams(
        blur_sigma=1.5, gauss_noise=0.02,
        sensor=SensorParams(enabled=True, pattern="RGGB",
                            noise_r=0.020, noise_g=0.015, noise_b=0.020),
    )


def scenario_phone_hostile():
    return SimParams(
        blur_sigma=3.0, gauss_noise=0.05, rotate_deg=4.0,
        sensor=SensorParams(enabled=True, pattern="RGGB",
                            noise_r=0.040, noise_g=0.030, noise_b=0.040),
    )


def scenario_low_light():
    return SimParams(
        blur_sigma=1.2, exposure=0.6, gamma=1.3,
        gauss_noise=0.04, shot_noise=0.04, bit_depth=7,
        sensor=SensorParams(enabled=True, pattern="RGGB",
                            noise_r=0.035, noise_g=0.025, noise_b=0.035),
    )


def scenario_fast_motion():
    return SimParams(
        blur_sigma=0.8,
        motion_blur_len=9, motion_blur_angle=15.0,
        rolling_shutter_shift=6,
        gauss_noise=0.02,
        sensor=SensorParams(enabled=True, pattern="RGGB",
                            noise_r=0.020, noise_g=0.015, noise_b=0.020),
    )


DEFAULT_SCENARIOS = {
    "phone_mild":     scenario_phone_mild(),
    "phone_moderate": scenario_phone_moderate(),
    "phone_hostile":  scenario_phone_hostile(),
    "low_light":      scenario_low_light(),
    "fast_motion":    scenario_fast_motion(),
}


# Full atlas probe family (hard structural + v0.7 language-relevant)
ATLAS_PROBE_KINDS = list(DEFAULT_PROBE_KINDS_HARD) + [
    "repetition_probe",
    "cardinality_probe",
    "role_zone_probe",
]


# Classification from a single-scenario survival number. We use a
# looser bucket scheme here than v0.6's mild+hostile combination because
# we only have one number per cell.
def _classify_single(surv: float) -> str:
    if not (isinstance(surv, float) and surv == surv):
        return "UNKNOWN"
    if surv >= 0.80:
        return "ROBUST"
    if surv >= 0.50:
        return "CONDITIONAL"
    return "FRAGILE"


def build_scenario_atlas(scenarios: Optional[dict] = None,
                         probe_kinds: Optional[list] = None,
                         size: int = 128, seed: int = 0) -> dict:
    """Evaluate every probe under every named scenario.

    Returns a dict with:
      per_scenario: {scenario_name: {probe_kind: survival}}
      per_probe_classification: {probe_kind: {scenario_name: bucket}}
      stability_summary: per-probe stability metrics
    """
    scenarios = scenarios or DEFAULT_SCENARIOS
    probe_kinds = probe_kinds or ATLAS_PROBE_KINDS

    per_scenario = {}
    for sname, params in scenarios.items():
        per_scenario[sname] = relation_confusion_table(
            params, probe_kinds=probe_kinds, size=size, seed=seed
        )

    per_probe_classification = {}
    stability = {}
    for kind in probe_kinds:
        per_probe_classification[kind] = {}
        survivals = []
        buckets = []
        for sname in scenarios.keys():
            v = per_scenario[sname].get(kind, float("nan"))
            per_probe_classification[kind][sname] = _classify_single(v)
            if isinstance(v, float) and v == v:
                survivals.append(v)
                buckets.append(_classify_single(v))
        if not survivals:
            stability[kind] = {
                "robust_count": 0, "conditional_count": 0, "fragile_count": 0,
                "n_scenarios": 0, "range": None, "mean": None,
                "is_stable": False, "majority_bucket": "UNKNOWN",
                "stable_verdict": "UNKNOWN",
            }
            continue
        r_count = sum(1 for b in buckets if b == "ROBUST")
        c_count = sum(1 for b in buckets if b == "CONDITIONAL")
        f_count = sum(1 for b in buckets if b == "FRAGILE")
        counts = {"ROBUST": r_count, "CONDITIONAL": c_count, "FRAGILE": f_count}
        majority = max(counts.items(), key=lambda kv: kv[1])[0]
        total = len(buckets)
        is_stable = (counts[majority] == total)  # all same bucket
        # Stable verdict:
        if r_count == total:
            verdict = "STABLE_ROBUST"
        elif f_count == total:
            verdict = "STABLE_FRAGILE"
        elif is_stable and majority == "CONDITIONAL":
            verdict = "STABLE_CONDITIONAL"
        elif r_count >= total - 1 and f_count == 0:
            verdict = "MOSTLY_ROBUST"
        elif f_count >= total - 1 and r_count == 0:
            verdict = "MOSTLY_FRAGILE"
        else:
            verdict = "SCENARIO_DEPENDENT"
        stability[kind] = {
            "robust_count": r_count,
            "conditional_count": c_count,
            "fragile_count": f_count,
            "n_scenarios": total,
            "range": float(max(survivals) - min(survivals)),
            "mean": float(sum(survivals) / total),
            "is_stable": bool(is_stable),
            "majority_bucket": majority,
            "stable_verdict": verdict,
        }

    return {
        "schema_version": "0.7",
        "scenarios": {name: params.as_dict()
                      for name, params in scenarios.items()},
        "probe_kinds": probe_kinds,
        "per_scenario": per_scenario,
        "per_probe_classification": per_probe_classification,
        "stability_summary": stability,
    }


def write_scenario_atlas_reports(out_dir: Path,
                                  atlas: Optional[dict] = None) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    atlas = atlas or build_scenario_atlas()

    with open(out_dir / "scenario_atlas.json", "w", encoding="utf-8") as f:
        json.dump(atlas, f, indent=2)

    # Markdown summary
    probe_kinds = atlas["probe_kinds"]
    scenario_names = list(atlas["scenarios"].keys())
    lines = ["# Aurexis Research Sim v0.7 - Scenario-conditioned atlas", ""]
    lines.append("Scenarios: " + ", ".join(scenario_names))
    lines.append("")

    # Survival matrix
    lines.append("## Per-scenario relation survival")
    header = "| probe | " + " | ".join(scenario_names) + " |"
    sep = "|-------|" + "|".join(["---"] * len(scenario_names)) + "|"
    lines.append(header); lines.append(sep)
    for kind in probe_kinds:
        row = [kind]
        for sn in scenario_names:
            v = atlas["per_scenario"][sn].get(kind, float("nan"))
            row.append("n/a" if not (isinstance(v, float) and v == v)
                       else "{:.3f}".format(v))
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    # Bucket matrix
    lines.append("## Per-scenario classification")
    lines.append(header); lines.append(sep)
    for kind in probe_kinds:
        row = [kind]
        for sn in scenario_names:
            row.append(atlas["per_probe_classification"][kind].get(sn, "UNKNOWN"))
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    # Stability summary
    lines.append("## Stability summary")
    lines.append("| probe | majority | verdict | R/C/F | range | mean |")
    lines.append("|-------|----------|---------|-------|-------|------|")
    for kind in probe_kinds:
        s = atlas["stability_summary"][kind]
        rng = s.get("range"); mean = s.get("mean")
        lines.append("| {} | {} | {} | {}/{}/{} | {} | {} |".format(
            kind, s["majority_bucket"], s["stable_verdict"],
            s["robust_count"], s["conditional_count"], s["fragile_count"],
            ("n/a" if rng is None else "{:.3f}".format(rng)),
            ("n/a" if mean is None else "{:.3f}".format(mean)),
        ))
    lines.append("")

    with open(out_dir / "SCENARIO_ATLAS.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return atlas
