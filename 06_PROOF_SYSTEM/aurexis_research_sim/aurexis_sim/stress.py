"""Relation-stress / discriminability + cross-stress cartography (v0.5).

v0.5 goes beyond single-axis sweeps. It adds:
  - `stress_grid_2d` — evaluate relation survival over a 2D grid of
    capture parameters so you can see the SHAPE of the collapse region,
    not just one slice.
  - Per-probe "right axis" sweeps — adjacency and ordering are
    geometrically robust to uniform blur; they collapse under noise or
    CFA mosaic noise. v0.5 sweeps the right axis for each probe.
  - `build_reports(out_dir)` — writes a packaged reports bundle
    (stress_report.json/csv, stress_grids.json, confusion_tables.json)
    so the delivered checkback zip actually ships the claimed artifacts.
"""
from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Iterable, Optional, Tuple

from .simulate import SimParams, run_chain
from .sensor import SensorParams
from . import truth as truth_mod
from .relations import compute_relation_metrics


# =========================================================================
# 1D sweep + collapse
# =========================================================================

def stress_sweep(probe_kind, probe_kwargs, params_builder, values, seed=0):
    """Sweep one parameter; return [(value, survival), ...]."""
    curve = []
    pkt = truth_mod.generate(probe_kind, **probe_kwargs)
    for v in values:
        params = params_builder(float(v))
        result = run_chain(pkt["image"], params, seed=seed)
        m = compute_relation_metrics(pkt, result["captured"])
        surv = m.get("relation_survival", float("nan"))
        curve.append((float(v), float(surv)))
    return curve


def collapse_threshold(curve, threshold=0.5):
    for v, s in curve:
        if isinstance(s, float) and s == s and s <= threshold:
            return (v, s)
    return None


def curve_is_monotone_nonincreasing(curve, tol=0.05):
    prev = None
    for _, s in curve:
        if not (isinstance(s, float) and s == s):
            continue
        if prev is not None and s > prev + tol:
            return False
        prev = s
    return True


# =========================================================================
# 2D stress grid (v0.5)
# =========================================================================

def stress_grid_2d(probe_kind: str, probe_kwargs: dict,
                   params_builder: Callable[[float, float], SimParams],
                   a_values: list, b_values: list,
                   seed: int = 0) -> dict:
    """Evaluate survival over (a, b) grid. Returns dict with:
        a_values, b_values, survival (2D list, rows=a, cols=b),
        collapse_region (fraction of cells with survival < 0.5).
    """
    pkt = truth_mod.generate(probe_kind, **probe_kwargs)
    matrix = []
    below = 0
    total = 0
    for a in a_values:
        row = []
        for b in b_values:
            p = params_builder(float(a), float(b))
            result = run_chain(pkt["image"], p, seed=seed)
            m = compute_relation_metrics(pkt, result["captured"])
            s = float(m.get("relation_survival", float("nan")))
            row.append(s)
            if s == s:
                total += 1
                if s < 0.5:
                    below += 1
        matrix.append(row)
    return {
        "probe_kind": probe_kind,
        "a_values": list(map(float, a_values)),
        "b_values": list(map(float, b_values)),
        "survival": matrix,
        "collapse_fraction_below_0_5": (below / total) if total else float("nan"),
    }


# =========================================================================
# Confusion table
# =========================================================================

DEFAULT_PROBE_KINDS_HARD = [
    "ordering_probe_hard",
    "adjacency_probe_hard",
    "symmetry_probe_hard",
    "orientation_probe_hard",
    "hierarchy_probe_hard",
]

DEFAULT_PROBE_KINDS_EASY = [
    "ordering_probe",
    "adjacency_probe",
    "symmetry_probe",
    "orientation_probe",
    "hierarchy_probe",
]


def relation_confusion_table(params, probe_kinds=None, size=128, seed=0):
    probe_kinds = probe_kinds or DEFAULT_PROBE_KINDS_HARD
    out = {}
    for kind in probe_kinds:
        try:
            pkt = truth_mod.generate(kind, size=size)
            result = run_chain(pkt["image"], params, seed=seed)
            m = compute_relation_metrics(pkt, result["captured"])
            out[kind] = float(m.get("relation_survival", float("nan")))
        except Exception:
            out[kind] = float("nan")
    return out


# =========================================================================
# Shipped sweeps — per-probe "right axis" selection (v0.5)
# =========================================================================

def _linspace(a, b, n):
    if n <= 1:
        return [float(a)]
    return [float(a + (b - a) * i / (n - 1)) for i in range(n)]


def _blur(v):                    return SimParams(blur_sigma=float(v))
def _noise(v):                   return SimParams(gauss_noise=float(v))
def _rotate(v):                  return SimParams(rotate_deg=float(v))
def _sensor_noise(v):            return SimParams(sensor=SensorParams(
    enabled=True, pattern="RGGB",
    noise_r=float(v), noise_g=float(v), noise_b=float(v)))
