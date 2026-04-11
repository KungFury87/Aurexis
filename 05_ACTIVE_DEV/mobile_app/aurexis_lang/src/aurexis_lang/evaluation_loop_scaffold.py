from typing import Dict, Any, List

from .learned_candidate_model import score_candidate_row

def evaluate_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    evaluated = []
    hits = 0
    for row in rows:
        scored = score_candidate_row(row)
        expected_role = row.get("expected_top_role")
        predicted_role = None
        labels = row.get("labels", [])
        if labels:
            predicted_role = labels[0].get("role")
        hit = expected_role is None or expected_role == predicted_role
        if hit:
            hits += 1
        evaluated.append({
            "source": row.get("source"),
            "provenance": row.get("provenance", "unknown"),
            "score": scored["score"],
            "tier": scored["tier"],
            "expected_top_role": expected_role,
            "predicted_top_role": predicted_role,
            "hit": hit,
        })
    total = len(evaluated)
    return {
        "row_count": total,
        "hit_count": hits,
        "hit_rate": (hits / total) if total else 0.0,
        "rows": evaluated,
    }

def summarize_by_provenance(result: Dict[str, Any]) -> Dict[str, Any]:
    groups = {}
    for row in result.get("rows", []):
        prov = row.get("provenance", "unknown")
        groups.setdefault(prov, {"count": 0, "hits": 0})
        groups[prov]["count"] += 1
        groups[prov]["hits"] += 1 if row.get("hit") else 0
    for prov, info in groups.items():
        info["hit_rate"] = (info["hits"] / info["count"]) if info["count"] else 0.0
    return groups
