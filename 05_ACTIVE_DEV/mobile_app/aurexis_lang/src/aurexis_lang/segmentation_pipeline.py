from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Union

try:
    from PIL import Image
except Exception:
    Image = None
import numpy as np

@dataclass
class SegmentCandidate:
    segment_id: str
    role_hint: str
    bbox: Dict[str, int]
    confidence: float

def coarse_partition(image_input: Union[str, np.ndarray]) -> Dict[str, Any]:
    if Image is None:
        return {"status": "pillow_missing", "segments": []}
    
    # Handle both file paths and numpy arrays
    if isinstance(image_input, str):
        img = Image.open(image_input).convert("L")
    elif isinstance(image_input, np.ndarray):
        if len(image_input.shape) == 3:
            img_rgb = image_input[:, :, ::-1]  # BGR to RGB
            img = Image.fromarray(img_rgb).convert("L")
        else:
            img = Image.fromarray(image_input).convert("L")
    else:
        return {"status": "unsupported_input", "segments": []}
        
    w, h = img.size
    segments = [
        SegmentCandidate("seg_center", "control", {"x0": int(w*0.35), "y0": int(h*0.35), "x1": int(w*0.65), "y1": int(h*0.65)}, 0.72),
        SegmentCandidate("seg_ring", "delimiter", {"x0": int(w*0.25), "y0": int(h*0.25), "x1": int(w*0.75), "y1": int(h*0.75)}, 0.68),
        SegmentCandidate("seg_outer", "literal", {"x0": 0, "y0": 0, "x1": w, "y1": h}, 0.63),
    ]
    return {"status": "ok", "image_size": {"width": w, "height": h}, "segments": [asdict(s) for s in segments]}

def segments_to_primitives(segmentation_result: Dict[str, Any]) -> Dict[str, Any]:
    primitive_observations = []
    for seg in segmentation_result.get("segments", []):
        primitive_observations.append({
            "primitive_type": "region",
            "attributes": {
                "role": seg["role_hint"],
                "value": seg["segment_id"],
                "bbox": seg["bbox"],
            },
            "stage_confidence": seg["confidence"],
            "projection_confidence": round(min(1.0, seg["confidence"] + 0.08), 3),
            "confidence": round(min(1.0, seg["confidence"] + 0.05), 3),
        })
    return {
        "status": segmentation_result.get("status", "unknown"),
        "primitive_observations": primitive_observations,
    }

def image_to_segmented_parser_bundle(image_input: Union[str, np.ndarray]) -> Dict[str, Any]:
    seg = coarse_partition(image_input)
    bundle = segments_to_primitives(seg)
    return {
        "source": str(image_input),
        "segmentation": seg,
        "bundle": bundle,
    }
