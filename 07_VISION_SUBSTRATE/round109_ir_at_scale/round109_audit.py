"""Round 109 — IR audit on the cached real-world corpus (N=76).

Closes progress on P-01 (stale since R47 — 'Run IR audit on 10,000+
image corpus'). N=76 isn't 10,000, but it's a 3.8x growth from
R107's N=20 synthetic corpus and the largest real-world IR run since
R85 (N=110 cached but not all re-audited at current 151-pred vocab).

Goals:
  1. Confirm all 151 R107-canonical predicates still parse / install
  2. Run substrate on N=76 cached real-world images
  3. Compute fire-rate distribution per predicate
  4. Find equivalence classes (predicates with identical fire patterns)
  5. Find near-collision pairs (Jaccard >= 0.95)
  6. Compute substrate effective rank (energy-90% PCA components)
  7. Compare to R77's 31/76 and R85's 39/110 figures
"""
from __future__ import annotations
import json, sys, time
from itertools import combinations
from pathlib import Path
import numpy as np

ROOT = Path("/sessions/wonderful-sharp-rubin/mnt/Aurexis evolved/"
            "Aurexis_Core_WORKING_20260414-1339/07_VISION_SUBSTRATE")
sys.path.insert(0, str(ROOT))
from aurexis_workbench.runtime import Runtime
from aurexis_workbench import dsl, predicates as P, vision_ops
from aurexis_workbench.visual_intake import _bundle_from_single

R55_DIR = Path("/sessions/wonderful-sharp-rubin/mnt/Aurexis evolved/"
                "round55_corpus_harness/corpus_images")
R85_DIR = Path("/sessions/wonderful-sharp-rubin/mnt/Aurexis evolved/"
                "round85_corpus_growth/images_diverse")


