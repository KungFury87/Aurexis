from typing import Dict, Any, List

from .cv_segmentation_upgrade import extract_segmented_primitives

def multi_threshold_segment(image_path: str, thresholds=None, min_area_ratio: float = 0.002) -> Dict[str, Any]:
    thresholds = thresholds or [96, 128, 160]
    runs = []
    for thr in thresholds:
        result = extract_segmented_primitives(image_path, threshold=thr, min_area_ratio=min_area_ratio)
        runs.append({
            "threshold": thr,
            "component_count": result.get("component_count", 0),
            "retained_segments": result.get("retained_segments", []),
            "primitive_observations": result.get("primitive_observations", []),
        })

    # simple stability summary
    retained_counts = [len(r["retained_segments"]) for r in runs]
    avg_retained = (sum(retained_counts) / len(retained_counts)) if retained_counts else 0.0
    stable = max(retained_counts) - min(retained_counts) <= 1 if retained_counts else False

    return {
        "source": image_path,
        "status": "ok",
        "thresholds": thresholds,
        "runs": runs,
        "stability": {
            "retained_counts": retained_counts,
            "average_retained": avg_retained,
            "stable_across_thresholds": stable,
        },
    }

def choose_best_segmentation(segmentation_bundle: Dict[str, Any]) -> Dict[str, Any]:
    runs = segmentation_bundle.get("runs", [])
    if not runs:
        return {"status": "no_runs"}
    # prefer the run with the most retained segments, then smallest threshold distance from 128
    ranked = sorted(
        runs,
        key=lambda r: (len(r.get("retained_segments", [])), -abs(r.get("threshold", 128) - 128)),
        reverse=True,
    )
    best = ranked[0]
    return {
        "status": "ok",
        "best_threshold": best.get("threshold"),
        "retained_segment_count": len(best.get("retained_segments", [])),
        "primitive_count": len(best.get("primitive_observations", [])),
        "best_run": best,
    }