def _blur_plus_sensor_noise(b, n): return SimParams(
    blur_sigma=float(b),
    sensor=SensorParams(enabled=True, pattern="RGGB",
                         noise_r=float(n), noise_g=float(n), noise_b=float(n)))


# Shape: (name, probe_kind, probe_kwargs, builder, values, seed, axis_name)
SHIPPED_SWEEPS = [
    # v0.5 right-axis choices:
    #   ordering: noise is the killer
    #   adjacency: sensor mosaic noise is the killer (blur alone preserves equal partners)
    #   symmetry: rotation / perspective
    #   orientation: blur (structure-tensor collapse)
    #   hierarchy: noise (shuffles intra- vs inter-group distances)
    ("ordering_hard_vs_noise",       "ordering_probe_hard",
     {"size": 128, "n": 10}, _noise,        _linspace(0.0, 0.15, 7), 0, "gauss_noise"),
    ("adjacency_hard_vs_sensor_noise", "adjacency_probe_hard",
     {"size": 128, "n_pairs": 6}, _sensor_noise, _linspace(0.0, 0.08, 7), 0, "sensor_noise"),
    ("symmetry_hard_vs_rotate",      "symmetry_probe_hard",
     {"size": 128, "axis": "vertical"}, _rotate, _linspace(0.0, 12.0, 7), 0, "rotate_deg"),
    ("orientation_hard_vs_blur",     "orientation_probe_hard",
     {"size": 128, "n": 4}, _blur,           _linspace(0.0, 6.0, 7), 0, "blur_sigma"),
    ("hierarchy_hard_vs_noise",      "hierarchy_probe_hard",
     {"size": 128}, _noise,                  _linspace(0.0, 0.20, 7), 0, "gauss_noise"),
    # Keep the v0.4 blur sweep too so the integrity-check story is complete
    ("ordering_hard_vs_blur_info_only", "ordering_probe_hard",
     {"size": 128, "n": 10}, _blur,          _linspace(0.0, 6.0, 7), 0, "blur_sigma"),
]


# 2D grids: (name, probe_kind, probe_kwargs, builder(a,b), a_vals, b_vals, axis_a, axis_b, seed)
SHIPPED_GRIDS = [
    ("ordering_hard_blur_x_noise",     "ordering_probe_hard",   {"size": 128, "n": 10},
     _blur_plus_sensor_noise, _linspace(0.0, 3.0, 4), _linspace(0.0, 0.06, 4),
     "blur_sigma", "sensor_noise", 0),
    ("adjacency_hard_blur_x_sensornoise", "adjacency_probe_hard", {"size": 128, "n_pairs": 6},
     _blur_plus_sensor_noise, _linspace(0.0, 3.0, 4), _linspace(0.0, 0.08, 4),
     "blur_sigma", "sensor_noise", 0),
    ("hierarchy_hard_blur_x_sensornoise", "hierarchy_probe_hard", {"size": 128},
     _blur_plus_sensor_noise, _linspace(0.0, 3.0, 4), _linspace(0.0, 0.06, 4),
     "blur_sigma", "sensor_noise", 0),
]


# =========================================================================
# Reports
# =========================================================================