def main():
    out_dir = Path("/tmp/round109_ir_at_scale"); out_dir.mkdir(exist_ok=True)
    vision_ops.register_all()
    text = (ROOT/"data"/"vision"/"vocab.aurex").read_text()
    runtime = Runtime()
    for pp in dsl.parse_source(text):
        if pp.ok:
            try:
                P.type_check(pp.pred); runtime.install(pp.pred)
            except Exception: pass
    pred_names = runtime.installed()
    print(f"installed {len(pred_names)} predicates")

    # Collect corpus
    corpus = []
    for d in [R55_DIR, R85_DIR]:
        for f in sorted(d.glob("*.npy")):
            corpus.append((f.stem, str(f)))
    print(f"corpus size: {len(corpus)} images")

    # Source breakdown
    by_source = {}
    for name, _ in corpus:
        prefix = name.split("_")[0]
        by_source[prefix] = by_source.get(prefix, 0) + 1
    print(f"sources: {by_source}")

    # Run substrate
    fingerprints = {}  # name -> dict[pred -> bool]
    failed_loads = []
    tic = time.time()
    for i, (name, path) in enumerate(corpus):
        try:
            rgb = np.load(path)
            if rgb.ndim != 3 or rgb.shape[-1] != 3:
                failed_loads.append((name, f"shape {rgb.shape}"))
                continue
            # Downsample for speed
            from PIL import Image
            img = Image.fromarray(rgb)
            img.thumbnail((320, 320), Image.LANCZOS)
            rgb = np.asarray(img)
            luma = (0.299*rgb[...,0] + 0.587*rgb[...,1] + 0.114*rgb[...,2]).astype(np.float64)/255.0
            color = rgb.astype(np.float64)/255.0
            bundle, _ = _bundle_from_single(luma, name, patch_size=64, color=color)
            # Multi-modal preds need depth/hyperspectral - they'll abstain
            fp = {}
            for pn in pred_names:
                rec = runtime.evaluate(pn, bundle)
                fp[pn] = bool(rec.value) if (rec.error is None and rec.value is not None) else False
            fingerprints[name] = fp
        except Exception as e:
            failed_loads.append((name, str(e)[:80]))
    elapsed = time.time() - tic
    print(f"\nevaluated {len(fingerprints)} bundles in {elapsed:.1f}s ({elapsed/max(len(fingerprints),1):.2f}s each)")
    if failed_loads:
        print(f"failed: {len(failed_loads)}")
        for f in failed_loads[:3]: print(f"  {f}")

    # Fire-rate distribution
    N = len(fingerprints)
    pred_fire = {pn: sum(fp[pn] for fp in fingerprints.values()) for pn in pred_names}
    fire_buckets = {"DEAD (0)": 0, "LOW (1-5%)": 0, "HEALTHY (5-95%)": 0,
                     "HIGH (95-100%)": 0, "ALWAYS (100%)": 0}
    dead_preds, always_preds, healthy_count = [], [], 0
    for pn, n in pred_fire.items():
        rate = n / N
        if rate == 0: fire_buckets["DEAD (0)"] += 1; dead_preds.append(pn)
        elif rate <= 0.05: fire_buckets["LOW (1-5%)"] += 1
        elif rate < 0.95: fire_buckets["HEALTHY (5-95%)"] += 1; healthy_count += 1
        elif rate < 1.0: fire_buckets["HIGH (95-100%)"] += 1
        else: fire_buckets["ALWAYS (100%)"] += 1; always_preds.append(pn)

    # Equivalence classes (identical fire pattern across all images)
    eq_classes = {}
    for pn in pred_names:
        pattern = tuple(fingerprints[name][pn] for name in fingerprints)
        eq_classes.setdefault(pattern, []).append(pn)
    multi_member_classes = {k: v for k, v in eq_classes.items() if len(v) > 1}

    # Near-collision pairs (Jaccard >= 0.95)
    near_collisions = []
    fire_sets = {pn: {nm for nm in fingerprints if fingerprints[nm][pn]}
                  for pn in pred_names}
    pn_list = list(pred_names)
    for i, pa in enumerate(pn_list):
        sa = fire_sets[pa]
        for pb in pn_list[i+1:]:
            sb = fire_sets[pb]
            if not sa and not sb: continue
            J = len(sa & sb) / len(sa | sb) if sa or sb else 0
            if J >= 0.95:
                near_collisions.append((pa, pb, round(J, 3)))

    # Effective rank: PCA on 151-bit fingerprint matrix
    M = np.array([[int(fp[pn]) for pn in pred_names] for fp in fingerprints.values()], dtype=np.float64)
    if M.shape[0] >= 2:
        Mc = M - M.mean(axis=0)
        try:
            _, s, _ = np.linalg.svd(Mc, full_matrices=False)
            energy = (s**2).cumsum() / (s**2).sum()
            rank_90 = int(np.searchsorted(energy, 0.90) + 1)
            rank_99 = int(np.searchsorted(energy, 0.99) + 1)
        except Exception:
            rank_90 = rank_99 = -1
    else:
        rank_90 = rank_99 = -1

    # R107-promoted predicates - check fire rate (will be all 0 since no
    # depth/hyperspectral fields)
    r107_promoted = ["has_far_field_dominance", "has_narrow_spectral_peak",
                      "is_distant_vegetation", "is_close_chromatic_object",
                      "is_uniform_lit_far_field"]
    r107_fire = {pn: pred_fire.get(pn, 0) for pn in r107_promoted}

    result = {
        "round": "R109", "date": "2026-05-01",
        "method": "IR audit on N=76 cached real-world corpus (R55 + R85)",
        "n_corpus": N, "n_failed_loads": len(failed_loads),
        "by_source": by_source,
        "n_predicates_total": len(pred_names),
        "fire_rate_distribution": fire_buckets,
        "n_dead_predicates": len(dead_preds),
        "dead_predicates": dead_preds[:30],
        "n_always_firing": len(always_preds),
        "always_firing_predicates": always_preds,
        "n_healthy_predicates": healthy_count,
        "n_equivalence_classes": len(eq_classes),
        "n_multi_member_eq_classes": len(multi_member_classes),
        "multi_member_eq_classes_largest": sorted(
            [(len(v), v[:8]) for v in multi_member_classes.values()],
            reverse=True
        )[:5],
        "n_near_collisions_J_geq_0_95": len(near_collisions),
        "near_collisions_top_5": near_collisions[:5],
        "effective_rank_90pct_energy": rank_90,
        "effective_rank_99pct_energy": rank_99,
        "r107_predicates_fire_count_in_RGB_only_corpus":
            "all 0 expected — these need depth/hyperspectral fields",
        "r107_fire": r107_fire,
        "comparison": {
            "R77_effective_rank_90pct": "31 / 76",
            "R85_effective_rank_90pct": "39 / 110",
            "R109_effective_rank_90pct": f"{rank_90} / {N}",
        },
    }
    (out_dir/"round109_audit.json").write_text(json.dumps(result, indent=2))
    print("\n=== R109 RESULTS ===")
    print(json.dumps({k: v for k, v in result.items()
                       if k not in ("dead_predicates", "multi_member_eq_classes_largest", "near_collisions_top_5")}, indent=2))
    print("\nDEAD predicates (need corpus pump):")
    for pn in dead_preds[:15]:
        print(f"  {pn}")
    if len(dead_preds) > 15: print(f"  ... and {len(dead_preds)-15} more")
    print("\nMulti-member equivalence classes (top 5):")
    for size, members in sorted([(len(v), v) for v in multi_member_classes.values()], reverse=True)[:5]:
        print(f"  size={size}: {members[:5]}{'...' if len(members)>5 else ''}")
    print("\nNear-collisions (top 5):")
    for pa, pb, J in near_collisions[:5]:
        print(f"  J={J}: {pa}  ↔  {pb}")


if __name__ == "__main__":
    main()
