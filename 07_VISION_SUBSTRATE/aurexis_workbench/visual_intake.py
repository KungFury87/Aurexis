"""Generic visual intake - feed ANY visual input into the language.

The vision language operates on `image` (2-D float array in [0,1]) and
`image_stack` (3-D). Where those tensors come from is irrelevant to
the predicates. This module turns:

  - a single image file (jpg/png/bmp/tiff/webp/heic/...)
  - a directory of images
  - a video file (mp4/mov/avi/...)
  - a pair of images (axis 0 / axis 90)

into a typed FieldBundle the Workbench runtime can evaluate the
vocabulary against. Substrate-agnostic by design.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image

from .fields import FieldBundle


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff",
                ".webp", ".heic", ".heif", ".gif"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


def _rgb_to_luma(arr: np.ndarray) -> np.ndarray:
    if arr.ndim == 2:
        return arr.astype(np.float64)
    a = arr[..., :3].astype(np.float64)
    return 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]


def _decode_image(path: str | Path,
                   resize_to: Optional[int] = 512) -> np.ndarray:
    """Decode and return luma. Use _decode_image_color for RGB."""
    luma, _ = _decode_image_color(path, resize_to=resize_to)
    return luma


def _decode_image_color(path: str | Path,
                          resize_to: Optional[int] = 512
                          ) -> tuple:
    """Returns (luma, color_rgb). color_rgb is HxWx3 in [0,1]."""
    img = Image.open(str(path))
    img.load()
    arr = np.asarray(img, dtype=np.float64)
    if arr.max() > 1.5:
        arr = arr / 255.0
    if arr.ndim == 2:
        # grayscale -> stack to RGB for color_image
        color = np.stack([arr, arr, arr], axis=-1)
        luma = arr.astype(np.float64)
    else:
        color = arr[..., :3].astype(np.float64)
        luma = _rgb_to_luma(arr)
    if resize_to is not None:
        long_side = max(luma.shape[0], luma.shape[1])
        if long_side > resize_to:
            step = max(1, long_side // resize_to)
            luma = luma[::step, ::step]
            color = color[::step, ::step]
    return luma.astype(np.float64), color.astype(np.float64)


def _decode_video(path: str | Path,
                   max_frames: int = 16,
                   resize_to: Optional[int] = 512) -> np.ndarray:
    """Sample up to max_frames evenly across the video. Uses imageio
    if available; falls back to ffmpeg via subprocess if needed."""
    try:
        import imageio.v3 as iio
        frames = []
        meta = iio.immeta(str(path))
        n_total = meta.get("nframes")
        if not n_total or n_total <= 0:
            # stream and stop after we have enough
            for i, fr in enumerate(iio.imiter(str(path))):
                frames.append(fr)
                if len(frames) >= max_frames * 4:
                    break
            if len(frames) > max_frames:
                idxs = np.linspace(0, len(frames) - 1, max_frames).astype(int)
                frames = [frames[i] for i in idxs]
        else:
            idxs = np.linspace(0, n_total - 1, min(max_frames, n_total)).astype(int)
            for i in idxs:
                frames.append(iio.imread(str(path), index=int(i)))
        decoded = []
        for fr in frames:
            arr = np.asarray(fr, dtype=np.float64)
            if arr.max() > 1.5:
                arr = arr / 255.0
            luma = _rgb_to_luma(arr)
            if resize_to is not None:
                long_side = max(luma.shape[0], luma.shape[1])
                if long_side > resize_to:
                    step = max(1, long_side // resize_to)
                    luma = luma[::step, ::step]
            decoded.append(luma.astype(np.float64))
        h_min = min(a.shape[0] for a in decoded)
        w_min = min(a.shape[1] for a in decoded)
        decoded = [a[:h_min, :w_min] for a in decoded]
        return np.stack(decoded, axis=0)
    except ImportError:
        raise RuntimeError(
            "video decoding needs imageio: pip install imageio imageio-ffmpeg")


@dataclass
class VisualMeta:
    source: str
    kind: str   # "image" / "image_dir" / "video" / "image_pair"
    n_frames: int = 1
    resolution: Tuple[int, int] = (0, 0)


def bundle_from_path(path: str | Path,
                       max_frames: int = 16,
                       resize_to: Optional[int] = 512,
                       patch_size: int = 64,
                       ) -> Tuple[FieldBundle, VisualMeta]:
    """Single entry point. path can be:
      - a single image file
      - a directory containing image files (sorted -> image_stack)
      - a video file
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)

    if p.is_dir():
        files = sorted([f for f in p.iterdir()
                          if f.suffix.lower() in IMAGE_EXTS])
        if not files:
            raise ValueError(f"no images in directory {p}")
        decoded = [_decode_image_color(f, resize_to=resize_to) for f in files]
        frames = [d[0] for d in decoded]
        colors = [d[1] for d in decoded]
        h_min = min(a.shape[0] for a in frames)
        w_min = min(a.shape[1] for a in frames)
        frames = [a[:h_min, :w_min] for a in frames]
        colors = [c[:h_min, :w_min] for c in colors]
        mid = len(frames) // 2
        return _bundle_from_stack(np.stack(frames, axis=0), p.name,
                                    "image_dir", patch_size,
                                    color=colors[mid])

    suffix = p.suffix.lower()
    if suffix in VIDEO_EXTS:
        stack = _decode_video(p, max_frames=max_frames,
                                resize_to=resize_to)
        return _bundle_from_stack(stack, p.name, "video", patch_size)

    if suffix in IMAGE_EXTS:
        scene, color = _decode_image_color(p, resize_to=resize_to)
        return _bundle_from_single(scene, p.name, patch_size, color=color)

    raise ValueError(f"unrecognised visual input: {p} (suffix {suffix!r})")


