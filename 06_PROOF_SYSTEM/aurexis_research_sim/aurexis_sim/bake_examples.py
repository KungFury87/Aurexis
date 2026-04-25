"""Bake example outputs from every shipped preset into examples/.

    python -m aurexis_sim.bake_examples
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

from . import truth as truth_mod
from . import metrics as metrics_mod
from .simulate import SimParams, run_chain
from .presets import list_presets, load_preset, params_from_preset
from .utils import save_png
from .color import is_rgb, luma
from .relations import relation_report
from .stress import stress_sweep, collapse_threshold, build_reports
from .atlas import write_atlas_reports, write_scenario_atlas_reports
from .validation import write_validation_reports
from .redesign import write_redesign_reports
from .interaction import write_interaction_reports
from .binding import write_binding_reports
from .soft_binding import write_soft_binding_reports
from .inferred_binding import write_inferred_binding_reports
from .arbitration import write_arbitration_reports
from .distractor_arbitration import write_distractor_arbitration_reports
from .fusion import write_fusion_reports
from .primitive_aware import write_primitive_aware_reports
from .coverage import write_coverage_reports
from .boundary import write_boundary_reports
from .unlock import write_unlock_reports
from .proof_taxonomy import write_taxonomy_reports
from .confidence import write_confidence_reports
from .semantic_stability import write_semantic_stability_reports
from .proof_index import write_proof_index_reports


ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"


def bake_one(name):
    preset = load_preset(name)
    kind = preset["truth"]["kind"]
    kwargs = preset["truth"]["kwargs"]
    params = params_from_preset(preset)
    seed = int(preset.get("seed", 0))

    truth_pkt = truth_mod.generate(kind, **kwargs)
    result = run_chain(truth_pkt["image"], params, seed=seed)
    out = EXAMPLES / name
    out.mkdir(parents=True, exist_ok=True)

    for stage, img in result["stages"].items():
        save_png(out / (stage + ".png"), img)
    save_png(out / "captured.png", result["captured"])
    save_png(out / "truth.png", truth_pkt["image"])

    metrics = metrics_mod.compute_all(truth_pkt, result["captured"])

    if kind.endswith("_probe"):
        try:
            rep = relation_report(truth_pkt, params, seed=seed)
            with open(out / "relation_report.json", "w", encoding="utf-8") as f:
                json.dump({k: (None if isinstance(v, float) and v != v else v)
                           for k, v in rep.items()}, f, indent=2)
            try:
                vals = [0.0, 0.5, 1.0, 2.0, 3.0, 5.0]
                curve = stress_sweep(kind, kwargs,
                                      lambda v: SimParams(blur_sigma=float(v)),
                                      vals, seed=seed)
                ct = collapse_threshold(curve, 0.5)
                with open(out / "stress_curve.json", "w", encoding="utf-8") as f:
                    json.dump({
                        "probe_kind": kind,
                        "sweep_param": "blur_sigma",
                        "curve": curve,
                        "collapse_at_0_5": list(ct) if ct else None,
                    }, f, indent=2)
            except Exception:
                pass
        except Exception as e:
            with open(out / "relation_report.json", "w", encoding="utf-8") as f:
                json.dump({"error": str(e)}, f, indent=2)

    safe = {k: (None if isinstance(v, float) and (v != v) else v)
            for k, v in metrics.items()}
    with open(out / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(safe, f, indent=2)
    with open(out / "preset.json", "w", encoding="utf-8") as f:
        json.dump(preset, f, indent=2)
    return safe


def _run_writer(name, fn):
    try:
        fn()
        print("wrote " + name)
    except Exception as e:
        print("warning: " + name + " failed: " + str(e))


def main():
    EXAMPLES.mkdir(parents=True, exist_ok=True)
    summary = {}
    for name in list_presets():
        print("baking: " + name)
        summary[name] = bake_one(name)
    with open(EXAMPLES / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    reports = ROOT / "reports"
    writers = [
        ("stress",                   lambda: build_reports(reports)),
        ("atlas",                    lambda: write_atlas_reports(reports)),
        ("scenario_atlas",           lambda: write_scenario_atlas_reports(reports)),
        ("validation",               lambda: write_validation_reports(reports)),
        ("redesign",                 lambda: write_redesign_reports(reports)),
        ("interaction",              lambda: write_interaction_reports(reports)),
        ("binding",                  lambda: write_binding_reports(reports)),
        ("soft_binding",             lambda: write_soft_binding_reports(reports)),
        ("inferred_binding",         lambda: write_inferred_binding_reports(reports)),
        ("arbitration",              lambda: write_arbitration_reports(reports)),
        ("distractor_arbitration",   lambda: write_distractor_arbitration_reports(reports)),
        ("fusion",                   lambda: write_fusion_reports(reports)),
        ("primitive_aware",          lambda: write_primitive_aware_reports(reports)),
        ("coverage",                 lambda: write_coverage_reports(reports)),
        ("boundary",                 lambda: write_boundary_reports(reports)),
        ("unlock",                   lambda: write_unlock_reports(reports)),
        ("proof_taxonomy",           lambda: write_taxonomy_reports(reports)),
        ("confidence",               lambda: write_confidence_reports(reports)),
        ("semantic_stability",       lambda: write_semantic_stability_reports(reports)),
        ("proof_index",              lambda: write_proof_index_reports(reports)),
    ]
    for name, fn in writers:
        _run_writer(name, fn)
    print("baked " + str(len(summary)) + " example sets")
    return 0


def _entry():
    return main()


if __name__ == "__main__":
    raise SystemExit(_entry())
# end of file padding
