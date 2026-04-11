from collections import deque
from typing import Dict, Any, List

try:
    from PIL import Image
except Exception:
    Image = None

def _to_binary(gray, threshold=128):
    w, h = gray.size
    data = list(gray.getdata())
    mask = [[0] * w for _ in range(h)]
    idx = 0
    for y in range(h):
        row = mask[y]
        for x in range(w):
            row[x] = 1 if data[idx] < threshold else 0
            idx += 1
    return mask

def _neighbors(x, y, w, h):
    for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < w and 0 <= ny < h:
            yield nx, ny

def _connected_components(mask):
    h = len(mask)
    w = len(mask[0]) if h else 0
    seen = [[False] * w for _ in range(h)]
    comps = []

    for y in range(h):
        for x in range(w):
            if mask[y][x] != 1 or seen[y][x]:
                continue
            q = deque([(x, y)])
            seen[y][x] = True
            pts = []
            while q:
                cx, cy = q.popleft()
                pts.append((cx, cy))
                for nx, ny in _neighbors(cx, cy, w, h):
                    if mask[ny][nx] == 1 and not seen[ny][nx]:
                        seen[ny][nx] = True
                        q.append((nx, ny))
            comps.append(pts)
    return comps

def _bbox(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return {
        "x0": min(xs), "y0": min(ys),
        "x1": max(xs) + 1, "y1": max(ys) + 1,
    }

def _project_role(bbox, image_w, image_h):
    cx = (bbox["x0"] + bbox["x1"]) / 2.0 / image_w
    cy = (bbox["y0"] + bbox["y1"]) / 2.0 / image_h
    area = (bbox["x1"] - bbox["x0"]) * (bbox["y1"] - bbox["y0"])
    if 0.35 <= cx <= 0.65 and 0.35 <= cy <= 0.65:
        return "control", "seg_center_candidate"
    if area < (image_w * image_h) * 0.01:
        return "sequence_marker", "seg_small_component"
    return "literal", "seg_outer_component"

def extract_segmented_primitives(image_path: str, threshold: int = 128, min_area_ratio: float = 0.002) -> Dict[str, Any]:
    if Image is None:
        return {"source": image_path, "status": "pillow_missing", "primitive_observations": []}

    img = Image.open(image_path).convert("L")
    w, h = img.size
    mask = _to_binary(img, threshold=threshold)
    comps = _connected_components(mask)

    min_area = max(1, int(w * h * min_area_ratio))
    segments = []
    observations = []

    for idx, comp in enumerate(comps, start=1):
        area = len(comp)
        if area < min_area:
            continue
        bbox = _bbox(comp)
        role, value = _project_role(bbox, w, h)
        area_ratio = area / float(w * h)
        conf = min(1.0, 0.45 + min(0.45, area_ratio * 10))
        seg = {
            "segment_id": f"cc_{idx:03d}",
            "bbox": bbox,
            "area": area,
            "area_ratio": round(area_ratio, 5),
            "role_hint": role,
            "value_hint": value,
            "confidence": round(conf, 3),
        }
        segments.append(seg)
        observations.append({
            "primitive_type": "region",
            "attributes": {
                "role": role,
                "value": value,
                "bbox": bbox,
                "segment_id": seg["segment_id"],
            },
            "stage_confidence": seg["confidence"],
            "projection_confidence": round(min(1.0, seg["confidence"] + 0.05), 3),
            "confidence": round(min(1.0, seg["confidence"] + 0.03), 3),
        })

    return {
        "source": image_path,
        "status": "ok",
        "image_size": {"width": w, "height": h},
        "threshold": threshold,
        "component_count": len(comps),
        "retained_segments": segments,
        "primitive_observations": observations,
        "notes": ["connected_components_segmentation_v1"],
    }

def segmented_image_to_parser_bundle(image_path: str, threshold: int = 128, min_area_ratio: float = 0.002) -> Dict[str, Any]:
    return extract_segmented_primitives(image_path, threshold=threshold, min_area_ratio=min_area_ratio)