def bundle_from_pair(path_axis_0: str | Path,
                       path_axis_90: str | Path,
                       resize_to: Optional[int] = 512,
                       patch_size: int = 64,
                       ) -> Tuple[FieldBundle, VisualMeta]:
    """Build a polarization-pair bundle from two image files."""
    p0 = Path(path_axis_0); p90 = Path(path_axis_90)
    a = _decode_image(p0, resize_to=resize_to)
    b = _decode_image(p90, resize_to=resize_to)
    h = min(a.shape[0], b.shape[0]); w = min(a.shape[1], b.shape[1])
    a = a[:h, :w]; b = b[:h, :w]
    bundle = FieldBundle(name=f"{p0.stem}+{p90.stem}")
    bundle.add_value("scene", "image", a, "axis-0 capture as scene")
    bundle.add_value("burst", "image_stack", np.stack([a, b], axis=0),
                      "axis pair as 2-frame stack")
    bundle.add_value("cap_axis_0", "image", a, "axis-0 capture")
    bundle.add_value("cap_axis_90", "image", b, "axis-90 capture")
    bundle.add_value("patch_size", "int", int(patch_size), "ROI size")
    return bundle, VisualMeta(source=str(p0) + "|" + str(p90),
                                 kind="image_pair", n_frames=2,
                                 resolution=(h, w))


def _bundle_from_single(scene: np.ndarray, name: str,
                         patch_size: int,
                         color: Optional[np.ndarray] = None
                         ) -> Tuple[FieldBundle, VisualMeta]:
    bundle = FieldBundle(name=name)
    bundle.add_value("scene", "image", scene, "single image as scene (luma)")
    bundle.add_value("burst", "image_stack",
                      np.stack([scene, scene], axis=0),
                      "single image broadcast to 2-frame stack")
    if color is not None:
        bundle.add_value("color_scene", "color_image", color,
                          "single image as color_scene (RGB)")
    bundle.add_value("patch_size", "int", int(patch_size), "ROI size")
    return bundle, VisualMeta(source=name, kind="image", n_frames=1,
                                 resolution=scene.shape)


def _bundle_from_stack(stack: np.ndarray, name: str, kind: str,
                         patch_size: int,
                         color: Optional[np.ndarray] = None
                         ) -> Tuple[FieldBundle, VisualMeta]:
    bundle = FieldBundle(name=name)
    scene = stack[stack.shape[0] // 2]
    bundle.add_value("scene", "image", scene, "middle frame (luma)")
    bundle.add_value("burst", "image_stack", stack, "decoded stack")
    if color is not None:
        bundle.add_value("color_scene", "color_image", color,
                          "middle-frame color")
    bundle.add_value("patch_size", "int", int(patch_size), "ROI size")
    return bundle, VisualMeta(source=name, kind=kind,
                                 n_frames=int(stack.shape[0]),
                                 resolution=tuple(scene.shape))
