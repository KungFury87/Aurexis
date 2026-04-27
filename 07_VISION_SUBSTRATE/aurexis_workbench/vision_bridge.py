"""Bridge from raw captures (.aurex-session zips) to Workbench FieldBundles.

Loads a session, builds a typed FieldBundle with the fields a vision
vocabulary expects (scene, burst, raw_bayer, cap_axis_0, cap_axis_90,
patch_size), then a runtime can evaluate the vocabulary against it.

This is the seam between the world (real captured photons through the
phone) and the language (typed predicates over instruments).
"""
from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image

from .fields import FieldBundle, FieldSpec, FieldValue


def _rgb_to_luma(arr: np.ndarray) -> np.ndarray:
    return 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]


@dataclass
class SessionMeta:
    session_id: str
    protocol_id: str
    device_model: str
    n_frames: int
    burst_actual_median_ms: Optional[float]
    light_lux_median: Optional[float]
    schema: Optional[str]


def load_session_bundle(zip_path: str | Path,
                          max_frames: int = 10,
                          resize_to: int = 256,
                          patch_size: int = 64,
                          ) -> Tuple[FieldBundle, SessionMeta]:
    """Load a .aurex-session zip into a typed FieldBundle.

    Always populated:
        scene       (image)         middle frame as luminance
        burst       (image_stack)   all decoded frames stacked
        patch_size  (int)           parameter for ROI predicates

    Conditionally populated (only if the harness captured the
    relevant data; otherwise these fields are simply not present):
        raw_bayer   (image)         raw Bayer mosaic (harness v3.0+)
        cap_axis_0  (image)         polarization-pair axis 0 (v2.2+)
        cap_axis_90 (image)         polarization-pair axis 90 (v2.2+)
    """
    p = Path(zip_path)
    if not p.exists():
        raise FileNotFoundError(p)
    with zipfile.ZipFile(p, "r") as zf:
        manifest_name = next((n for n in zf.namelist()
                                if n.endswith("manifest.json")), None)
        if manifest_name is None:
            raise ValueError(f"no manifest.json in {p.name}")
        manifest = json.loads(zf.read(manifest_name).decode("utf-8"))
        frames_meta = sorted(manifest["frames"],
                              key=lambda f: f.get("frameIndex", 0))
        if max_frames is not None:
            frames_meta = frames_meta[:max_frames]
        all_names = zf.namelist()
        decoded: List[np.ndarray] = []
        axis_labels: List[Optional[str]] = []
        for fm in frames_meta:
            target = fm["filename"]
            cand = [n for n in all_names if n.endswith(target)]
            if not cand:
                continue
            with zf.open(cand[0]) as fh:
                img = Image.open(io.BytesIO(fh.read()))
                img.load()
            arr = np.asarray(img, dtype=np.float64) / 255.0
            luma = _rgb_to_luma(arr[..., :3]) if arr.ndim == 3 else arr
            if resize_to is not None:
                long_side = max(luma.shape[0], luma.shape[1])
                if long_side > resize_to:
                    step = max(1, long_side // resize_to)
                    luma = luma[::step, ::step]
            decoded.append(luma.astype(np.float64))
            axis_labels.append(fm.get("axisLabel"))
    if not decoded:
        raise ValueError(f"no frames decoded from {p.name}")
    h_min = min(a.shape[0] for a in decoded)
    w_min = min(a.shape[1] for a in decoded)
    decoded = [a[:h_min, :w_min] for a in decoded]
    burst = np.stack(decoded, axis=0)
    scene = burst[len(decoded) // 2]

    bundle = FieldBundle(name=p.stem)
    bundle.add_value("scene", "image", scene,
                      description="middle-frame luminance")
    bundle.add_value("burst", "image_stack", burst,
                      description="decoded burst frames as luminance")
    bundle.add_value("patch_size", "int", int(patch_size),
                      description="ROI side length for patch predicates")

    # If the harness recorded axis labels, populate cap_axis_0 / cap_axis_90.
    if any(str(a) in ("0", "0deg") for a in axis_labels) and \
       any(str(a) in ("90", "90deg") for a in axis_labels):
        idx_0 = [i for i, a in enumerate(axis_labels)
                  if str(a) in ("0", "0deg")]
        idx_90 = [i for i, a in enumerate(axis_labels)
                   if str(a) in ("90", "90deg")]
        if idx_0 and idx_90:
            cap0 = float_mean_frames(burst, idx_0)
            cap90 = float_mean_frames(burst, idx_90)
            bundle.add_value("cap_axis_0", "image", cap0,
                              description="axis-0 mean frame")
            bundle.add_value("cap_axis_90", "image", cap90,
                              description="axis-90 mean frame")

    # raw_bayer field: not yet plumbed - the harness needs Camera2 RAW
    # capture before this can be populated. The vocabulary's
    # Bayer-dependent predicates will simply error with
    # "field not in bundle" if asked to evaluate on a JPEG-only session.

    meta = SessionMeta(
        session_id=manifest.get("sessionId") or p.stem.split(".")[0],
        protocol_id=frames_meta[0].get("protocolId", "unknown"),
        device_model=manifest.get("device", {}).get("model", "unknown"),
        n_frames=len(decoded),
        burst_actual_median_ms=manifest.get("burstActualMedianMs"),
        light_lux_median=_median_or_none(
            [f.get("lightLux") for f in frames_meta]),
        schema=manifest.get("schema"),
    )
    return bundle, meta


def float_mean_frames(stack: np.ndarray, indices: list) -> np.ndarray:
    return np.mean(stack[indices], axis=0)


def _median_or_none(vals):
    cleaned = [v for v in vals if v is not None]
    if not cleaned:
        return None
    return float(np.median(cleaned))


def find_sessions(root: str | Path) -> List[Path]:
    return sorted(Path(root).rglob("*.aurex-session.zip"))
