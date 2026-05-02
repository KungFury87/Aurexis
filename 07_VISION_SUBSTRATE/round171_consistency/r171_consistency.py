"""R171 - claim-verification self-consistency audit on N=623."""
import json
from pathlib import Path
import numpy as np

DIRS = [('r111', Path('/tmp/r111_fps')),
        ('r158', Path('/tmp/r158_fps')),
        ('r159', Path('/tmp/r159_fps'))]
OUT = Path('/tmp/round171_audit'); OUT.mkdir(exist_ok=True)

all_fps = {}
for prefix, d in DIRS:
    for fp_path in d.glob('*.json'):
        all_fps[f"{prefix}_{fp_path.stem}"] = json.loads(fp_path.read_text())
n = len(all_fps)
keys = sorted(all_fps.keys())
print(f"N = {n}")

# Same CLAIM_MAP as R168/R169 production
CLAIM_MAP = {
    "is outdoors":              [('NOT_ANY', ['has_indoor_scene_signature'])],
    "is indoors":               [('OR', ['has_indoor_scene_signature'])],
    "contains a person":        [('OR', ['has_face_like_signature', 'has_human_subject_signature', 'has_skin_tone_signature'])],
    "is monochrome":            [('OR', ['has_monochrome', 'has_pure_grayscale_palette'])],
    "has a horizon":            [('OR', ['has_clear_horizon'])],
    "has warm tones":           [('OR', ['has_warm_palette', 'has_strongly_warm_palette'])],
    "has cool tones":           [('OR', ['has_cool_palette', 'has_dominant_blue_hue'])],
    "is high contrast":         [('OR', ['is_high_contrast_image'])],
    "has blue tones":           [('OR', ['has_dominant_blue_hue', 'has_significant_cyan_hue'])],
    "has low-key lighting":     [('OR', ['has_low_key', 'has_low_light_signature'])],
    "is centered":              [('OR', ['has_centered_subject'])],
    "has high frequency detail":[('OR', ['has_high_frequency_residual'])],
    "is largely empty":         [('OR', ['has_significant_negative_space'])],
    "has vegetation":           [('OR', ['has_vegetation_signature', 'has_green_dominant'])],
}

def evaluate_claim(fp, claim):
    constraints = CLAIM_MAP[claim]
    overall = True
    for op, preds in constraints:
        if op == 'OR':
            if not any(fp.get(p, False) for p in preds): overall = False
        elif op == 'AND':
            if not all(fp.get(p, False) for p in preds): overall = False
        elif op == 'NOT_ANY':
            if any(fp.get(p, False) for p in preds): overall = False
    return overall

# Build claim-firing matrix
claims = list(CLAIM_MAP.keys())
nC = len(claims)
M = np.zeros((n, nC), dtype=np.int8)
for i, k in enumerate(keys):
    fp = all_fps[k]
    for j, claim in enumerate(claims):
        M[i, j] = 1 if evaluate_claim(fp, claim) else 0

# Per-claim fire rates
print(f"\n=== Per-claim fire rates ===")
for j, claim in enumerate(claims):
    print(f"  {claim:35s}: {M[:, j].mean():.3f} ({int(M[:, j].sum())}/{n})")

# Pairwise co-fire (Jaccard) matrix
print(f"\n=== Pairwise Jaccard between claims ===")
J = np.zeros((nC, nC))
for i in range(nC):
    for j in range(nC):
        a = set(np.where(M[:, i] == 1)[0])
        b = set(np.where(M[:, j] == 1)[0])
        u = len(a | b)
        J[i, j] = len(a & b) / u if u > 0 else 0
print(f"{'':35s}", end='')
for j, c in enumerate(claims):
    print(f"{c[:8]:>9s}", end='')
print()
for i, c in enumerate(claims):
    print(f"{c[:35]:35s}", end='')
    for j in range(nC):
        marker = "*" if i == j else " "
        print(f"{J[i,j]:>9.2f}", end='')
    print()

