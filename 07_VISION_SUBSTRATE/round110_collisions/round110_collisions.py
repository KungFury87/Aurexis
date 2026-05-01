"""Round 110 — investigate 5 R109 near-collision pairs.

For each pair (J >= 0.95 at N=76), determine:
  1. Disagreement scenes — which images do they DISAGREE on?
  2. Per-source breakdown — does the collision hold across all source
     types, or is it driven by one corpus subset?
  3. Threshold sensitivity — would different thresholds break the
     collision while keeping each predicate's intent intact?
  4. Verdict — "redesign" if there's a clear way to make them
     orthogonal; "document" if the correlation is physically
     unavoidable.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path("/sessions/wonderful-sharp-rubin/mnt/Aurexis evolved/"
            "Aurexis_Core_WORKING_20260414-1339/07_VISION_SUBSTRATE")
sys.path.insert(0, str(ROOT))
from aurexis_workbench.runtime import Runtime
from aurexis_workbench import dsl, predicates as P, vision_ops, operators as ops

R55_DIR = Path("/sessions/wonderful-sharp-rubin/mnt/Aurexis evolved/"
                "round55_corpus_harness/corpus_images")
R85_DIR = Path("/sessions/wonderful-sharp-rubin/mnt/Aurexis evolved/"
                "round85_corpus_growth/images_diverse")

NEAR_COLLISIONS = [
    ("has_gradient_energy", "has_many_corners"),
    ("has_gradient_energy", "has_circular_signature"),
    ("has_gradient_energy", "has_chroma_subsampled_signature"),
    ("has_circular_signature", "has_many_corners"),
    ("has_many_corners", "has_chroma_subsampled_signature"),
]

# We also need raw scalar values from the underlying ops so we can
# investigate threshold sensitivity. Look up which ops these predicates
# call.

def main():
    out_dir = Path("/tmp/round110_collisions"); out_dir.mkdir(exist_ok=True)
    vision_ops.register_all()
    text = (ROOT/"data"/"vision"/"vocab.aurex").read_text()
    runtime = Runtime()
    pred_objs = {}
    for pp in dsl.parse_source(text):
        if pp.ok:
            try:
                P.type_check(pp.pred); runtime.install(pp.pred)
                pred_objs[pp.pred.name] = pp.pred
            except Exception: pass

    # Load corpus
    corpus = []
    for d in [R55_DIR, R85_DIR]:
        for f in sorted(d.glob("*.npy")):
            corpus.append((f.stem, str(f)))

    # Run substrate
    from aurexis_workbench.visual_intake import _bundle_from_single
    from PIL import Image
    fp = {}
    for name, path in corpus:
        try:
            rgb = np.load(path)
            if rgb.ndim != 3 or rgb.shape[-1] != 3: continue
            img = Image.fromarray(rgb); img.thumbnail((320, 320), Image.LANCZOS)
            rgb = np.asarray(img)
            luma = (0.299*rgb[...,0] + 0.587*rgb[...,1] + 0.114*rgb[...,2]).astype(np.float64)/255.0
            color = rgb.astype(np.float64)/255.0
            bundle, _ = _bundle_from_single(luma, name, patch_size=64, color=color)
            row = {}
            for pn in runtime.installed():
                rec = runtime.evaluate(pn, bundle)
                row[pn] = bool(rec.value) if (rec.error is None and rec.value is not None) else False
            fp[name] = row
        except Exception as e:
            print(f"FAIL {name}: {e}")
    print(f"loaded {len(fp)} fingerprints")

    # Per-pair analysis
    pair_analysis = {}
    for pa, pb in NEAR_COLLISIONS:
        sa = {n for n in fp if fp[n][pa]}
        sb = {n for n in fp if fp[n][pb]}
        agree_yes = sa & sb
        agree_no = (set(fp) - sa) & (set(fp) - sb)
        disagree_a_only = sa - sb
        disagree_b_only = sb - sa
        J = len(sa & sb) / len(sa | sb) if (sa | sb) else 0.0

        # Per-source breakdown
        by_source = {}
        for n in fp:
            src = n.split("_")[0]
            by_source.setdefault(src, {"a_only": 0, "b_only": 0, "both": 0, "neither": 0, "total": 0})
            if n in disagree_a_only: by_source[src]["a_only"] += 1
            elif n in disagree_b_only: by_source[src]["b_only"] += 1
            elif n in agree_yes: by_source[src]["both"] += 1
            else: by_source[src]["neither"] += 1
            by_source[src]["total"] += 1

        pair_analysis[f"{pa} vs {pb}"] = {
            "Jaccard": round(J, 3),
            "n_a_fires": len(sa),
            "n_b_fires": len(sb),
            "agree_both_fire": len(agree_yes),
            "agree_both_quiet": len(agree_no),
            "disagree_a_only": sorted(disagree_a_only)[:5],
            "n_disagree_a_only": len(disagree_a_only),
            "disagree_b_only": sorted(disagree_b_only)[:5],
            "n_disagree_b_only": len(disagree_b_only),
            "by_source": by_source,
        }

    print("\n=== R110 NEAR-COLLISION ANALYSIS ===")
    for pair, a in pair_analysis.items():
        print(f"\n{pair}: J={a['Jaccard']}")
        print(f"  fire counts: a={a['n_a_fires']}, b={a['n_b_fires']}")
        print(f"  agree(both fire): {a['agree_both_fire']}; agree(both quiet): {a['agree_both_quiet']}")
        print(f"  disagree a-only: {a['n_disagree_a_only']}, samples: {a['disagree_a_only']}")
        print(f"  disagree b-only: {a['n_disagree_b_only']}, samples: {a['disagree_b_only']}")
        # Show per-source where collision is HIGH (both fire) vs LOW (varied)
        print(f"  by source (a_only / b_only / both / neither / total):")
        for src, c in sorted(a["by_source"].items()):
            print(f"    {src:14s}  {c['a_only']}/{c['b_only']}/{c['both']}/{c['neither']}/{c['total']}")

    # Verdicts: a pair is "redesign-able" if there exist disagreement
    # scenes — meaning the predicates DO sometimes differ, just not
    # often. A pair where every source has near-100% both-fire or
    # both-quiet is "physically correlated, document instead."
    verdicts = {}
    for pair, a in pair_analysis.items():
        n_disagree = a["n_disagree_a_only"] + a["n_disagree_b_only"]
        n_total = sum(a["by_source"][s]["total"] for s in a["by_source"])
        if n_disagree >= 2 and a["Jaccard"] < 0.99:
            verdicts[pair] = "REDESIGN POSSIBLE — disagreement scenes exist; threshold or operator change could break collision"
        elif n_disagree == 0:
            verdicts[pair] = "PHYSICAL CORRELATION — predicates agree on every scene; collision is signal, not bug"
        else:
            verdicts[pair] = "MIXED — small disagreement but mostly correlated"

    result = {
        "round": "R110", "date": "2026-05-01",
        "n_corpus": len(fp),
        "near_collisions_analysis": pair_analysis,
        "verdicts": verdicts,
    }
    (out_dir/"round110_audit.json").write_text(json.dumps(result, indent=2))
    print("\n=== VERDICTS ===")
    for p, v in verdicts.items():
        print(f"  {p}")
        print(f"    -> {v}")


if __name__ == "__main__":
    main()