def build_reports(out_dir: Path) -> dict:
    """Build + write a shipped reports bundle.

    Writes:
      out_dir/stress_report.json
      out_dir/stress_report.csv
      out_dir/stress_grids.json
      out_dir/confusion_tables.json
      out_dir/SUMMARY.md
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sweeps_info = {}
    for (name, kind, kwargs, builder, values, seed, axis_name) in SHIPPED_SWEEPS:
        curve = stress_sweep(kind, kwargs, builder, values, seed=seed)
        c5 = collapse_threshold(curve, 0.5)
        c8 = collapse_threshold(curve, 0.8)
        sweeps_info[name] = {
            "probe_kind": kind,
            "axis": axis_name,
            "curve": curve,
            "collapse_at_0_5": list(c5) if c5 else None,
            "collapse_at_0_8": list(c8) if c8 else None,
            "monotone_nonincreasing": curve_is_monotone_nonincreasing(curve),
        }

    grids_info = {}
    for (name, kind, kwargs, builder, a_vals, b_vals, axis_a, axis_b, seed) in SHIPPED_GRIDS:
        g = stress_grid_2d(kind, kwargs, builder, a_vals, b_vals, seed=seed)
        g["axis_a"] = axis_a; g["axis_b"] = axis_b
        grids_info[name] = g

    mild = SimParams(blur_sigma=1.2, gauss_noise=0.015,
                     sensor=SensorParams(enabled=True, pattern="RGGB",
                                         noise_r=0.015, noise_g=0.010, noise_b=0.015))
    hostile = SimParams(blur_sigma=3.0, gauss_noise=0.05, rotate_deg=4.0,
                        sensor=SensorParams(enabled=True, pattern="RGGB",
                                            noise_r=0.04, noise_g=0.03, noise_b=0.04))
    confusion = {
        "mild_hard":    relation_confusion_table(mild, DEFAULT_PROBE_KINDS_HARD),
        "hostile_hard": relation_confusion_table(hostile, DEFAULT_PROBE_KINDS_HARD),
        "mild_easy":    relation_confusion_table(mild, DEFAULT_PROBE_KINDS_EASY),
        "hostile_easy": relation_confusion_table(hostile, DEFAULT_PROBE_KINDS_EASY),
    }

    report = {"sweeps": sweeps_info, "grids": grids_info, "confusion": confusion}

    with open(out_dir / "stress_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    with open(out_dir / "stress_report.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sweep", "probe_kind", "axis", "value", "relation_survival"])
        for name, info in sweeps_info.items():
            for v, s in info["curve"]:
                w.writerow([name, info["probe_kind"], info["axis"], v, s])

    with open(out_dir / "stress_grids.json", "w", encoding="utf-8") as f:
        json.dump(grids_info, f, indent=2)

    with open(out_dir / "confusion_tables.json", "w", encoding="utf-8") as f:
        json.dump(confusion, f, indent=2)

    # Human-readable summary
    lines = ["# Aurexis Research Sim v0.5 - shipped reports", ""]
    lines.append("## 1D sweeps (per-probe right axis)")
    for name, info in sweeps_info.items():
        c5 = info["collapse_at_0_5"]
        mark = "not reached" if not c5 else "collapse@0.5 at {}={:.3g} (surv={:.3f})".format(
            info["axis"], c5[0], c5[1])
        lines.append("- {:<38} [{}] axis={}: {}".format(
            name, info["probe_kind"], info["axis"], mark))
    lines.append("")
    lines.append("## 2D grids (collapse fraction below 0.5)")
    for name, g in grids_info.items():
        lines.append("- {:<40} [{}]  frac_below_0.5 = {:.2f}".format(
            name, g["probe_kind"], g.get("collapse_fraction_below_0_5", float("nan"))))
    lines.append("")
    lines.append("## Confusion tables (per-relation survival under shared capture)")
    for label, table in confusion.items():
        lines.append("### " + label)
        for k, v in table.items():
            vs = "n/a" if isinstance(v, float) and v != v else "{:.3f}".format(v)
            lines.append("- {:<28} {}".format(k, vs))
        lines.append("")
    with open(out_dir / "SUMMARY.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return report


# Backward-compat alias used by v0.4
def run_all_shipped_sweeps(out_dir: Optional[Path] = None) -> dict:
    out_dir = Path(out_dir) if out_dir else Path.cwd()
    return build_reports(out_dir)


def main():
    report = build_reports(Path.cwd())
    print("Aurexis Research Sim v0.5 - stress report\n")
    print("## 1D sweeps")
    for name, info in report["sweeps"].items():
        print("  " + name + " [" + info["probe_kind"] + "] axis=" + info["axis"])
        for v, s in info["curve"]:
            vs = "n/a" if isinstance(s, float) and s != s else format(s, ".3f")
            print("    val={:.4g}  surv={}".format(v, vs))
        c5 = info["collapse_at_0_5"]
        print("    collapse@0.5: " + (("val=" + format(c5[0], ".3g") +
              ", surv=" + format(c5[1], ".3f")) if c5 else "not reached"))
        print("    monotone_nonincreasing: " + str(info["monotone_nonincreasing"]))

    print("\n## 2D grids")
    for name, g in report["grids"].items():
        print("  " + name + " [" + g["probe_kind"] + "] " + g["axis_a"] + " x " + g["axis_b"])
        header = "   a\\b" + "".join(["  {:>6.3g}".format(b) for b in g["b_values"]])
        print(header)
        for i, a in enumerate(g["a_values"]):
            row = "   {:>5.3g}".format(a)
            for s in g["survival"][i]:
                row += "  " + ("  n/a " if isinstance(s, float) and s != s else "{:>6.3f}".format(s))
            print(row)
        print("   collapse_fraction_below_0_5={:.2f}".format(
            g.get("collapse_fraction_below_0_5", float("nan"))))

    print("\n## Confusion tables")
    for label, table in report["confusion"].items():
        print("  " + label)
        for k, v in table.items():
            vs = "n/a" if isinstance(v, float) and v != v else format(v, ".3f")
            print("    {:<28} {}".format(k, vs))
    print("\nWrote stress_report.json, stress_report.csv, stress_grids.json,")
    print("confusion_tables.json, and SUMMARY.md into CWD.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
