"""Promoted-primitive validation (v0.8).

For the three v0.7 STABLE_ROBUST primitives (ordering, repetition,
role_zone), this module runs:

  - the base probe under all five shipped scenarios,
  - a HARD variant under all five scenarios,
  - a set of NEGATIVE CONTROLS that should score low if the metric
    is meaningful.

From those three signals it emits a confidence verdict per primitive:

  EARNED_ROBUST   base >= robust_thr in every scenario AND
                  hard >= conditional_thr in every scenario AND
                  all negative controls <= neg_ctrl_max
  WEAK_ROBUST     base passes but hard falls below conditional_thr
                  in any scenario, negative controls still clean
  SUSPECT         any negative control scores > neg_ctrl_max
                  (metric is probably too forgiving)
  NOT_ROBUST      base drops below robust_thr in any scenario
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from . import truth as truth_mod
from .simulate import SimParams, run_chain
from .relations import compute_relation_metrics
from .atlas import DEFAULT_SCENARIOS


ROBUST_THR = 0.80
CONDITIONAL_THR = 0.50
NEG_CTRL_MAX = 0.50


# Promoted primitives -> their base probe, hard variant, and negative
# control list. The "hard" entry may be None if a hard variant exists
# only for some.
PROMOTED = {
    "ordering": {
        "base":     ("ordering_probe_hard", {"size": 128, "n": 10}),
        "hard":     ("ordering_probe_hard", {"size": 128, "n": 14}),
        "neg_ctrls": [
            ("scrambled_ordering_probe", {"size": 128, "n": 8}),
            ("null_relation_probe",
                {"size": 128, "relation_kind": "ordering"}),
        ],
    },
    "repetition": {
        "base":     ("repetition_probe",      {"size": 128, "n": 7}),
        "hard":     ("repetition_probe_hard", {"size": 128, "n": 12}),
        "neg_ctrls": [
            ("non_repetition_probe", {"size": 128, "n": 7}),
            ("null_relation_probe",
                {"size": 128, "relation_kind": "repetition"}),
        ],
    },
    "role_zone": {
        "base":     ("role_zone_probe",      {"size": 128, "n_secondary": 4}),
        "hard":     ("role_zone_probe_hard", {"size": 128, "n_secondary": 6}),
        "neg_ctrls": [
            ("equalized_role_zone_probe", {"size": 128, "n_secondary": 4}),
            ("null_relation_probe",
                {"size": 128, "relation_kind": "role_zone"}),
        ],
    },
}


def _run_under_scenarios(probe_kind: str, probe_kwargs: dict,
                         scenarios: dict, seed: int = 0) -> dict:
    out = {}
    pkt = truth_mod.generate(probe_kind, **probe_kwargs)
    for sname, params in scenarios.items():
        try:
            result = run_chain(pkt["image"], params, seed=seed)
            m = compute_relation_metrics(pkt, result["captured"])
            out[sname] = float(m.get("relation_survival", float("nan")))
        except Exception:
            out[sname] = float("nan")
    return out


def _eval_negative(probe_kind: str, probe_kwargs: dict, seed: int = 0) -> float:
    """Negative control: evaluate the metric on the probe's OWN identity
    image. If the probe is constructed to violate the claimed relation,
    the metric should return a low score."""
    pkt = truth_mod.generate(probe_kind, **probe_kwargs)
    m = compute_relation_metrics(pkt, pkt["image"])
    v = m.get("relation_survival", float("nan"))
    return float(v) if isinstance(v, float) and v == v else float("nan")


def _verdict(base_surv: dict, hard_surv: dict,
             neg_results: dict) -> str:
    base_all_pass = all(
        isinstance(v, float) and v == v and v >= ROBUST_THR
        for v in base_surv.values()
    )
    hard_all_pass = all(
        isinstance(v, float) and v == v and v >= CONDITIONAL_THR
        for v in hard_surv.values()
    )
    neg_all_clean = all(
        isinstance(v, float) and v == v and v <= NEG_CTRL_MAX
        for v in neg_results.values()
    )
    if not neg_all_clean:
        return "SUSPECT"
    if not base_all_pass:
        return "NOT_ROBUST"
    if not hard_all_pass:
        return "WEAK_ROBUST"
    return "EARNED_ROBUST"


def validate_promoted_primitives(scenarios: Optional[dict] = None,
                                  seed: int = 0) -> dict:
    scenarios = scenarios or DEFAULT_SCENARIOS
    out = {
        "schema_version": "0.8",
        "thresholds": {
            "robust_thr": ROBUST_THR,
            "conditional_thr": CONDITIONAL_THR,
            "neg_ctrl_max": NEG_CTRL_MAX,
        },
        "scenarios": list(scenarios.keys()),
        "per_primitive": {},
    }
    for name, cfg in PROMOTED.items():
        base_kind, base_kw = cfg["base"]
        hard_kind, hard_kw = cfg["hard"]
        base_surv = _run_under_scenarios(base_kind, base_kw, scenarios, seed=seed)
        hard_surv = _run_under_scenarios(hard_kind, hard_kw, scenarios, seed=seed)
        neg_results = {}
        for (nk, nkw) in cfg["neg_ctrls"]:
            key = nk + "::" + str(sorted(nkw.items()))
            neg_results[key] = _eval_negative(nk, nkw, seed=seed)
        verdict = _verdict(base_surv, hard_surv, neg_results)
        out["per_primitive"][name] = {
            "base_probe":  base_kind,
            "hard_probe":  hard_kind,
            "base_survival_per_scenario":  base_surv,
            "hard_survival_per_scenario":  hard_surv,
            "negative_control_results":    neg_results,
            "verdict": verdict,
        }
    return out


def write_validation_reports(out_dir: Path,
                              report: Optional[dict] = None) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = report or validate_promoted_primitives()

    with open(out_dir / "validation.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    lines = ["# Aurexis Research Sim v0.8 - Promoted-primitive validation", ""]
    thr = report["thresholds"]
    lines.append("Thresholds: base >= {:.2f} per scenario, "
                 "hard >= {:.2f} per scenario, "
                 "negative controls <= {:.2f}.".format(
                     thr["robust_thr"], thr["conditional_thr"],
                     thr["neg_ctrl_max"]))
    lines.append("")

    lines.append("## Verdict summary")
    lines.append("| primitive | base probe | hard probe | verdict |")
    lines.append("|-----------|------------|------------|---------|")
    for name, rec in report["per_primitive"].items():
        lines.append("| {} | {} | {} | **{}** |".format(
            name, rec["base_probe"], rec["hard_probe"], rec["verdict"]))
    lines.append("")

    for name, rec in report["per_primitive"].items():
        lines.append("### " + name)
        lines.append("- verdict: **" + rec["verdict"] + "**")
        lines.append("- base_probe: " + rec["base_probe"])
        lines.append("- hard_probe: " + rec["hard_probe"])
        lines.append("- base_survival_per_scenario:")
        for s, v in rec["base_survival_per_scenario"].items():
            vs = "n/a" if not (isinstance(v, float) and v == v) else "{:.3f}".format(v)
            lines.append("    - " + s + ": " + vs)
        lines.append("- hard_survival_per_scenario:")
        for s, v in rec["hard_survival_per_scenario"].items():
            vs = "n/a" if not (isinstance(v, float) and v == v) else "{:.3f}".format(v)
            lines.append("    - " + s + ": " + vs)
        lines.append("- negative_control_results:")
        for k, v in rec["negative_control_results"].items():
            vs = "n/a" if not (isinstance(v, float) and v == v) else "{:.3f}".format(v)
            lines.append("    - " + k + ": " + vs)
        lines.append("")

    with open(out_dir / "VALIDATION.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return report


def main():
    report = validate_promoted_primitives()
    out = Path.cwd()
    write_validation_reports(out, report)
    print("Aurexis Research Sim v0.8 - Promoted-primitive validation\n")
    for name, rec in report["per_primitive"].items():
        print("  " + name + ": " + rec["verdict"])
        print("    base  : " + ", ".join(
            s + "=" + ("n/a" if not (isinstance(v, float) and v == v)
                       else "{:.3f}".format(v))
            for s, v in rec["base_survival_per_scenario"].items()))
        print("    hard  : " + ", ".join(
            s + "=" + ("n/a" if not (isinstance(v, float) and v == v)
                       else "{:.3f}".format(v))
            for s, v in rec["hard_survival_per_scenario"].items()))
        print("    neg   : " + ", ".join(
            k.split("::")[0] + "=" + ("n/a" if not (isinstance(v, float) and v == v)
                                       else "{:.3f}".format(v))
            for k, v in rec["negative_control_results"].items()))
        print()
    print("Wrote validation.json and VALIDATION.md into CWD.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
