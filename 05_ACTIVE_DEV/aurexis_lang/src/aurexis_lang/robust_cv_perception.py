from typing import Dict, Any, List

from .cv_primitive_extractor import extract_cv_primitives
from .cv_segmentation_upgrade import extract_segmented_primitives
from .cv_segmentation_quality import multi_threshold_segment, choose_best_segmentation

def fuse_perception_layers(image_path: str) -> Dict[str, Any]:
    cv_layer = extract_cv_primitives(image_path)
    seg_layer = extract_segmented_primitives(image_path)
    multi_layer = multi_threshold_segment(image_path)
    best_seg = choose_best_segmentation(multi_layer)

    primitive_candidates: List[Dict[str, Any]] = []
    primitive_candidates.extend(cv_layer.get("primitive_observations", []))
    primitive_candidates.extend(seg_layer.get("primitive_observations", []))
    if best_seg.get("status") == "ok":
        primitive_candidates.extend(best_seg.get("best_run", {}).get("primitive_observations", []))

    confidence_vals = []
    for item in primitive_candidates:
        confidence_vals.append(float(item.get("confidence", item.get("projection_confidence", 0.0))))

    avg_conf = (sum(confidence_vals) / len(confidence_vals)) if confidence_vals else 0.0
    stable = multi_layer.get("stability", {}).get("stable_across_thresholds", False)

    return {
        "source": image_path,
        "status": "ok",
        "layers": {
            "cv_layer_status": cv_layer.get("status"),
            "segmentation_status": seg_layer.get("status"),
            "multi_threshold_status": multi_layer.get("status", "ok"),
        },
        "candidate_count": len(primitive_candidates),
        "average_candidate_confidence": round(avg_conf, 4),
        "stable_across_thresholds": stable,
        "primitive_candidates": primitive_candidates,
        "notes": ["robust_cv_perception_scaffold_v1"],
    }

def summarize_perception_disagreement(bundle: Dict[str, Any]) -> Dict[str, Any]:
    candidates = bundle.get("primitive_candidates", [])
    roles = [c.get("attributes", {}).get("role", "unknown") for c in candidates]
    unique_roles = sorted(set(roles))
    return {
        "candidate_count": len(candidates),
        "unique_roles": unique_roles,
        "role_disagreement": len(unique_roles) > 3,
        "average_candidate_confidence": bundle.get("average_candidate_confidence", 0.0),
    }
