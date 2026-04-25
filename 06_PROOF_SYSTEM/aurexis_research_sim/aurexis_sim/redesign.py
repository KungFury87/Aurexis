"""Primitive redesign / failure-attribution (v0.9).

v0.8 verdicts (SUSPECT, WEAK_ROBUST, NOT_ROBUST) tell you that a
promoted primitive failed. v0.9 tells you *why*, and suggests a
redesign direction.

Method:
  For each promoted primitive (ordering, repetition, role_zone) we:
    1. Take a baseline probe and measure its survival under a shared
       hostile capture (see `ATTRIBUTION_CAPTURE`).
    2. Generate 3 "challenge variants" that each reduce ONE property
       (contrast, spacing/period, marker scale, or crowding), holding
       everything else fixed.
    3. Compute sensitivity_i = baseline_survival - challenge_i_survival.
    4. Rank properties by sensitivity. Highest = dominant weakness.
    5. Map dominant weakness -> redesign direction via an explicit
       lookup.

Honest scope:
  - The properties tested are not exhaustive. Color coding, shape,
    rotation, motion-specific weaknesses are left for future passes.
  - "Dominant" only means "largest measured drop among the three
    tested challenges", not "the only cause".
  - Challenge variants are post-processed from the existing probes
    (intensity rescaling, parameter tweaks) rather than hand-crafted
    new probes, to keep the pass small and auditable.
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


# Shared hostile capture for attribution
def ATTRIBUTION_CAPTURE():
    return SimParams(
        blur_sigma=3.0, gauss_noise=0.05, rotate_deg=4.0,
        sensor=SensorParams(enabled=True, pattern="RGGB",
                            noise_r=0.040, noise_g=0.030, noise_b=0.040),
    )


# --- image post-processors used to build challenge variants -------------

def _rescale_toward(pkt: dict, factor: float) -> dict:
    """Compress intensities toward 0.5 by (1 - factor). Preserves labels
    and meta. Reduces effective contrast."""
    img = pkt["image"].astype(np.float32)
    new_img = 0.5 + (img - 0.5) * (1.0 - float(factor))
    new_img = np.clip(new_img, 0.0, 1.0)
    out = dict(pkt)
    out["image"] = new_img
    return out


# --- challenge-variant builders -----------------------------------------

def _ordering_challenges(size: int = 128):
    """Return list of (challenge_name, probe_pkt) for ordering."""
    out = []
    # baseline
    base = truth_mod.generate("ordering_probe_hard",
                               size=size, n=10)
    out.append(("baseline", base))
    # low_contrast: keep geometry, compress intensities toward 0.5
    out.append(("low_contrast",
                _rescale_toward(truth_mod.generate("ordering_probe_hard",
                                                     size=size, n=10),
                                 factor=0.75)))
    # tight_spacing: many more markers in the same span
    out.append(("tight_spacing",
                truth_mod.generate("ordering_probe_hard",
                                     size=size, n=14)))
    # small_markers: generate at smaller size so marker pixel radius
    # shrinks; still n=10
    out.append(("small_markers",
                truth_mod.generate("ordering_probe_hard",
                                     size=max(64, size // 2), n=10)))
    return out


def _repetition_challenges(size: int = 128):
    out = []
    base = truth_mod.generate("repetition_probe", size=size, n=7)
    out.append(("baseline", base))
    out.append(("low_contrast",
                _rescale_toward(truth_mod.generate("repetition_probe",
                                                     size=size, n=7),
                                 factor=0.70)))
    out.append(("tight_period",
                truth_mod.generate("repetition_probe_hard",
                                     size=size, n=16)))
    out.append(("small_markers",
                truth_mod.generate("repetition_probe",
                                     size=max(64, size // 2), n=7)))
    return out


def _role_zone_challenges(size: int = 128):
    out = []
    base = truth_mod.generate("role_zone_probe",
                                size=size, n_secondary=4)
    out.append(("baseline", base))
    out.append(("low_contrast",
                _rescale_toward(truth_mod.generate("role_zone_probe",
                                                     size=size, n_secondary=4),
                                 factor=0.80)))
    out.append(("many_secondaries",
                truth_mod.generate("role_zone_probe",
                                     size=size, n_secondary=10)))
    out.append(("tight_anchor_margin",
                truth_mod.generate("role_zone_probe_hard",
                                     size=size, n_secondary=6)))
    return out


CHALLENGES = {
    "ordering":   _ordering_challenges,
    "repetition": _repetition_challenges,
    "role_zone":  _role_zone_challenges,
}


# --- redesign suggestion lookup -----------------------------------------

REDESIGN_LOOKUP = {
    "low_contrast":
        "increase intensity separation OR encode with color / shape / "
        "spatial cue rather than intensity alone",
    "tight_spacing":
        "enforce a minimum spacing floor; reserve a coarser spatial "
        "frequency band; or add per-marker signatures that don't rely "
        "on spatial separation",
    "tight_period":
        "enforce a period floor (keep period >> PSF footprint); or "
        "encode repetition with aperiodic but countable cues",
    "small_markers":
        "require a minimum marker radius relative to expected PSF; "
        "scale-floor the primitive",
    "many_secondaries":
        "cap secondaries per anchor; OR give the anchor a distinctive "
        "independent cue (color, shape) that doesn't depend on count",
    "tight_anchor_margin":
        "widen anchor/companion contrast OR add a second cue "
        "(color, shape, position) so role survives when intensity "
        "contrast collapses",
}


# --- attribution --------------------------------------------------------

def _eval_survival(pkt: dict, params: SimParams, seed: int = 0) -> float:
    try:
        result = run_chain(pkt["image"], params, seed=seed)
        m = compute_relation_metrics(pkt, result["captured"])
        v = m.get("relation_survival", float("nan"))
        return float(v) if isinstance(v, float) and v == v else float("nan")
    except Exception:
        return float("nan")


def build_redesign_dossier(size: int = 128, seed: int = 0) -> dict:
    capture = ATTRIBUTION_CAPTURE()
    per_primitive = {}
    for name, builder in CHALLENGES.items():
        entries = builder(size=size)
        scores = {}
        for (cname, pkt) in entries:
            scores[cname] = _eval_survival(pkt, capture, seed=seed)
        baseline = scores.get("baseline", float("nan"))
        sensitivities = {}
        for cname, s in scores.items():
            if cname == "baseline":
                continue
            if isinstance(baseline, float) and baseline == baseline \
               and isinstance(s, float) and s == s:
                sensitivities[cname] = float(baseline - s)
            else:
                sensitivities[cname] = float("nan")
        # Rank: highest sensitivity = dominant weakness
        ranked = sorted(
            [(c, v) for c, v in sensitivities.items()
             if isinstance(v, float) and v == v],
            key=lambda kv: kv[1],
            reverse=True,
        )
        dominant = ranked[0][0] if ranked else None
        suggestion = REDESIGN_LOOKUP.get(dominant,
            "no clear dominant weakness from the 3 probed properties; "
            "expand property coverage (color, rotation, motion-specific) "
            "before drawing redesign conclusions")
        per_primitive[name] = {
            "baseline_survival_under_attribution_capture": baseline,
            "challenge_survivals": scores,
            "property_sensitivities": sensitivities,
            "ranked_properties":     ranked,
            "dominant_weakness":     dominant,
            "suggested_redesign":    suggestion,
        }

    return {
        "schema_version": "0.9",
        "attribution_capture": capture.as_dict(),
        "challenge_properties_per_primitive": {
            name: [c for (c, _p) in builder(size=size) if c != "baseline"]
            for name, builder in CHALLENGES.items()
        },
        "per_primitive": per_primitive,
    }


def write_redesign_reports(out_dir: Path,
                            dossier: Optional[dict] = None) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dossier = dossier or build_redesign_dossier()

    with open(out_dir / "redesign.json", "w", encoding="utf-8") as f:
        json.dump(dossier, f, indent=2)

    lines = ["# Aurexis Research Sim v0.9 - Primitive redesign dossier", ""]
    lines.append("For each promoted primitive we evaluate 3 property "
                 "challenges under a shared hostile capture and rank "
                 "properties by sensitivity (= baseline - challenge).")
    lines.append("")
    lines.append("## Redesign summary")
    lines.append("| primitive | baseline | dominant weakness | suggested redesign |")
    lines.append("|-----------|----------|-------------------|--------------------|")
    for name, rec in dossier["per_primitive"].items():
        b = rec["baseline_survival_under_attribution_capture"]
        bs = "n/a" if not (isinstance(b, float) and b == b) else "{:.3f}".format(b)
        lines.append("| {} | {} | {} | {} |".format(
            name, bs,
            rec["dominant_weakness"] or "unclear",
            rec["suggested_redesign"],
        ))
    lines.append("")

    for name, rec in dossier["per_primitive"].items():
        lines.append("### " + name)
        lines.append("- baseline_survival (hostile capture): "
                     + ("n/a" if not (isinstance(rec["baseline_survival_under_attribution_capture"], float)
                                      and rec["baseline_survival_under_attribution_capture"] == rec["baseline_survival_under_attribution_capture"])
                        else "{:.3f}".format(rec["baseline_survival_under_attribution_capture"])))
        lines.append("- challenge survivals:")
        for c, v in rec["challenge_survivals"].items():
            vs = "n/a" if not (isinstance(v, float) and v == v) else "{:.3f}".format(v)
            lines.append("    - " + c + ": " + vs)
        lines.append("- property sensitivities (baseline - challenge):")
        for c, v in rec["property_sensitivities"].items():
            vs = "n/a" if not (isinstance(v, float) and v == v) else "{:+.3f}".format(v)
            lines.append("    - " + c + ": " + vs)
        lines.append("- ranked_properties (most sensitive first):")
        for c, v in rec["ranked_properties"]:
            lines.append("    - {}: sensitivity={:+.3f}".format(c, v))
        lines.append("- dominant_weakness: **" + str(rec["dominant_weakness"]) + "**")
        lines.append("- suggested_redesign: " + rec["suggested_redesign"])
        lines.append("")

    with open(out_dir / "REDESIGN.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return dossier


def main():
    dossier = build_redesign_dossier()
    out = Path.cwd()
    write_redesign_reports(out, dossier)
    print("Aurexis Research Sim v0.9 - Primitive redesign dossier\n")
    for name, rec in dossier["per_primitive"].items():
        b = rec["baseline_survival_under_attribution_capture"]
        bs = "n/a" if not (isinstance(b, float) and b == b) else "{:.3f}".format(b)
        print("  " + name + ": baseline=" + bs)
        print("    dominant_weakness: " + str(rec["dominant_weakness"]))
        print("    suggested_redesign: " + rec["suggested_redesign"])
        print("    ranked properties:")
        for c, v in rec["ranked_properties"]:
            print("      {:<22} sensitivity {:+.3f}".format(c, v))
        print()
    print("Wrote redesign.json and REDESIGN.md into CWD.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
