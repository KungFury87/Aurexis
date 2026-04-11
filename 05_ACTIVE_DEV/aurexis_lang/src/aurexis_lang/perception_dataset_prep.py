import json
from pathlib import Path
from typing import Dict, Any, List

def load_rows(path: str) -> List[Dict[str, Any]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))

def rank_row_usefulness(row: Dict[str, Any]) -> float:
    fv = row.get("feature_vector", {})
    score = 0.0
    score += min(1.0, float(fv.get("average_candidate_confidence", 0.0)))
    score += 0.2 if fv.get("stable_across_thresholds", False) else 0.0
    score -= 0.15 if fv.get("role_disagreement", False) else 0.0
    score += min(0.3, float(fv.get("unique_role_count", 0)) * 0.05)
    if row.get("provenance") == "observed":
        score += 0.25
    return round(max(0.0, score), 4)

def assign_split(index: int) -> str:
    mod = index % 10
    if mod < 7:
        return "train"
    if mod < 9:
        return "validation"
    return "test"

def build_dataset_manifest(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    manifest_rows = []
    for idx, row in enumerate(rows):
        manifest_rows.append({
            "source": row.get("source"),
            "provenance": row.get("provenance", "unknown"),
            "split": assign_split(idx),
            "usefulness_score": rank_row_usefulness(row),
            "label_count": len(row.get("labels", [])),
            "status": row.get("status", "unknown"),
        })
    return {
        "row_count": len(manifest_rows),
        "rows": manifest_rows,
    }

def write_dataset_manifest(rows_path: str, out_path: str) -> Dict[str, Any]:
    rows = load_rows(rows_path)
    manifest = build_dataset_manifest(rows)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {
        "status": "ok",
        "out_path": str(out),
        "row_count": manifest["row_count"],
    }
