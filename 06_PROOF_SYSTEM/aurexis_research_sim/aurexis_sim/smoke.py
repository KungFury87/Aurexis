"""Headless smoke runner.

    python -m aurexis_sim.smoke
"""
from __future__ import annotations

from pprint import pprint

from . import truth as truth_mod
from . import metrics as metrics_mod
from .simulate import SimParams, run_chain
from .sensor import SensorParams
from .relations import relation_report
from .stress import (
    stress_sweep, collapse_threshold,
    relation_confusion_table,
    DEFAULT_PROBE_KINDS_HARD, DEFAULT_PROBE_KINDS_EASY,
)


def main():
    print("Aurexis Research Sim v0.6 - smoke run (Engine-semantics proof system)")

    scenarios = [
        ("clean (grayscale)",
         SimParams(),
         "blocks", {"size": 128, "n": 8, "seed": 0}),
        ("mild (grayscale)",
         SimParams(blur_sigma=1.0, gauss_noise=0.01, gamma=1.2),
         "phoxel_probe", {"size": 128, "cell": 8, "seed": 0}),
        ("hostile (grayscale)",
         SimParams(scale=0.5, rotate_deg=7.0, perspective=0.1,
                   blur_sigma=2.5, motion_blur_len=9, motion_blur_angle=15.0,
                   rolling_shutter_shift=8, exposure=1.2, gamma=1.6,
                   contrast=1.4, gauss_noise=0.03, shot_noise=0.05, bit_depth=6),
         "relation_probe", {"size": 128, "seed": 0}),
        ("sensor bayer clean",
         SimParams(sensor=SensorParams(enabled=True, pattern="RGGB")),
         "rgb_blocks", {"size": 128, "n": 8, "seed": 0}),
        ("sensor bayer + per-channel noise/blur",
         SimParams(
             blur_sigma=0.5,
             sensor=SensorParams(
                 enabled=True, pattern="RGGB",
                 blur_sigma_r=0.8, blur_sigma_g=0.4, blur_sigma_b=0.8,
                 noise_r=0.02, noise_g=0.01, noise_b=0.02,
             ),
         ),
         "color_relation_probe", {"size": 128, "seed": 0}),
    ]
    for name, params, kind, tk_kwargs in scenarios:
        print("\n--- scenario: " + name + " / pattern: " + kind + " ---")
        truth_pkt = truth_mod.generate(kind, **tk_kwargs)
        result = run_chain(truth_pkt["image"], params, seed=42)
        pprint(metrics_mod.compute_all(truth_pkt, result["captured"]))

    # v0.3 per-stage relation report (retained)
    print("\n=== v0.3 per-stage relation report ===")
    rel_scenarios = [
        ("ordering_probe",    {"size": 128, "n": 6}),
        ("adjacency_probe",   {"size": 128, "n_pairs": 4}),
        ("symmetry_probe",    {"size": 128, "axis": "vertical"}),
        ("orientation_probe", {"size": 128, "n": 4}),
        ("hierarchy_probe",   {"size": 128}),
    ]
    p = SimParams(
        blur_sigma=0.8,
        sensor=SensorParams(enabled=True, pattern="RGGB",
                             noise_r=0.015, noise_g=0.01, noise_b=0.015),
    )
    for kind, kw in rel_scenarios:
        pkt = truth_mod.generate(kind, **kw)
        rep = relation_report(pkt, p, seed=7)
        print("\n-- " + kind + " --")
        for stage, v in rep.items():
            vs = "n/a" if isinstance(v, float) and v != v else format(v, ".3f")
            print("   {:<22} {}".format(stage, vs))

    # v0.4 stress sweep on each hard probe (short)
    print("\n=== v0.4 stress sweep (hard probes vs blur_sigma) ===")
    blur_values = [0.0, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0]
    for kind in DEFAULT_PROBE_KINDS_HARD:
        kwargs = {"size": 128}
        curve = stress_sweep(kind, kwargs,
                             lambda v: SimParams(blur_sigma=float(v)),
                             blur_values, seed=0)
        ct = collapse_threshold(curve, 0.5)
        print("\n-- " + kind + " --")
        for v, s in curve:
            vs = "n/a" if isinstance(s, float) and s != s else format(s, ".3f")
            print("   blur={:<4.2f}  surv={}".format(v, vs))
        print("   collapse@0.5: " + (("blur=" + format(ct[0], ".3g") +
                                      " surv=" + format(ct[1], ".3f"))
                                     if ct else "not reached"))

    # v0.4 confusion table (hard vs easy)
    print("\n=== v0.4 relation confusion: hard vs easy probes under mild sensor ===")
    mild = SimParams(blur_sigma=1.2, gauss_noise=0.015,
                     sensor=SensorParams(enabled=True, pattern="RGGB",
                                         noise_r=0.015, noise_g=0.010,
                                         noise_b=0.015))
    hard = relation_confusion_table(mild, DEFAULT_PROBE_KINDS_HARD)
    easy = relation_confusion_table(mild, DEFAULT_PROBE_KINDS_EASY)
    print("   {:<28}  hard  | easy".format("relation"))
    kinds = ["ordering", "adjacency", "symmetry", "orientation", "hierarchy"]
    for k in kinds:
        h = hard.get(k + "_probe_hard", float("nan"))
        e = easy.get(k + "_probe", float("nan"))
        hs = "n/a" if h != h else format(h, ".3f")
        es = "n/a" if e != e else format(e, ".3f")
        print("   {:<28}  {}  | {}".format(k, hs, es))

    # v0.7 scenario stability summary (short)
    print("\n=== v0.7 scenario stability summary ===")
    try:
        from .atlas import build_scenario_atlas
        atlas = build_scenario_atlas(size=96)
        print("   {:<24} {:<22} R/C/F  range  mean".format("probe", "verdict"))
        for kind in atlas["probe_kinds"]:
            s = atlas["stability_summary"][kind]
            rng = s.get("range"); mean = s.get("mean")
            rs = "n/a" if rng is None else format(rng, ".3f")
            ms = "n/a" if mean is None else format(mean, ".3f")
            print("   {:<24} {:<22} {}/{}/{}  {}  {}".format(
                kind, s["stable_verdict"],
                s["robust_count"], s["conditional_count"], s["fragile_count"],
                rs, ms))
    except Exception as _e:
        print("   scenario atlas failed:", _e)

    # v0.8 promoted-primitive validation (short)
    print("\n=== v0.8 promoted-primitive validation ===")
    try:
        from .validation import validate_promoted_primitives
        report = validate_promoted_primitives()
        for name, rec in report["per_primitive"].items():
            print("   {:<12} verdict: {}".format(name, rec["verdict"]))
    except Exception as _e:
        print("   validation failed:", _e)

    # v0.9 primitive redesign attribution (short)
    print("\n=== v0.9 primitive redesign attribution ===")
    try:
        from .redesign import build_redesign_dossier
        dossier = build_redesign_dossier()
        for name, rec in dossier["per_primitive"].items():
            b = rec["baseline_survival_under_attribution_capture"]
            bs = "n/a" if not (isinstance(b, float) and b == b) else format(b, ".3f")
            print("   {:<12} baseline={}  dominant={}  ->".format(
                name, bs, rec["dominant_weakness"]))
            print("       " + rec["suggested_redesign"])
    except Exception as _e:
        print("   redesign attribution failed:", _e)

    # v1.0 composite interaction (short)
    print("\n=== v1.0 composite interaction ===")
    try:
        from .interaction import build_interaction_dossier
        dossier = build_interaction_dossier()
        for ck, rec in dossier["per_composite"].items():
            print("   {:<46} overall: {}".format(ck, rec["overall_flag"]))
            for sr in rec["sub_relations"]:
                ic = sr["survival_in_composite"]; al = sr["survival_alone"]
                ics = "n/a" if not (isinstance(ic, float) and ic == ic) else format(ic, ".3f")
                als = "n/a" if not (isinstance(al, float) and al == al) else format(al, ".3f")
                print("       {:<12} composite={}  alone={}  {}".format(
                    sr["sub_primitive"], ics, als, sr["flag"]))
    except Exception as _e:
        print("   interaction failed:", _e)

    # v1.1 scene-scoped binding (short)
    print("\n=== v1.1 scene-scoped binding ===")
    try:
        from .binding import build_binding_dossier
        dossier = build_binding_dossier()
        for ck, rec in dossier["per_composite"].items():
            print("   {:<46} overall: {}".format(ck, rec["overall_verdict"]))
            for sr in rec["sub_relations"]:
                u = sr["unbound_survival"]; b = sr["bound_survival"]
                us = "n/a" if not (isinstance(u, float) and u == u) else format(u, ".3f")
                bs = "n/a" if not (isinstance(b, float) and b == b) else format(b, ".3f")
                tag = (" " + ",".join(sr["tags"])) if sr["tags"] else ""
                print("       {:<12} unbound={}  bound={}  {}{}".format(
                    sr["sub_primitive"], us, bs, sr["verdict"], tag))
    except Exception as _e:
        print("   binding failed:", _e)

    # v1.2 soft-binding (short)
    print("\n=== v1.2 soft-binding ===")
    try:
        from .soft_binding import build_soft_binding_dossier
        dossier = build_soft_binding_dossier()
        for ck, rec in dossier["per_composite"].items():
            print("   {:<46} overall: {}".format(ck, rec["overall_verdict"]))
            for sr in rec["sub_relations"]:
                p = sr["mode_survival"].get("perfect")
                ws = sr["worst_soft_score"]; wm = sr["worst_soft_mode"]
                ps = "n/a" if not (isinstance(p, float) and p == p) else format(p, ".3f")
                wss = "n/a" if not (isinstance(ws, float) and ws == ws) else format(ws, ".3f")
                print("       {:<12} perfect={}  worst_soft={}@{}  {}".format(
                    sr["sub_primitive"], ps, wss, str(wm), sr["verdict"]))
    except Exception as _e:
        print("   soft_binding failed:", _e)

    # v1.3 inferred-binding (short)
    print("\n=== v1.3 inferred-binding ===")
    try:
        from .inferred_binding import build_inferred_binding_dossier
        dossier = build_inferred_binding_dossier()
        for ck, rec in dossier["per_composite"].items():
            print("   {:<46} overall: {}".format(ck, rec["overall_verdict"]))
            for sr in rec["sub_relations"]:
                bi = sr["best_inferred"]; bp = sr["best_proposal"]
                bis = "n/a" if not (isinstance(bi, float) and bi == bi) else format(bi, ".3f")
                print("       {:<12} best_inferred={}@{}  {}".format(
                    sr["sub_primitive"], bis, str(bp), sr["verdict"]))
    except Exception as _e:
        print("   inferred_binding failed:", _e)

    # v1.4 arbitration / proposal competition (short)
    print("\n=== v1.4 arbitration / proposal competition ===")
    try:
        from .arbitration import build_arbitration_dossier
        dossier = build_arbitration_dossier()
        for ck, rec in dossier["per_composite"].items():
            print("   {:<46} overall: {}".format(ck, rec["overall_verdict"]))
            for sr in rec["sub_relations"]:
                ob = sr["oracle_best"]; t1 = sr["top1"]; w = sr["worst"]
                obs = "n/a" if not (isinstance(ob, float) and ob == ob) else format(ob, ".3f")
                t1s = "n/a" if not (isinstance(t1, float) and t1 == t1) else format(t1, ".3f")
                ws  = "n/a" if not (isinstance(w,  float) and w  == w ) else format(w,  ".3f")
                print("       {:<12} n_cands={}  oracle={}  top1={}  worst={}  {}".format(
                    sr["sub_primitive"], sr["n_candidates_total"],
                    obs, t1s, ws, sr["verdict"]))
    except Exception as _e:
        print("   arbitration failed:", _e)


    # v1.5 distractor-arbitration / ranking brittleness (short)
    print("\n=== v1.5 distractor-arbitration / ranking brittleness ===")
    try:
        from .distractor_arbitration import build_distractor_arbitration_dossier
        dossier = build_distractor_arbitration_dossier()
        for ck, rec in dossier["per_composite"].items():
            print("   {:<46} overall: {}".format(ck, rec["overall_verdict"]))
            for sr in rec["sub_relations"]:
                ob = sr["oracle_best"]
                obs = "n/a" if not (isinstance(ob, float) and ob == ob) else format(ob, ".3f")
                passes = sum(1 for v in sr["per_ranker_top1"].values()
                             if isinstance(v, float) and v == v and v >= 0.80)
                total = len(sr["per_ranker_top1"])
                print("       {:<12} oracle={}  {}/{} rankers pass  {}".format(
                    sr["sub_primitive"], obs, passes, total, sr["verdict"]))
    except Exception as _e:
        print("   distractor_arbitration failed:", _e)


    # v1.6 fusion / arbitration redesign (short)
    print("\n=== v1.6 fusion / arbitration redesign ===")
    try:
        from .fusion import build_fusion_dossier
        dossier = build_fusion_dossier()
        for ck, rec in dossier["per_composite"].items():
            print("   {:<46} overall: {}".format(ck, rec["overall_verdict"]))
            for sr in rec["sub_relations"]:
                ob = sr["oracle_best"]
                obs = "n/a" if not (isinstance(ob, float) and ob == ob) else format(ob, ".3f")
                fused_pass = sum(1 for v in sr["fused_top1"].values()
                                 if isinstance(v, float) and v == v and v >= 0.80)
                fused_total = len(sr["fused_top1"])
                # Pick the most-cited dominant_misleading feature among failed singles.
                doms = [a["dominant_misleading"]
                        for a in sr["attributions"].values() if a is not None]
                dom = max(set(doms), key=doms.count) if doms else "-"
                print("       {:<12} oracle={}  {}/{} fused pass  dominant={}  {}".format(
                    sr["sub_primitive"], obs, fused_pass, fused_total, dom, sr["verdict"]))
    except Exception as _e:
        print("   fusion failed:", _e)


    # v1.7 primitive-aware / target-conditioned arbitration (short)
    print("\n=== v1.7 primitive-aware / target-conditioned arbitration ===")
    try:
        from .primitive_aware import build_primitive_aware_dossier
        dossier = build_primitive_aware_dossier()
        for ck, rec in dossier["per_composite"].items():
            print("   {:<46} overall: {}".format(ck, rec["overall_verdict"]))
            for sr in rec["sub_relations"]:
                ob = sr["oracle_best"]; bg = sr["best_generic"]; pa = sr["primitive_aware"]
                fmt = lambda v: "n/a" if not (isinstance(v, float) and v == v) else format(v, ".3f")
                print("       {:<12} oracle={}  best_generic={} ({})  primitive_aware={}  {}".format(
                    sr["sub_primitive"], fmt(ob), fmt(bg),
                    str(sr["best_generic_name"]), fmt(pa), sr["verdict"]))
    except Exception as _e:
        print("   primitive_aware failed:", _e)


    # v1.8 primitive-aware coverage / repetition-fix (short)
    print("\n=== v1.8 primitive-aware coverage / repetition-fix ===")
    try:
        from .coverage import build_coverage_dossier
        dossier = build_coverage_dossier()
        for ck, rec in dossier["per_composite"].items():
            print("   {:<46} overall: {}".format(ck, rec["overall_verdict"]))
            for sr in rec["sub_relations"]:
                fmt = lambda v: "n/a" if not (isinstance(v, float) and v == v) else format(v, ".3f")
                print("       {:<12} ({:<11}) oracle={}  best_generic={} ({})  primitive_aware={}  {}".format(
                    sr["sub_primitive"], sr["relation_kind"],
                    fmt(sr["oracle_best"]), fmt(sr["best_generic"]),
                    str(sr["best_generic_name"]),
                    fmt(sr["primitive_aware"]), sr["verdict"]))
    except Exception as _e:
        print("   coverage failed:", _e)


    # v1.9 arbitration-boundary mapping (short)
    print("\n=== v1.9 arbitration-boundary mapping ===")
    try:
        from .boundary import build_boundary_dossier
        dossier = build_boundary_dossier()
        print("   family boundary map:")
        for fam, rec in dossier["family_boundary_map"].items():
            print("     {:<14} {}".format(fam, rec["boundary_tag"]))
        print("")
        for ck, rec in dossier["per_composite"].items():
            print("   {:<46} overall: {}".format(ck, rec["overall_verdict"]))
            for sr in rec["sub_relations"]:
                fmt = lambda v: "n/a" if not (isinstance(v, float) and v == v) else format(v, ".3f")
                print("       {:<12} ({:<11}) oracle={}  best_generic={} ({})  primitive_aware={}  {}".format(
                    sr["sub_primitive"], sr["relation_kind"],
                    fmt(sr["oracle_best"]), fmt(sr["best_generic"]),
                    str(sr["best_generic_name"]),
                    fmt(sr["primitive_aware"]), sr["verdict"]))
    except Exception as _e:
        print("   boundary failed:", _e)


    # v2.0 blocked-family unlock (short)
    print("\n=== v2.0 blocked-family unlock ===")
    try:
        from .unlock import build_unlock_dossier
        dossier = build_unlock_dossier()
        print("   family boundary map (v2.0):")
        for fam, rec in dossier["family_boundary_map"].items():
            print("     {:<14} {}".format(fam, rec["boundary_tag"]))
        print("")
        for ck, rec in dossier["per_composite"].items():
            print("   {:<46} overall: {}".format(ck, rec["overall_verdict"]))
            for sr in rec["sub_relations"]:
                fmt = lambda v: "n/a" if not (isinstance(v, float) and v == v) else format(v, ".3f")
                print("       {:<12} ({:<11}) oracle={}  best_generic={} ({})  primitive_aware={}  {}".format(
                    sr["sub_primitive"], sr["relation_kind"],
                    fmt(sr["oracle_best"]), fmt(sr["best_generic"]),
                    str(sr["best_generic_name"]),
                    fmt(sr["primitive_aware"]), sr["verdict"]))
    except Exception as _e:
        print("   unlock failed:", _e)


    # v0.6 Engine-semantics proof index (top-level summary)
    print("\n=== v0.6 Engine-semantics proof index ===")
    try:
        from .proof_index import build_proof_index
        idx = build_proof_index()
        print("   Proof-category status:")
        for cat, info in idx["categories"].items():
            st = idx["category_status"].get(cat, "?")
            print("     {:<26} {}".format(cat, st))
        print("")
        print("   Per-family Engine-semantics table:")
        for fam, rec in idx["family_table"].items():
            print("     {:<14} boundary={:<28} validation={:<14} confidence={:<22} semantic={}".format(
                fam,
                str(rec.get("boundary_tag") or "-"),
                str(rec.get("validation_verdict") or "-"),
                str(rec.get("confidence_state") or "-"),
                str(rec.get("semantic_stability") or "-")))
    except Exception as _e:
        print("   proof_index failed:", _e)

    return 0


def _smoke_entry_v06():
    return main()


if __name__ == "__main__":
    raise SystemExit(_smoke_entry_v06())
# end of file padding
