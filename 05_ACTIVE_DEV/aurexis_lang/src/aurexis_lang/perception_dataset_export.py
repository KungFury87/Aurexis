import json
from pathlib import Path
from typing import Dict, Any, List

from .robust_cv_perception import fuse_perception_layers, summarize_perception_disagreement

def perception_row_from_image(image_path: str, provenance: str = "synthetic") -> Dict[str, Any]:
    fused = fuse_perception_layers(image_path)
    disagreement = summarize_perception_disagreement(fused)
    feature_vector = {
        "candidate_count": fused.get("candidate_count", 0),
        "average_candidate_confidence": fused.get("average_candidate_confidence", 0.0),
        "stable_across_thresholds": fused.get("stable_across_thresholds", False),
        "role_disagreement": disagreement.get("role_disagreement", False),
        "unique_role_count": len(disagreement.get("unique_roles", [])),
    }
    labels = []
    for item in fused.get("primitive_candidates", []):
        labels.append({
            "role": item.get("attributes", {}).get("role", "unknown"),
            "value": item.get("attributes", {}).get("value", "unknown"),
            "confidence": item.get("confidence", item.get("projection_confidence", 0.0)),
        })
    return {
        "source": image_path,
        "provenance": provenance,
        "feature_vector": feature_vector,
        "labels": labels,
        "status": fused.get("status", "unknown"),
    }

def export_dataset_rows(image_paths: List[str], out_path: str, provenance: str = "synthetic") -> Dict[str, Any]:
    rows = [perception_row_from_image(path, provenance=provenance) for path in image_paths]
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return {"status": "ok", "row_count": len(rows), "out_path": str(out)}
