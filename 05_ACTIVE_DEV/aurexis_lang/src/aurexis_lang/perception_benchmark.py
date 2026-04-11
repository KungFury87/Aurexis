from typing import Dict, Any, List

def _score_with_profile(row: Dict[str, Any], profile: Dict[str, float]) -> float:
    fv = row.get("feature_vector", {})
    score = 0.0
    score += profile.get("confidence_weight", 1.0) * float(fv.get("average_candidate_confidence", 0.0))
    score += profile.get("stability_bonus", 0.0) if fv.get("stable_across_thresholds", False) else 0.0
    score -= profile.get("disagreement_penalty", 0.0) if fv.get("role_disagreement", False) else 0.0
    score += min(profile.get("role_count_cap", 0.25), float(fv.get("unique_role_count", 0)) * profile.get("role_count_weight", 0.04))
    if row.get("provenance") == "observed":
        score += profile.get("observed_bonus", 0.2)
    return round(score, 4)

def benchmark_profiles(rows: List[Dict[str, Any]], profiles: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
    profile_results = {}
    for name, profile in profiles.items():
        scored = []
        for row in rows:
            score = _score_with_profile(row, profile)
            scored.append({"source": row.get("source"), "score": score})
        avg = (sum(float(item["score"]) for item in scored) / len(scored)) if scored else 0.0
        profile_results[name] = {
            "average_score": float(round(avg, 4)),
            "rows": scored,
        }
    best_name = max(profile_results.keys(), key=lambda k: profile_results[k]["average_score"]) if profile_results else None
    return {
        "profile_count": int(len(profile_results)),
        "best_profile": best_name,
        "profiles": profile_results,
    }
