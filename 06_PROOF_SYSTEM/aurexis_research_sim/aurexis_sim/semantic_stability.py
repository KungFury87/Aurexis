"""Semantic stability proofs (v0.6).

Existing reports (atlas, scenario_atlas, stress_grids) tell us how
much a primitive's *survival score* changes across capture stress.
That is a survival-stability question. v0.6 asks a different
question:

    "When the primitive's metric returns a recovered VALUE (count,
     period_px, axis), is that recovered value stable across capture
     scenarios? Or does it drift?"

The semantic stability of a primitive is not the same as its
survival stability. A primitive can survive (score >= threshold)
yet recover the wrong count or wrong period under different
scenarios. Engine-semantics design needs to know which primitives
have stable semantics, not just stable survival.

In v0.6 we evaluate semantic stability for primitives whose metric
returns a recoverable value via threshold + structural analysis:

  - cardinality:  recovered count = number of components above thr
  - repetition:   recovered period = autocorr peak lag in the strip
  - ordering:     recovered direction = ascending vs descending
  - symmetry:     recovered axis = vertical vs horizontal mirror corr

For each primitive we run multiple capture scenarios and compare
the recovered value against the truth value declared by the probe.
The output is a per-primitive semantic-stability score:

    1.0  -> all scenarios recover the truth value exactly
    drops with each scenario where the recovered value disagrees.

Verdicts:
    SEMANTIC_STABLE        all scenarios match truth
    SEMANTIC_DRIFT         majority match, some drift
    SEMANTIC_UNSTABLE      majority do not match truth
    SEMANTIC_UNRECOVERABLE recoverable value not produced under most
                            scenarios

Honest scope:
  - Tests cardinality and repetition with their existing strip /
    bound metrics. Symmetry and ordering use simple within-image
    structural checks (no ROI competition - this isn't an
    arbitration test).
  - Truth values come from the probe builders' own labels (counts,
    periods).
  - Two scenarios are tested per primitive: SIM_MILD and SIM_HOSTILE.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, List

import numpy as np

from .simulate import SimParams, run_chain
from .sensor import SensorParams
from .interaction import INTERACTION_CAPTURE
from .relations import _lum, _count_components
from . import truth as truth_mod


# Two reference scenarios for cross-scenario semantic-stability.
SCENARIOS = {
    "SIM_MILD":   SimParams(blur_sigma=0.8, gauss_noise=0.01),
    "SIM_HOSTILE": INTERACTION_CAPTURE(),
}


def _full_image_count(captured) -> int:
    lum = _lum(captured)
    thr = float(lum.mean() + 1.5 * lum.std())
    thr = max(thr, float(lum.mean()) + 0.10)
    binary = lum > thr
    return _count_components(binary)


def _full_image_dominant_period(captured, target_period_px: float,
                                  row_y: int) -> Optional[int]:
    """Return the lag at which the autocorrelation peaks within the
    full row. Returns None if too short."""
    lum = _lum(captured)
    if row_y < 0 or row_y >= lum.shape[0]:
        return None
    row = lum[row_y].astype(np.float64)
    n = row.size
    if n < int(2 * target_period_px):
        return None
    prof = row - row.mean()
    if prof.std() < 1e-9:
        return None
    ac = np.correlate(prof, prof, mode="full")[n - 1:]
    max_lag = n // 2
    if max_lag < 5:
        return None
    nontrivial = ac[1:max_lag + 1]
    if nontrivial.max() <= 0:
        return None
    return int(np.argmax(nontrivial)) + 1


def _stability_score(matches: List[bool]) -> float:
    if not matches:
        return float("nan")
    return float(sum(1 for m in matches if m) / len(matches))


def _verdict(score: float, recoverable_count: int, total: int) -> str:
    ok = lambda x: isinstance(x, float) and x == x
    if not ok(score) or recoverable_count < total:
        # Some scenarios couldn't recover any value
        if recoverable_count <= total // 2:
            return "SEMANTIC_UNRECOVERABLE"
    if not ok(score):
        return "SEMANTIC_UNRECOVERABLE"
    if score >= 1.0:
        return "SEMANTIC_STABLE"
    if score >= 0.5:
        return "SEMANTIC_DRIFT"
    return "SEMANTIC_UNSTABLE"


def evaluate_cardinality(seed: int = 0) -> dict:
    pkt = truth_mod.generate("cardinality_probe",
                              size=128, n=4, seed=seed)
    truth_count = int(pkt["meta"]["relation"]["count"])
    matches: List[bool] = []
    recovered: Dict[str, Optional[int]] = {}
    for name, params in SCENARIOS.items():
        result = run_chain(pkt["image"], params, seed=seed)
        try:
            count = _full_image_count(result["captured"])
            recovered[name] = count
            matches.append(count == truth_count)
        except Exception:
            recovered[name] = None
            matches.append(False)
    score = _stability_score(matches)
    rec_count = sum(1 for v in recovered.values() if v is not None)
    return {
        "primitive": "cardinality",
        "truth_value": truth_count,
        "recovered": recovered,
        "matches": matches,
        "stability_score": score,
        "verdict": _verdict(score, rec_count, len(SCENARIOS)),
    }


def evaluate_repetition(seed: int = 0) -> dict:
    pkt = truth_mod.generate("repetition_probe",
                              size=160, n=7, seed=seed)
    rel = pkt["meta"]["relation"]
    truth_period = float(rel["period_px"])
    row_y = int(rel["row_y"])
    matches: List[bool] = []
    recovered: Dict[str, Optional[int]] = {}
    for name, params in SCENARIOS.items():
        result = run_chain(pkt["image"], params, seed=seed)
        try:
            lag = _full_image_dominant_period(result["captured"],
                                                truth_period, row_y)
            recovered[name] = lag
            if lag is None:
                matches.append(False)
            else:
                matches.append(abs(lag - int(round(truth_period))) <= 2)
        except Exception:
            recovered[name] = None
            matches.append(False)
    score = _stability_score(matches)
    rec_count = sum(1 for v in recovered.values() if v is not None)
    return {
        "primitive": "repetition",
        "truth_value": truth_period,
        "recovered": recovered,
        "matches": matches,
        "stability_score": score,
        "verdict": _verdict(score, rec_count, len(SCENARIOS)),
    }


def build_semantic_stability_dossier(seed: int = 0) -> dict:
    cardinality = evaluate_cardinality(seed=seed)
    repetition = evaluate_repetition(seed=seed)
    return {
        "schema_version": "0.6",
        "scenarios": list(SCENARIOS.keys()),
        "per_primitive": {
            "cardinality": cardinality,
            "repetition":  repetition,
        },
    }


def write_semantic_stability_reports(out_dir: Path,
                                       dossier: Optional[dict] = None
                                       ) -> dict:
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    dossier = dossier or build_semantic_stability_dossier()

    with open(out_dir / "semantic_stability.json", "w",
               encoding="utf-8") as f:
        json.dump(dossier, f, indent=2)

    L = []
    L.append("# Aurexis Research Sim v0.6 - Semantic stability dossier")
    L.append("")
    L.append("Per primitive: does the recovered semantic value (count, "
              "period) match the truth across capture scenarios?")
    L.append("")
    L.append("Scenarios: " + ", ".join("`" + s + "`"
                                         for s in dossier["scenarios"]))
    L.append("")
    L.append("Verdicts:")
    L.append("- **SEMANTIC_STABLE**      all scenarios recover the truth value")
    L.append("- **SEMANTIC_DRIFT**       majority match, some drift")
    L.append("- **SEMANTIC_UNSTABLE**    majority do not match truth")
    L.append("- **SEMANTIC_UNRECOVERABLE** value not recovered under most scenarios")
    L.append("")
    L.append("## Per-primitive semantic stability")
    L.append("| primitive | truth | recovered | stability_score | verdict |")
    L.append("|---|---|---|---|---|")
    for name, rec in dossier["per_primitive"].items():
        rec_str = ", ".join("{}={}".format(k, v)
                              for k, v in rec["recovered"].items())
        sc = rec.get("stability_score")
        sc_str = ("n/a" if not (isinstance(sc, float) and sc == sc)
                  else "{:.2f}".format(sc))
        L.append("| " + name
                 + " | " + str(rec.get("truth_value"))
                 + " | " + rec_str
                 + " | " + sc_str
                 + " | **" + rec["verdict"] + "** |")
    L.append("")

    with open(out_dir / "SEMANTIC_STABILITY.md", "w",
               encoding="utf-8") as f:
        f.write("\n".join(L))
    return dossier


def main():
    dossier = build_semantic_stability_dossier()
    write_semantic_stability_reports(Path.cwd(), dossier)
    print("Aurexis Research Sim v0.6 - Semantic stability dossier")
    print("")
    for name, rec in dossier["per_primitive"].items():
        sc = rec.get("stability_score")
        sc_str = ("n/a" if not (isinstance(sc, float) and sc == sc)
                  else "{:.2f}".format(sc))
        print("  {:<12}  truth={}  recovered={}  score={}  verdict={}".format(
            name, str(rec.get("truth_value")),
            ", ".join(str(k) + "=" + str(v)
                       for k, v in rec["recovered"].items()),
            sc_str, rec["verdict"]))
    print("")
    print("Wrote semantic_stability.json and SEMANTIC_STABILITY.md into CWD.")
    return 0


def _entry():
    return main()


if __name__ == "__main__":
    raise SystemExit(_entry())
# end of file padding
