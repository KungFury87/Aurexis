"""Aurexis Research Sim v0.3 - Streamlit entrypoint.

Lives at the project root so Streamlit's script-dir sys.path behavior
resolves the aurexis_sim package cleanly.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np
import streamlit as st

from aurexis_sim import truth as truth_mod
from aurexis_sim import metrics as metrics_mod
from aurexis_sim.simulate import SimParams, run_chain
from aurexis_sim.sensor import SensorParams, BAYER_PATTERNS
from aurexis_sim.presets import (
    list_presets, load_preset, save_preset, preset_from_ui, log_run,
)
from aurexis_sim.utils import to_uint8
from aurexis_sim.color import is_rgb, luma
from aurexis_sim.relations import relation_report
from aurexis_sim.stress import stress_sweep, collapse_threshold, stress_grid_2d
from aurexis_sim.atlas import build_atlas, build_scenario_atlas
from aurexis_sim.validation import validate_promoted_primitives
from aurexis_sim.redesign import build_redesign_dossier
from aurexis_sim.interaction import build_interaction_dossier
from aurexis_sim.binding import build_binding_dossier
from aurexis_sim.soft_binding import build_soft_binding_dossier
from aurexis_sim.inferred_binding import build_inferred_binding_dossier
from aurexis_sim.arbitration import build_arbitration_dossier
from aurexis_sim.distractor_arbitration import build_distractor_arbitration_dossier
from aurexis_sim.fusion import build_fusion_dossier
from aurexis_sim.primitive_aware import build_primitive_aware_dossier
from aurexis_sim.coverage import build_coverage_dossier
from aurexis_sim.boundary import build_boundary_dossier
from aurexis_sim.unlock import build_unlock_dossier
from aurexis_sim.proof_index import build_proof_index


st.set_page_config(page_title="Aurexis Research Sim v0.6", layout="wide")

st.title("Aurexis Research Simulation Suite - v0.6 (Engine-semantics proof system)")
st.caption(
    "Local research harness. v0.6 reframes the suite as an Engine-"
    "semantics proof system organized around seven proof categories: "
    "VISUAL_RELATIONSHIP, PHOXEL_RASTER_LAW, SEMANTIC_STABILITY, "
    "CALIBRATION_CONFIDENCE, PHYSICAL_SIMULATION, REAL_EVIDENCE_ANCHORING, "
    "LANGUAGE_CONSTRUCTION. New v0.6 evidence: per-family confidence "
    "states (TRUST/HOLD/DOWNGRADE/REJECT/NEED_MORE_EVIDENCE), explicit "
    "semantic-stability metrics, and a master proof index. Upstream: "
    "all v0.1-v2.0 mechanisms preserved (relation probes, sensor path, "
    "stress sweeps, atlas, validation, redesign, interaction, binding, "
    "soft_binding, inferred_binding, arbitration, distractor_arbitration, "
    "fusion, primitive_aware, coverage, boundary, unlock). "
    "Not a runtime, not a camera app, not E/D work."
)


with st.sidebar:
    st.header("1. Truth plane")
    truth_kind = st.selectbox("Pattern", truth_mod.list_kinds(), index=0)
    size = st.select_slider("Size (px)",
                            options=[64, 128, 192, 256, 384, 512], value=256)

    tk_kwargs = {"size": int(size)}
    if truth_kind == "blocks":
        tk_kwargs["n"] = st.slider("Blocks per side", 2, 32, 8)
        tk_kwargs["seed"] = st.number_input("Seed", 0, 10000, 0, key="sB")
    elif truth_kind == "grid":
        tk_kwargs["cell"] = st.slider("Cell size", 4, 64, 16)
        tk_kwargs["line"] = st.slider("Line width", 1, 4, 1)
    elif truth_kind == "gradient":
        tk_kwargs["axis"] = st.selectbox("Axis", ["x", "y", "radial"], 0)
    elif truth_kind == "relation_probe":
        tk_kwargs["seed"] = st.number_input("Seed", 0, 10000, 0, key="sR")
    elif truth_kind == "phoxel_probe":
        tk_kwargs["cell"] = st.slider("Phoxel cell (px)", 2, 32, 8)
        tk_kwargs["seed"] = st.number_input("Seed", 0, 10000, 0, key="sP")
    elif truth_kind == "rgb_blocks":
        tk_kwargs["n"] = st.slider("Blocks per side", 2, 32, 8, key="rgbN")
        tk_kwargs["seed"] = st.number_input("Seed", 0, 10000, 0, key="sRGB")
    elif truth_kind == "color_relation_probe":
        tk_kwargs["seed"] = st.number_input("Seed", 0, 10000, 0, key="sCR")
    elif truth_kind == "ordering_probe":
        tk_kwargs["n"] = st.slider("Markers", 3, 10, 6)
        tk_kwargs["axis"] = st.selectbox("Axis",
                                          ["horizontal", "vertical"], 0)
        tk_kwargs["seed"] = st.number_input("Seed", 0, 10000, 0, key="sORD")
    elif truth_kind == "adjacency_probe":
        tk_kwargs["n_pairs"] = st.slider("Pairs", 2, 9, 4)
        tk_kwargs["seed"] = st.number_input("Seed", 0, 10000, 0, key="sADJ")
    elif truth_kind == "symmetry_probe":
        tk_kwargs["axis"] = st.selectbox("Axis",
                                          ["vertical", "horizontal"], 0)
        tk_kwargs["seed"] = st.number_input("Seed", 0, 10000, 0, key="sSYM")
    elif truth_kind == "orientation_probe":
        tk_kwargs["n"] = st.slider("Strokes", 2, 4, 4)
        tk_kwargs["seed"] = st.number_input("Seed", 0, 10000, 0, key="sORI")
    elif truth_kind == "hierarchy_probe":
        tk_kwargs["seed"] = st.number_input("Seed", 0, 10000, 0, key="sHIE")

    st.header("2. Capture parameters")

    with st.expander("Geometric", expanded=True):
        scale = st.slider("Scale", 0.1, 4.0, 1.0, 0.05)
        rotate_deg = st.slider("Rotate (deg)", -45.0, 45.0, 0.0, 0.5)
        perspective = st.slider("Perspective", 0.0, 0.4, 0.0, 0.01)

    with st.expander("Optical / motion", expanded=True):
        blur_sigma = st.slider("Gaussian blur sigma (px)", 0.0, 8.0, 0.0, 0.1)
        motion_blur_len = st.slider("Motion blur length (px)", 0, 31, 0, 1)
        motion_blur_angle = st.slider("Motion blur angle (deg)",
                                      -90.0, 90.0, 0.0, 1.0)
        rolling_shutter_shift = st.slider("Rolling-shutter shift (px)",
                                          0, 64, 0, 1)

    with st.expander("Photometric", expanded=True):
        exposure = st.slider("Exposure", 0.1, 3.0, 1.0, 0.05)
        gamma = st.slider("Gamma", 0.2, 3.0, 1.0, 0.05)
        contrast = st.slider("Contrast", 0.1, 2.0, 1.0, 0.05)

    with st.expander("Sensor path", expanded=True):
        sensor_enabled = st.checkbox(
            "Enable sensor path (CFA mosaic + demosaic)", value=False)
        sensor_pattern = st.selectbox("Bayer pattern",
                                      list(BAYER_PATTERNS), index=0)
        c1, c2, c3 = st.columns(3)
        with c1:
            blur_r = st.slider("PSF R", 0.0, 3.0, 0.0, 0.1)
            noise_r = st.slider("Noise R", 0.0, 0.1, 0.0, 0.005)
        with c2:
            blur_g = st.slider("PSF G", 0.0, 3.0, 0.0, 0.1)
            noise_g = st.slider("Noise G", 0.0, 0.1, 0.0, 0.005)
        with c3:
            blur_b = st.slider("PSF B", 0.0, 3.0, 0.0, 0.1)
            noise_b = st.slider("Noise B", 0.0, 0.1, 0.0, 0.005)

    with st.expander("Final noise / quantization", expanded=False):
        gauss_noise = st.slider("Gaussian noise (std)", 0.0, 0.2, 0.0, 0.005)
        shot_noise = st.slider("Shot noise scale", 0.0, 0.2, 0.0, 0.005)
        bit_depth = st.slider("Bit depth", 1, 12, 8, 1)

    seed = int(st.number_input("Capture seed", 0, 10000, 0))


sensor = SensorParams(
    enabled=sensor_enabled, pattern=sensor_pattern,
    blur_sigma_r=blur_r, blur_sigma_g=blur_g, blur_sigma_b=blur_b,
    noise_r=noise_r, noise_g=noise_g, noise_b=noise_b,
)
params = SimParams(
    scale=scale, rotate_deg=rotate_deg, perspective=perspective,
    blur_sigma=blur_sigma, motion_blur_len=motion_blur_len,
    motion_blur_angle=motion_blur_angle,
    rolling_shutter_shift=rolling_shutter_shift,
    exposure=exposure, gamma=gamma, contrast=contrast,
    gauss_noise=gauss_noise, shot_noise=shot_noise, bit_depth=bit_depth,
    sensor=sensor,
)


# Preset controls
tbar1, tbar2, tbar3 = st.columns([2, 2, 2])
with tbar1:
    existing = ["<none>"] + list_presets()
    sel = st.selectbox("Load preset", existing, index=0)
    if sel != "<none>":
        if st.button("Apply '" + sel + "'"):
            p = load_preset(sel)
            st.session_state["_loaded_preset"] = p
            st.info("Preset loaded. See 'Resolved params' panel below.")
with tbar2:
    save_name = st.text_input("Save current as preset name", "")
    if st.button("Save preset") and save_name.strip():
        preset = preset_from_ui(save_name.strip(), truth_kind,
                                tk_kwargs, params, seed)
        path = save_preset(preset, save_name.strip())
        st.success("Saved to " + str(path))
with tbar3:
    log_btn = st.button("LOG RUN TO DISK", use_container_width=True)


truth_pkt = truth_mod.generate(truth_kind, **tk_kwargs)
truth_img = truth_pkt["image"]
result = run_chain(truth_img, params, seed=seed)
captured = result["captured"]
metrics = metrics_mod.compute_all(truth_pkt, captured)
corr = metrics_mod.local_corruption_map(truth_img, captured, block=16)


def show(img, **kw):
    st.image(to_uint8(img), clamp=True, use_container_width=True, **kw)


col_a, col_b, col_c = st.columns(3)
with col_a:
    st.subheader("Source / truth"); show(truth_img)
with col_b:
    st.subheader("Simulated capture"); show(captured)
with col_c:
    st.subheader("Absolute difference (luma)")
    t_l = luma(truth_img) if is_rgb(truth_img) else truth_img.astype(np.float32)
    c_l = luma(captured) if is_rgb(captured) else captured.astype(np.float32)
    diff = np.abs(t_l - c_l)
    dm = diff.max() or 1.0
    show(diff / dm)

col_d, col_e = st.columns([2, 1])
with col_d:
    st.subheader("Local corruption map (luma per-block MSE, normalized)")
    show(corr)
with col_e:
    st.subheader("Metrics")
    for k, v in metrics.items():
        if isinstance(v, float) and v != v:
            st.write("**" + k + "**: n/a")
        elif isinstance(v, float):
            st.write("**" + k + "**: " + format(v, ".4f"))
        else:
            st.write("**" + k + "**: " + str(v))


# v0.3: per-stage relation report when the probe advertises a relation
rel = (truth_pkt.get("meta") or {}).get("relation") or {}
if rel.get("kind"):
    st.subheader("Per-stage relation report (v0.3)")
    st.caption("Relation: " + str(rel.get("kind")) +
               " - survival at each chain stage. 1.0 = relation preserved.")
    try:
        rep = relation_report(truth_pkt, params, seed=seed)
    except Exception as e:
        rep = {"error": str(e)}
    rows = []
    for stage, v in rep.items():
        if isinstance(v, float) and v != v:
            vs = "n/a"
        elif isinstance(v, float):
            vs = format(v, ".3f")
        else:
            vs = str(v)
        rows.append({"stage": stage, "relation_survival": vs})
    st.table(rows)

    # v0.4 stress curve: fixed blur sweep for the selected probe.
    st.subheader("Stress sweep (v0.4): relation survival vs blur_sigma")
    st.caption("Small fixed blur sweep. Look for the collapse point.")
    blur_vals = [0.0, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0]
    try:
        curve = stress_sweep(truth_kind, tk_kwargs,
                             lambda v: SimParams(blur_sigma=float(v)),
                             blur_vals, seed=seed)
        ct = collapse_threshold(curve, 0.5)
        rows2 = []
        for v, s in curve:
            rows2.append({
                "blur_sigma": format(v, ".2f"),
                "relation_survival": ("n/a" if (isinstance(s, float) and s != s)
                                       else format(s, ".3f")),
            })
        st.table(rows2)
        if ct:
            st.info("Collapse at 0.5: blur_sigma = " + format(ct[0], ".3g") +
                    ", survival = " + format(ct[1], ".3f"))
        else:
            st.info("Relation never drops to 0.5 in this sweep range.")
    except Exception as _e:
        st.warning("Stress sweep failed: " + str(_e))

    # v0.5 2D stress grid: blur_sigma x sensor_noise, small and fast.
    st.subheader("2D stress grid (v0.5): blur_sigma x sensor_noise")
    st.caption("Small 4x4 grid. Darker = lower relation survival.")
    try:
        a_vals = [0.0, 1.0, 2.0, 3.0]
        b_vals = [0.0, 0.02, 0.04, 0.06]
        def _builder(a, b):
            return SimParams(blur_sigma=float(a),
                             sensor=SensorParams(enabled=True, pattern="RGGB",
                                                 noise_r=float(b), noise_g=float(b),
                                                 noise_b=float(b)))
        g = stress_grid_2d(truth_kind, tk_kwargs, _builder, a_vals, b_vals, seed=seed)
        mat = g["survival"]
        header = ["blur\\sensor_n"] + [format(b, ".3f") for b in b_vals]
        rows3 = []
        for i, a in enumerate(a_vals):
            row = {"blur\\sensor_n": format(a, ".2f")}
            for j, b in enumerate(b_vals):
                s = mat[i][j]
                row[format(b, ".3f")] = ("n/a" if (isinstance(s, float) and s != s)
                                          else format(s, ".3f"))
            rows3.append(row)
        st.table(rows3)
        st.caption("collapse fraction (< 0.5): " + format(
            g.get("collapse_fraction_below_0_5", float("nan")), ".2f"))
    except Exception as _e:
        st.warning("Stress grid failed: " + str(_e))


if sensor_enabled:
    st.subheader("Sensor path intermediates")
    stages = result["stages"]
    s_cols = st.columns(4)
    keys = ["sensor_pre_cfa", "sensor_mosaic",
            "sensor_mosaic_noisy", "sensor_demosaiced"]
    labels = ["pre-CFA RGB", "mosaic (1 ch/px)",
              "mosaic + read noise", "bilinear demosaic"]
    for col, k, lbl in zip(s_cols, keys, labels):
        if k in stages:
            with col:
                st.caption(lbl); show(stages[k])


if is_rgb(captured):
    st.subheader("Per-channel (captured)")
    cols = st.columns(3)
    for c, (col, name) in enumerate(zip(cols, ("R", "G", "B"))):
        with col:
            st.caption(name); show(captured[..., c])


with st.expander("Stage inspector (all intermediates)", expanded=False):
    cols = st.columns(4)
    i = 0
    for name, img in result["stages"].items():
        with cols[i % 4]:
            st.caption(name); show(img)
        i += 1


with st.expander("Resolved params & loaded preset", expanded=False):
    st.json({
        "truth": {"kind": truth_kind, "kwargs": tk_kwargs},
        "params": params.as_dict(),
        "seed": seed,
    })
    if "_loaded_preset" in st.session_state:
        st.write("Last loaded preset:")
        st.json(st.session_state["_loaded_preset"])


if log_btn:
    preset = preset_from_ui(
        save_name.strip() or "run_" + truth_kind,
        truth_kind, tk_kwargs, params, seed,
    )
    run_dir = log_run(preset, truth_img, captured, metrics,
                      corruption_map=corr)
    st.success("Run logged to " + str(run_dir))


st.caption(
    "v0.3 scope: v0.2 chain + relation probes + per-probe survival + "
    "per-stage relation report. Not included: E/D work, decoder, "
    "language runtime, production camera sim."
)

# v0.6 primitive atlas: one-click synthesis from stress + confusion +
# per-stage data. Cached by Streamlit session state so repeated reruns
# don't rebuild unless the user requests it.
st.subheader("Primitive survivability atlas (v0.6)")
st.caption("Classifies hard relation probes by mild + hostile survival, "
           "and reports the stage where each relation first drops below 0.8 "
           "(moderate capture). Click to (re)build.")
if st.button("Build / refresh atlas"):
    with st.spinner("Running atlas (stress + confusion + per-stage)..."):
        st.session_state["_atlas"] = build_atlas(seed=0)
atl = st.session_state.get("_atlas")
if atl is not None:
    rows = []
    for i, (kind, surv) in enumerate(atl["ranked_fragility_under_hostile"]):
        rec = atl["per_relation"][kind]
        rows.append({
            "rank": i + 1,
            "probe": kind,
            "classification": rec["classification"],
            "mild": ("n/a" if rec["mild_hard_survival"] is None
                     else format(rec["mild_hard_survival"], ".3f")),
            "hostile": ("n/a" if rec["hostile_hard_survival"] is None
                        else format(rec["hostile_hard_survival"], ".3f")),
            "first<0.8": str(rec["stage_first_below_0_8"] or "-"),
            "first<0.5": str(rec["stage_first_below_0_5"] or "-"),
            "tags": ", ".join(rec["tags"]) if rec["tags"] else "",
        })
    st.table(rows)


# v0.7 scenario-conditioned atlas panel
st.subheader("Scenario-conditioned atlas (v0.7)")
st.caption("Evaluates every probe under several named capture scenarios "
           "and reports a stability verdict per probe.")
if st.button("Build / refresh scenario atlas"):
    with st.spinner("Running scenario atlas..."):
        st.session_state["_scenario_atlas"] = build_scenario_atlas(size=96)
satl = st.session_state.get("_scenario_atlas")
if satl is not None:
    rows = []
    for kind in satl["probe_kinds"]:
        s = satl["stability_summary"][kind]
        rng = s.get("range"); mean = s.get("mean")
        rows.append({
            "probe": kind,
            "verdict": s["stable_verdict"],
            "majority": s["majority_bucket"],
            "R/C/F": "{}/{}/{}".format(
                s["robust_count"], s["conditional_count"], s["fragile_count"]),
            "range": "n/a" if rng is None else format(rng, ".3f"),
            "mean":  "n/a" if mean is None else format(mean, ".3f"),
        })
    st.table(rows)


# v0.8 promoted-primitive validation panel
st.subheader("Promoted-primitive validation (v0.8)")
st.caption("Runs base + hard variants across 5 scenarios, plus negative "
           "controls. Emits a confidence verdict per promoted primitive.")
if st.button("Build / refresh validation"):
    with st.spinner("Running validation..."):
        st.session_state["_validation"] = validate_promoted_primitives()
val = st.session_state.get("_validation")
if val is not None:
    rows = []
    for name, rec in val["per_primitive"].items():
        rows.append({
            "primitive": name,
            "base_probe": rec["base_probe"],
            "hard_probe": rec["hard_probe"],
            "verdict": rec["verdict"],
            "hard_min_scenario_survival": min(
                (v for v in rec["hard_survival_per_scenario"].values()
                 if isinstance(v, float) and v == v),
                default=float("nan")),
            "worst_negative_control": max(
                (v for v in rec["negative_control_results"].values()
                 if isinstance(v, float) and v == v),
                default=float("nan")),
        })
    # coerce floats to nice strings
    for r in rows:
        for key in ("hard_min_scenario_survival", "worst_negative_control"):
            v = r[key]
            r[key] = ("n/a" if not (isinstance(v, float) and v == v)
                       else format(v, ".3f"))
    st.table(rows)


# v0.9 primitive redesign / failure-attribution panel
st.subheader("Primitive redesign dossier (v0.9)")
st.caption("For each promoted primitive, runs 3 property challenges under "
           "a shared hostile capture and ranks them by sensitivity. "
           "Outputs a suggested redesign direction.")
if st.button("Build / refresh redesign dossier"):
    with st.spinner("Running property-level challenges..."):
        st.session_state["_redesign"] = build_redesign_dossier()
dossier = st.session_state.get("_redesign")
if dossier is not None:
    rows = []
    for name, rec in dossier["per_primitive"].items():
        b = rec["baseline_survival_under_attribution_capture"]
        bs = "n/a" if not (isinstance(b, float) and b == b) else format(b, ".3f")
        rows.append({
            "primitive": name,
            "baseline": bs,
            "dominant_weakness": rec["dominant_weakness"] or "unclear",
            "suggested_redesign": rec["suggested_redesign"],
        })
    st.table(rows)


# v1.0 composite / interaction panel
st.subheader("Composite interaction dossier (v1.0)")
st.caption("Places two primitive families in the same field and measures "
           "how much each primitive's survival drops vs isolation. "
           "Flags: BINDING_OK, CROWDING, BINDING_FAILURE.")
if st.button("Build / refresh interaction dossier"):
    with st.spinner("Running composites..."):
        st.session_state["_interaction"] = build_interaction_dossier()
inter = st.session_state.get("_interaction")
if inter is not None:
    rows = []
    for ck, rec in inter["per_composite"].items():
        for sr in rec["sub_relations"]:
            ic = sr["survival_in_composite"]; al = sr["survival_alone"]; it = sr["interference"]
            rows.append({
                "composite": ck,
                "overall": rec["overall_flag"],
                "sub_primitive": sr["sub_primitive"],
                "in_composite": "n/a" if not (isinstance(ic, float) and ic == ic) else format(ic, ".3f"),
                "alone":        "n/a" if not (isinstance(al, float) and al == al) else format(al, ".3f"),
                "interference": "n/a" if not (isinstance(it, float) and it == it) else format(it, ".3f"),
                "flag":         sr["flag"],
            })
    st.table(rows)


# v1.1 scene-scoped binding panel
st.subheader("Scene-scoped binding dossier (v1.1)")
st.caption("For each composite sub-primitive: unbound (global metric) vs "
           "bound (ROI from labels) survival. Verdict: SURVIVES_GLOBAL / "
           "NEEDS_BINDING / FAILS_EVEN_BOUND.")
if st.button("Build / refresh binding dossier"):
    with st.spinner("Running ROI-aware evaluation..."):
        st.session_state["_binding"] = build_binding_dossier()
bdos = st.session_state.get("_binding")
if bdos is not None:
    rows = []
    for ck, rec in bdos["per_composite"].items():
        for sr in rec["sub_relations"]:
            u = sr["unbound_survival"]; b = sr["bound_survival"]; bb = sr["binding_boost"]
            rows.append({
                "composite": ck,
                "overall":   rec["overall_verdict"],
                "sub":       sr["sub_primitive"],
                "kind":      sr["relation_kind"],
                "unbound":   "n/a" if not (isinstance(u, float) and u == u) else format(u, ".3f"),
                "bound":     "n/a" if not (isinstance(b, float) and b == b) else format(b, ".3f"),
                "boost":     "n/a" if not (isinstance(bb, float) and bb == bb) else format(bb, "+.3f"),
                "verdict":   sr["verdict"],
                "tags":      ", ".join(sr["tags"]) if sr["tags"] else "",
            })
    st.table(rows)


# v1.2 soft-binding panel
st.subheader("Soft-binding dossier (v1.2)")
st.caption("Evaluates each composite sub-primitive under the perfect ROI "
           "plus four imperfect-ROI modes (dilate_extra, erode, shift_px, "
           "noisy_10pct). Verdicts: ROBUST_TO_SOFT_BINDING, "
           "NEEDS_TIGHT_BINDING, FAILS_EVEN_PERFECT.")
if st.button("Build / refresh soft-binding dossier"):
    with st.spinner("Running imperfect-ROI evaluation..."):
        st.session_state["_soft_binding"] = build_soft_binding_dossier()
sbd = st.session_state.get("_soft_binding")
if sbd is not None:
    rows = []
    modes = sbd["soft_modes"]
    for ck, rec in sbd["per_composite"].items():
        for sr in rec["sub_relations"]:
            row = {"composite": ck, "overall": rec["overall_verdict"],
                   "sub": sr["sub_primitive"], "kind": sr["relation_kind"]}
            for m in modes:
                v = sr["mode_survival"].get(m)
                row[m] = "n/a" if not (isinstance(v, float) and v == v) else format(v, ".3f")
            row["verdict"] = sr["verdict"]
            rows.append(row)
    st.table(rows)


# v1.3 inferred-binding panel
st.subheader("Inferred-binding dossier (v1.3)")
st.caption("Two image-only ROI proposals per sub-primitive "
           "(propose_threshold, propose_edges). Verdicts: "
           "SURVIVES_WITH_INFERENCE / NEEDS_TIGHT_INFERENCE / FAILS_EVEN_PERFECT.")
if st.button("Build / refresh inferred-binding dossier"):
    with st.spinner("Running image-only proposals..."):
        st.session_state["_inferred_binding"] = build_inferred_binding_dossier()
ibd = st.session_state.get("_inferred_binding")
if ibd is not None:
    rows = []
    for ck, rec in ibd["per_composite"].items():
        for sr in rec["sub_relations"]:
            def _s(v):
                return "n/a" if not (isinstance(v, float) and v == v) else format(v, ".3f")
            row = {"composite": ck, "overall": rec["overall_verdict"],
                   "sub": sr["sub_primitive"], "kind": sr["relation_kind"],
                   "unbound":  _s(sr["unbound"]),
                   "perfect":  _s(sr["perfect"]),
                   "soft_worst": _s(sr["soft_worst"])}
            for p in ibd["proposals"]:
                row[p] = _s(sr["inferred"].get(p, float("nan")))
            row["best_inferred"] = _s(sr["best_inferred"])
            row["best_proposal"] = str(sr["best_proposal"])
            row["verdict"] = sr["verdict"]
            rows.append(row)
    st.table(rows)


# v1.4 arbitration / proposal competition panel
st.subheader("Arbitration / proposal-competition dossier (v1.4)")
st.caption("Each image-only proposal mask is split into connected-component "
           "candidates; a label-blind largest-area ranker picks top-1. "
           "Verdicts: SURVIVES_WITH_TOP1 / NEEDS_ORACLE_ARBITRATION / "
           "FAILS_UNDER_COMPETITION.")
if st.button("Build / refresh arbitration dossier"):
    with st.spinner("Generating candidates and arbitrating..."):
        st.session_state["_arbitration"] = build_arbitration_dossier()
abd = st.session_state.get("_arbitration")
if abd is not None:
    rows = []
    for ck, rec in abd["per_composite"].items():
        for sr in rec["sub_relations"]:
            def _s(v):
                return "n/a" if not (isinstance(v, float) and v == v) else format(v, ".3f")
            row = {"composite": ck, "overall": rec["overall_verdict"],
                   "sub": sr["sub_primitive"], "kind": sr["relation_kind"],
                   "n_cands":     str(sr["n_candidates_total"]),
                   "oracle_best": _s(sr["oracle_best"]),
                   "top1":        _s(sr["top1"]),
                   "worst":       _s(sr["worst"]),
                   "spread":      _s(sr["spread"]) if sr["spread"] is not None else "n/a"}
            for p in abd["proposals"]:
                pm = sr["per_method"].get(p, {})
                row[p + ".top1"] = _s(pm.get("top1_score", float("nan")))
                row[p + ".n"]    = str(pm.get("n_candidates", 0))
            row["verdict"] = sr["verdict"]
            rows.append(row)
    st.table(rows)


# v1.5 distractor-arbitration / ranking brittleness panel
st.subheader("Distractor-arbitration / ranking brittleness dossier (v1.5)")
st.caption("Distractor-rich composites with 4 label-blind rankers "
           "(area, mean_intensity, edge_density, compactness). Verdicts: "
           "SURVIVES_UNDER_DISTRACTORS / RANKER_BRITTLE / "
           "DISTRACTOR_DOMINATED / FAILS_EVEN_ORACLE.")
if st.button("Build / refresh distractor-arbitration dossier"):
    with st.spinner("Running distractor composites and ranker comparison..."):
        st.session_state["_distractor_arb"] = build_distractor_arbitration_dossier()
dab = st.session_state.get("_distractor_arb")
if dab is not None:
    rows = []
    for ck, rec in dab["per_composite"].items():
        for sr in rec["sub_relations"]:
            def _s(v):
                return "n/a" if not (isinstance(v, float) and v == v) else format(v, ".3f")
            row = {"composite": ck, "overall": rec["overall_verdict"],
                   "sub": sr["sub_primitive"], "kind": sr["relation_kind"],
                   "n_cands": str(sr["n_candidates"]),
                   "oracle_best": _s(sr["oracle_best"])}
            for r in dab["rankers"]:
                row[r + ".top1"] = _s(sr["per_ranker_top1"].get(r, float("nan")))
            row["disagree"] = str(sr["ranker_disagreement"])
            row["burden"] = (_s(sr["distractor_burden"])
                              if sr["distractor_burden"] is not None else "n/a")
            row["verdict"] = sr["verdict"]
            rows.append(row)
    st.table(rows)


# v1.6 fusion / arbitration redesign panel
st.subheader("Fusion / arbitration redesign dossier (v1.6)")
st.caption("Per-feature attribution for failed single rankers + 2 fused "
           "rankers (normalized_sum, borda) + per-ranker confidence "
           "margin. Verdicts: FUSION_ROBUST / FUSION_PARTIAL / "
           "FUSION_INSUFFICIENT / PROPOSAL_QUALITY_LIMIT.")
if st.button("Build / refresh fusion dossier"):
    with st.spinner("Running attribution and fused rankers..."):
        st.session_state["_fusion"] = build_fusion_dossier()
fd = st.session_state.get("_fusion")
if fd is not None:
    rows = []
    for ck, rec in fd["per_composite"].items():
        for sr in rec["sub_relations"]:
            def _s(v):
                return "n/a" if not (isinstance(v, float) and v == v) else format(v, ".3f")
            row = {"composite": ck, "overall": rec["overall_verdict"],
                   "sub": sr["sub_primitive"], "kind": sr["relation_kind"],
                   "n_cands": str(sr["n_candidates"]),
                   "oracle_best": _s(sr["oracle_best"])}
            for r in fd["single_rankers"]:
                row[r + ".top1"] = _s(sr["single_top1"].get(r, float("nan")))
            for f in fd["fused_rankers"]:
                row[f + ".top1"] = _s(sr["fused_top1"].get(f, float("nan")))
            row["verdict"] = sr["verdict"]
            rows.append(row)
    st.table(rows)
    st.markdown("**Failed-ranker attributions (z-score diff: picker - oracle)**")
    attr_rows = []
    for ck, rec in fd["per_composite"].items():
        for sr in rec["sub_relations"]:
            for r in fd["single_rankers"]:
                a = sr["attributions"].get(r)
                if a is None:
                    continue
                d = a["per_feature_z_diff"]
                attr_rows.append({
                    "composite": ck, "sub": sr["sub_primitive"], "ranker": r,
                    "dominant": a["dominant_misleading"],
                    "area": format(d["area"], "+.2f"),
                    "mean_intensity": format(d["mean_intensity"], "+.2f"),
                    "compactness": format(d["compactness"], "+.2f"),
                })
    if attr_rows:
        st.table(attr_rows)


# v1.7 primitive-aware / target-conditioned arbitration panel
st.subheader("Primitive-aware / target-conditioned dossier (v1.7)")
st.caption("Compares best of 4 single + 2 fused generic rankers against "
           "a target-conditioned primitive-aware ranker (cardinality_target, "
           "repetition_target). Verdicts: GENERIC_FUSION_SUFFICIENT / "
           "PRIMITIVE_AWARE_HELPS / PRIMITIVE_AWARE_STILL_FAILS / "
           "PROPOSAL_QUALITY_LIMIT.")
if st.button("Build / refresh primitive-aware dossier"):
    with st.spinner("Running target-conditioned arbitration..."):
        st.session_state["_primitive_aware"] = build_primitive_aware_dossier()
pad = st.session_state.get("_primitive_aware")
if pad is not None:
    rows = []
    for ck, rec in pad["per_composite"].items():
        for sr in rec["sub_relations"]:
            def _s(v):
                return "n/a" if not (isinstance(v, float) and v == v) else format(v, ".3f")
            tp = sr["target_params"]
            tp_str = ", ".join(k + "=" + str(v) for k, v in tp.items()) or "-"
            row = {"composite": ck, "overall": rec["overall_verdict"],
                   "sub": sr["sub_primitive"], "kind": sr["relation_kind"],
                   "target": tp_str,
                   "oracle_best": _s(sr["oracle_best"]),
                   "best_generic": _s(sr["best_generic"]),
                   "via": str(sr["best_generic_name"]),
                   "primitive_aware": _s(sr["primitive_aware"]),
                   "verdict": sr["verdict"]}
            rows.append(row)
    st.table(rows)


# v1.8 primitive-aware coverage / repetition-fix panel
st.subheader("Primitive-aware coverage dossier (v1.8)")
st.caption("Cardinality + repetition coverage with a fixed strip-based "
           "repetition metric. Compares best of 4 single + 2 fused generic "
           "rankers against target-conditioned primitive-aware rankers "
           "across cardinality and repetition composites. Verdicts: "
           "GENERIC_FUSION_SUFFICIENT / ARBITRATION_INVARIANT / "
           "PRIMITIVE_AWARE_HELPS / PRIMITIVE_AWARE_STILL_FAILS / "
           "PROPOSAL_QUALITY_LIMIT.")
if st.button("Build / refresh coverage dossier"):
    with st.spinner("Running coverage across cardinality + repetition..."):
        st.session_state["_coverage"] = build_coverage_dossier()
cov = st.session_state.get("_coverage")
if cov is not None:
    rows = []
    for ck, rec in cov["per_composite"].items():
        for sr in rec["sub_relations"]:
            def _s(v):
                return "n/a" if not (isinstance(v, float) and v == v) else format(v, ".3f")
            tp = sr["target_params"]
            tp_str = ", ".join(k + "=" + str(v) for k, v in tp.items()) or "-"
            row = {"composite": ck, "overall": rec["overall_verdict"],
                   "sub": sr["sub_primitive"], "kind": sr["relation_kind"],
                   "target": tp_str,
                   "oracle_best": _s(sr["oracle_best"]),
                   "best_generic": _s(sr["best_generic"]),
                   "via": str(sr["best_generic_name"]),
                   "primitive_aware": _s(sr["primitive_aware"]),
                   "label_scoped": str(sr["label_scoped"]),
                   "verdict": sr["verdict"]}
            rows.append(row)
    st.table(rows)


# v1.9 arbitration-boundary mapping panel
st.subheader("Arbitration-boundary dossier (v1.9)")
st.caption("Cross-family boundary map + per-composite verdicts. Per primitive "
           "family we tag whether arbitration matters: PRIMITIVE_AWARE_HELPS / "
           "GENERIC_FUSION_SUFFICIENT / METRIC_GAP_ROI_INSENSITIVE / "
           "PROPOSAL_QUALITY_LIMIT / PRIMITIVE_AWARE_STILL_FAILS.")
if st.button("Build / refresh boundary dossier"):
    with st.spinner("Mapping arbitration boundaries across families..."):
        st.session_state["_boundary"] = build_boundary_dossier()
bnd = st.session_state.get("_boundary")
if bnd is not None:
    st.markdown("**Family boundary map**")
    fam_rows = []
    for fam, rec in bnd["family_boundary_map"].items():
        fam_rows.append({"family": fam,
                          "boundary_tag": rec["boundary_tag"],
                          "per_composite_verdicts":
                              ", ".join(rec["per_composite_verdicts"])})
    st.table(fam_rows)
    st.markdown("**Per-composite results**")
    rows = []
    for ck, rec in bnd["per_composite"].items():
        for sr in rec["sub_relations"]:
            def _s(v):
                return "n/a" if not (isinstance(v, float) and v == v) else format(v, ".3f")
            tp = sr["target_params"]
            tp_str = ", ".join(k + "=" + str(v) for k, v in tp.items()) or "-"
            rows.append({"composite": ck, "overall": rec["overall_verdict"],
                          "sub": sr["sub_primitive"], "kind": sr["relation_kind"],
                          "target": tp_str,
                          "oracle_best": _s(sr["oracle_best"]),
                          "best_generic": _s(sr["best_generic"]),
                          "via": str(sr["best_generic_name"]),
                          "primitive_aware": _s(sr["primitive_aware"]),
                          "verdict": sr["verdict"]})
    st.table(rows)


# v2.0 blocked-family unlock panel
st.subheader("Blocked-family unlock dossier (v2.0)")
st.caption("Cross-family boundary map after the v2.0 unlock pass. ordering "
           "and symmetry now have ROI-sensitive metrics + target-conditioned "
           "rankers; adjacency, orientation, hierarchy remain "
           "METRIC_GAP_ROI_INSENSITIVE pending further work.")
if st.button("Build / refresh unlock dossier"):
    with st.spinner("Re-running across cardinality/repetition/role_zone/ordering/symmetry..."):
        st.session_state["_unlock_v20"] = build_unlock_dossier()
unl = st.session_state.get("_unlock_v20")
if unl is not None:
    st.markdown("**Family boundary map (v2.0)**")
    fam_rows = []
    for fam, rec in unl["family_boundary_map"].items():
        fam_rows.append({"family": fam,
                          "boundary_tag": rec["boundary_tag"],
                          "per_composite_verdicts":
                              ", ".join(rec["per_composite_verdicts"])})
    st.table(fam_rows)
    st.markdown("**Per-composite results**")
    rows = []
    for ck, rec in unl["per_composite"].items():
        for sr in rec["sub_relations"]:
            def _s(v):
                return "n/a" if not (isinstance(v, float) and v == v) else format(v, ".3f")
            tp = sr["target_params"]
            tp_str = ", ".join(k + "=" + str(v) for k, v in tp.items()) or "-"
            rows.append({"composite": ck, "overall": rec["overall_verdict"],
                          "sub": sr["sub_primitive"], "kind": sr["relation_kind"],
                          "target": tp_str,
                          "oracle_best": _s(sr["oracle_best"]),
                          "best_generic": _s(sr["best_generic"]),
                          "via": str(sr["best_generic_name"]),
                          "primitive_aware": _s(sr["primitive_aware"]),
                          "verdict": sr["verdict"]})
    st.table(rows)


# v0.6 Engine-semantics proof index panel
st.subheader("Engine-semantics proof index (v0.6)")
st.caption("Top-level Engine-semantics index. Per-family table combines "
           "boundary tag, validation verdict, calibrated confidence state "
           "(TRUST/HOLD/DOWNGRADE/REJECT/NEED_MORE_EVIDENCE), and "
           "semantic-stability verdict.")
if st.button("Build / refresh proof index"):
    with st.spinner("Aggregating proof-category evidence..."):
        st.session_state["_proof_index"] = build_proof_index()
pix = st.session_state.get("_proof_index")
if pix is not None:
    st.markdown("**Proof-category status**")
    cat_rows = []
    for cat, info in pix["categories"].items():
        cat_rows.append({
            "category": cat,
            "status": pix["category_status"].get(cat, "?"),
            "question": info["question"],
        })
    st.table(cat_rows)
    st.markdown("**Per-family Engine-semantics table**")
    fam_rows = []
    for fam, rec in pix["family_table"].items():
        fam_rows.append({
            "family": fam,
            "boundary_tag":       str(rec.get("boundary_tag") or "-"),
            "validation_verdict": str(rec.get("validation_verdict") or "-"),
            "confidence_state":   str(rec.get("confidence_state") or "-"),
            "semantic_stability": str(rec.get("semantic_stability") or "-"),
        })
    st.table(fam_rows)
