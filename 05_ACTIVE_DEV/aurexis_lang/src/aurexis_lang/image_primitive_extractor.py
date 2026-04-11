from pathlib import Path
from typing import Dict, Any, List
import json

try:
    from PIL import Image
except Exception:
    Image = None

def _region_stats(gray, x0, y0, x1, y1):
    crop = gray.crop((x0, y0, x1, y1))
    data = list(crop.getdata())
    if not data:
        return {"mean": 0.0, "density": 0.0}
    mean = sum(data) / len(data)
    # very coarse dark-density proxy
    density = sum(1 for px in data if px < 128) / len(data)
    return {"mean": mean, "density": density}

def extract_image_primitives(image_path: str) -> Dict[str, Any]:
    if Image is None:
        return {
            "source": image_path,
            "status": "pillow_missing",
            "primitive_observations": [],
        }

    img = Image.open(image_path).convert("L")
    w, h = img.size
    cx0, cy0 = int(w * 0.35), int(h * 0.35)
    cx1, cy1 = int(w * 0.65), int(h * 0.65)

    center = _region_stats(img, cx0, cy0, cx1, cy1)

    # crude ring approximation: middle band excluding center
    ring_boxes = [
        (int(w*0.25), int(h*0.25), int(w*0.75), int(h*0.35)),
        (int(w*0.25), int(h*0.65), int(w*0.75), int(h*0.75)),
        (int(w*0.25), int(h*0.35), int(w*0.35), int(h*0.65)),
        (int(w*0.65), int(h*0.35), int(w*0.75), int(h*0.65)),
    ]
    ring_stats = []
    for box in ring_boxes:
        ring_stats.append(_region_stats(img, *box))
    ring_mean = sum(r["mean"] for r in ring_stats) / len(ring_stats)
    ring_density = sum(r["density"] for r in ring_stats) / len(ring_stats)

    outer_boxes = [
        (0, 0, int(w*0.25), h),
        (int(w*0.75), 0, w, h),
    ]
    outer_stats = []
    for box in outer_boxes:
        outer_stats.append(_region_stats(img, *box))
    outer_mean = sum(r["mean"] for r in outer_stats) / len(outer_stats)
    outer_density = sum(r["density"] for r in outer_stats) / len(outer_stats)

    observations: List[Dict[str, Any]] = [
        {
            "primitive_type": "region",
            "attributes": {"role": "control", "value": "central_sigil_candidate"},
            "confidence": round(min(1.0, 0.5 + abs(center["density"] - ring_density)), 3),
        },
        {
            "primitive_type": "region",
            "attributes": {"role": "delimiter", "value": "transition_ring_candidate"},
            "confidence": round(min(1.0, 0.5 + abs(ring_density - outer_density)), 3),
        },
        {
            "primitive_type": "region",
            "attributes": {"role": "literal", "value": "outer_field_candidate"},
            "confidence": round(min(1.0, 0.5 + outer_density), 3),
        },
    ]

    return {
        "source": image_path,
        "status": "ok",
        "image_size": {"width": w, "height": h},
        "center_stats": center,
        "ring_stats": {"mean": ring_mean, "density": ring_density},
        "outer_stats": {"mean": outer_mean, "density": outer_density},
        "primitive_observations": observations,
    }

def image_to_parser_bundle(image_path: str) -> Dict[str, Any]:
    return extract_image_primitives(image_path)
