import json
from pathlib import Path
from typing import Dict, Any, List

from .learned_candidate_model import score_candidate_row

def load_dataset_manifest(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))

def run_training_loop_scaffold(manifest: Dict[str, Any]) -> Dict[str, Any]:
    split_stats: Dict[str, Dict[str, Any]] = {}
    for row in manifest.get("rows", []):
        split = row.get("split", "unknown")
        split_stats.setdefault(split, {"count": 0, "sources": []})
        split_stats[split]["count"] += 1
        split_stats[split]["sources"].append(row.get("source"))

    # fabricate row-shaped items from manifest rows for scoring reuse
    ranked_inputs: List[Dict[str, Any]] = []
    for row in manifest.get("rows", []):
        ranked_inputs.append({
            "source": row.get("source"),
            "provenance": row.get("provenance", "unknown"),
            "feature_vector": {
                "average_candidate_confidence": row.get("usefulness_score", 0.0),
                "stable_across_thresholds": True,
                "role_disagreement": False,
                "unique_role_count": max(1, int(row.get("label_count", 1))),
            },
        })

    scored = [score_candidate_row(r) for r in ranked_inputs]
    avg_score = (sum(item["score"] for item in scored) / len(scored)) if scored else 0.0

    return {
        "row_count": len(manifest.get("rows", [])),
        "split_stats": split_stats,
        "average_score": round(avg_score, 4),
        "scored_rows": scored,
        "status": "training_loop_scaffold_ok",
    }

def write_training_loop_outputs(manifest_path: str, out_path: str) -> Dict[str, Any]:
    manifest = load_dataset_manifest(manifest_path)
    result = run_training_loop_scaffold(manifest)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return {"status": "ok", "out_path": str(out), "row_count": result["row_count"]}
