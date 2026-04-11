from typing import Dict, Any, List

def score_candidate_row(row: Dict[str, Any]) -> Dict[str, Any]:
    fv = row.get("feature_vector", {})
    score = 0.0
    score += float(fv.get("average_candidate_confidence", 0.0))
    score += 0.15 if fv.get("stable_across_thresholds", False) else 0.0
    score -= 0.12 if fv.get("role_disagreement", False) else 0.0
    score += min(0.25, float(fv.get("unique_role_count", 0)) * 0.04)
    score += 0.20 if row.get("provenance") == "observed" else 0.0

    if score >= 1.1:
        tier = "A"
    elif score >= 0.8:
        tier = "B"
    elif score >= 0.5:
        tier = "C"
    else:
        tier = "D"

    return {
        "source": row.get("source"),
        "score": round(score, 4),
        "tier": tier,
        "provenance": row.get("provenance", "unknown"),
    }

def rank_candidate_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    ranked = [score_candidate_row(r) for r in rows]
    ranked.sort(key=lambda r: r["score"], reverse=True)
    return {
        "row_count": len(ranked),
        "ranked_rows": ranked,
    }
