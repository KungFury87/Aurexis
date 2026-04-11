from typing import Dict, Any, List

from .learned_candidate_model import rank_candidate_rows

def infer_from_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    ranked = rank_candidate_rows(rows)
    items = ranked.get("ranked_rows", [])
    top = items[0] if items else None
    alternatives = items[1:] if len(items) > 1 else []

    ambiguous = False
    if len(items) >= 2:
        ambiguous = abs(items[0]["score"] - items[1]["score"]) < 0.12

    provenance = sorted(set(i.get("provenance", "unknown") for i in items))

    return {
        "row_count": ranked.get("row_count", 0),
        "top_candidate": top,
        "alternatives": alternatives,
        "ambiguous": ambiguous,
        "provenance_summary": provenance,
    }