# Exclusivity check: claims that should be mutually exclusive
print(f"\n=== EXCLUSIVITY CHECKS (should have J=0 by claim definition) ===")
exclusive_pairs = [
    ("is indoors", "is outdoors"),  # complementary by definition
    ("has warm tones", "has cool tones"),  # somewhat exclusive
    ("is monochrome", "has warm tones"),  # monochrome shouldn't have color
    ("is monochrome", "has cool tones"),
    ("is monochrome", "has blue tones"),
]
violations = []
for a, b in exclusive_pairs:
    ai, bi = claims.index(a), claims.index(b)
    n_both = ((M[:, ai] == 1) & (M[:, bi] == 1)).sum()
    pct = 100 * n_both / n
    pass_threshold = "PASS" if n_both <= 5 else "VIOLATIONS" if n_both < 30 else "MAJOR FAIL"
    print(f"  {a} ∧ {b}: {n_both}/{n} = {pct:.1f}% [{pass_threshold}]")
    violations.append((a, b, int(n_both), pct))

# Expected correlation: horizon → outdoors
print(f"\n=== EXPECTED CORRELATIONS ===")
def cond_prob(a, b):  # P(b | a)
    ai, bi = claims.index(a), claims.index(b)
    a_fire = (M[:, ai] == 1).sum()
    if a_fire == 0: return None
    both = ((M[:, ai] == 1) & (M[:, bi] == 1)).sum()
    return both / a_fire

correlations = [
    ("has a horizon", "is outdoors", "horizons appear outside"),
    ("has vegetation", "is outdoors", "vegetation appears outside"),
    ("contains a person", "has warm tones", "human skin is warm — partial"),
    ("has blue tones", "has cool tones", "blue is cool"),
    ("is monochrome", "has low-key lighting", "monochrome darker often"),
    ("has high frequency detail", "is largely empty", "should anti-correlate"),
]
correlation_results = []
for a, b, note in correlations:
    p = cond_prob(a, b)
    if p is not None:
        flag = "STRONG" if p >= 0.80 else "GOOD" if p >= 0.60 else "WEAK" if p >= 0.30 else "NONE"
        print(f"  P({b} | {a}) = {p:.3f}  [{flag}]  ({note})")
        correlation_results.append({"prior": a, "consequent": b, "P_cond": float(p), "note": note, "flag": flag})

# Self-consistency score
total_violations = sum(v[2] for v in violations)
print(f"\n=== R171 self-consistency summary ===")
print(f"  Total exclusivity violations: {total_violations} across {len(violations)} pairs")
print(f"  Worst single pair: {max(violations, key=lambda x: x[2])}")
correlations_pass = sum(1 for c in correlation_results if c['flag'] in ('STRONG', 'GOOD'))
print(f"  Correlations PASS (≥0.60): {correlations_pass}/{len(correlation_results)}")

# Overall claim-verification health
indoors_outdoors_overlap = next((v for v in violations if v[:2] == ("is indoors", "is outdoors")), None)
indoors_outdoors_pct = indoors_outdoors_overlap[3] if indoors_outdoors_overlap else None
print(f"  indoors/outdoors complementarity: {indoors_outdoors_pct:.1f}% overlap" if indoors_outdoors_pct is not None else "")
horizon_outdoors_p = next((c['P_cond'] for c in correlation_results if c['prior']=="has a horizon"), None)
print(f"  horizon→outdoors P: {horizon_outdoors_p:.3f}" if horizon_outdoors_p else "")

audit = {
    "round": "R171", "date": "2026-05-01",
    "method": "Claim-verification self-consistency audit on N=623 corpus. Tests exclusivity violations and expected correlations as proxy for ground-truth accuracy (no manual labeling).",
    "n_corpus": n,
    "claim_fire_rates": {claims[j]: float(M[:, j].mean()) for j in range(nC)},
    "exclusivity_check": [{"a": v[0], "b": v[1], "n_both": v[2], "pct": v[3]} for v in violations],
    "expected_correlations": correlation_results,
    "summary": {
        "total_exclusivity_violations": int(total_violations),
        "correlations_passing": int(correlations_pass),
        "correlations_total": len(correlation_results),
        "indoors_outdoors_overlap_pct": indoors_outdoors_pct,
        "horizon_implies_outdoors_P": horizon_outdoors_p,
    },
}
out = OUT / "round171_audit.json"
out.write_text(json.dumps(audit, indent=2))
print(f"\nwrote {out}")
