from typing import Dict, Any, List, Union
try:
    from PIL import Image, ImageFilter
except Exception:
    Image = None
    ImageFilter = None
import numpy as np

def _mean(vals):
    return sum(vals) / len(vals) if vals else 0.0

def _crop_stats(gray, box):
    crop = gray.crop(box)
    data = list(crop.getdata())
    if not data:
        return {"mean": 0.0, "dark_density": 0.0}
    mean = _mean(data)
    dark_density = sum(1 for px in data if px < 128) / len(data)
    return {"mean": mean, "dark_density": dark_density}

def _edge_density(gray):
    if ImageFilter is None:
        return 0.0
    edges = gray.filter(ImageFilter.FIND_EDGES)
    data = list(edges.getdata())
    if not data:
        return 0.0
    return sum(1 for px in data if px > 24) / len(data)

def extract_cv_primitives(image_input: Union[str, np.ndarray]) -> Dict[str, Any]:
    if Image is None:
        return {"source": str(image_input), "status": "pillow_missing", "primitive_observations": []}

    # Handle both file paths and numpy arrays
    if isinstance(image_input, str):
        img = Image.open(image_input).convert("L")
        source = image_input
    elif isinstance(image_input, np.ndarray):
        # Convert numpy array to PIL Image
        if len(image_input.shape) == 3:
            # Convert BGR to RGB then to grayscale
            img_rgb = image_input[:, :, ::-1]  # BGR to RGB
            img = Image.fromarray(img_rgb).convert("L")
        else:
            img = Image.fromarray(image_input).convert("L")
        source = "numpy_array"
    else:
        return {"source": str(image_input), "status": "unsupported_input", "primitive_observations": []}
    w, h = img.size

    center_box = (int(w*0.35), int(h*0.35), int(w*0.65), int(h*0.65))
    ring_boxes = [
        (int(w*0.25), int(h*0.25), int(w*0.75), int(h*0.35)),
        (int(w*0.25), int(h*0.65), int(w*0.75), int(h*0.75)),
        (int(w*0.25), int(h*0.35), int(w*0.35), int(h*0.65)),
        (int(w*0.65), int(h*0.35), int(w*0.75), int(h*0.65)),
    ]
    outer_boxes = [
        (0, 0, int(w*0.25), h),
        (int(w*0.75), 0, w, h),
    ]

    center = _crop_stats(img, center_box)
    ring_stats = [_crop_stats(img, b) for b in ring_boxes]
    outer_stats = [_crop_stats(img, b) for b in outer_boxes]

    ring_mean = _mean([r["mean"] for r in ring_stats])
    ring_dark = _mean([r["dark_density"] for r in ring_stats])
    outer_mean = _mean([r["mean"] for r in outer_stats])
    outer_dark = _mean([r["dark_density"] for r in outer_stats])

    edge_density = _edge_density(img)
    center_contrast = abs(center["dark_density"] - ring_dark)
    ring_outer_contrast = abs(ring_dark - outer_dark)

    observations: List[Dict[str, Any]] = [
        {
            "primitive_type": "region",
            "attributes": {"role": "control", "value": "central_sigil_candidate"},
            "confidence": round(min(1.0, 0.45 + center_contrast), 3),
        },
        {
            "primitive_type": "region",
            "attributes": {"role": "delimiter", "value": "transition_ring_candidate"},
            "confidence": round(min(1.0, 0.45 + ring_outer_contrast), 3),
        },
        {
            "primitive_type": "region",
            "attributes": {"role": "literal", "value": "outer_field_candidate"},
            "confidence": round(min(1.0, 0.45 + outer_dark), 3),
        },
        {
            "primitive_type": "alignment",
            "attributes": {"role": "sequence_marker", "value": "edge_grid_candidate"},
            "confidence": round(min(1.0, 0.35 + edge_density), 3),
        },
    ]

    return {
        "source": source,
        "status": "ok",
        "image_size": {"width": w, "height": h},
        "features": {
            "edge_density": round(edge_density, 4),
            "center_dark_density": round(center["dark_density"], 4),
            "ring_dark_density": round(ring_dark, 4),
            "outer_dark_density": round(outer_dark, 4),
            "center_ring_contrast": round(center_contrast, 4),
            "ring_outer_contrast": round(ring_outer_contrast, 4),
        },
        "primitive_observations": observations,
        "notes": ["cv_style_heuristic_layer_v1"],
    }

def cv_image_to_parser_bundle(image_input: Union[str, np.ndarray]) -> Dict[str, Any]:
    return extract_cv_primitives(image_input)
