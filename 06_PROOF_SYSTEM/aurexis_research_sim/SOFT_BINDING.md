# Aurexis Research Sim v1.2 - Soft-binding dossier

For each composite sub-primitive we evaluate under the
perfect ROI (v1.1) plus four imperfect-ROI modes:

- `perfect`
- `dilate_extra`
- `erode`
- `shift_px`
- `noisy_10pct`

Verdict:
- **ROBUST_TO_SOFT_BINDING**  all soft modes >= 0.80
- **NEEDS_TIGHT_BINDING**     perfect passes, at least one soft mode < 0.80
- **FAILS_EVEN_PERFECT**      perfect < 0.80 (from v1.1)

## Overall summary
| composite | overall verdict |
|-----------|-----------------|
| composite_ordering_role_zone | **ROBUST_TO_SOFT_BINDING** |
| composite_repetition_cardinality | **NEEDS_TIGHT_BINDING** |
| composite_ordering_crowded_by_adjacency | **ROBUST_TO_SOFT_BINDING** |

### composite_ordering_role_zone
- overall_verdict: **ROBUST_TO_SOFT_BINDING**
| sub | kind | unbound | perfect | dilate_extra | erode | shift_px | noisy_10pct | worst_soft_mode | worst_soft_score | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| ordering | ordering | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | dilate_extra | 1.000 | ROBUST_TO_SOFT_BINDING |
| role_zone | role_zone | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | dilate_extra | 1.000 | ROBUST_TO_SOFT_BINDING |

### composite_repetition_cardinality
- overall_verdict: **NEEDS_TIGHT_BINDING**
| sub | kind | unbound | perfect | dilate_extra | erode | shift_px | noisy_10pct | worst_soft_mode | worst_soft_score | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| repetition | repetition | 0.921 | 0.958 | 0.921 | 0.523 | 0.995 | 0.605 | erode | 0.523 | NEEDS_TIGHT_BINDING |
| cardinality | cardinality | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | noisy_10pct | 0.000 | NEEDS_TIGHT_BINDING |

### composite_ordering_crowded_by_adjacency
- overall_verdict: **ROBUST_TO_SOFT_BINDING**
| sub | kind | unbound | perfect | dilate_extra | erode | shift_px | noisy_10pct | worst_soft_mode | worst_soft_score | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| ordering | ordering | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | dilate_extra | 1.000 | ROBUST_TO_SOFT_BINDING |
| adjacency | adjacency | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | dilate_extra | 1.000 | ROBUST_TO_SOFT_BINDING |
