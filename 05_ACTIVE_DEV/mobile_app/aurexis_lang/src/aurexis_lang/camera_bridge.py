"""
Aurexis Core — Camera Bridge
File-based ingestion for real phone photos and videos.

Replaces camera_bridge_stub.py for production use.

Reads JPEG/PNG/DNG images and MP4/MOV video files from disk.
Parses EXIF metadata (Samsung S23 and others) to build canonical phoxel records.
Stamps every frame as REAL_CAPTURE tier evidence.
Feeds into the existing Aurexis visual pipeline.

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations

import json
import math
import struct
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import cv2
import numpy as np

from .evidence_tiers import EvidenceTier, stamp_result
from .phoxel_schema import coerce_phoxel_schema, validate_phoxel_schema
from .visual_tokenizer import PrimitiveObservation, primitives_to_tokens
from .parser_expanded import parse_tokens_expanded
from .ir import ast_to_ir
from .ir_optimizer import optimize as optimize_ir, optimization_report_to_dict

# ─────────────────────────────────────────────
# Supported file extensions
# ─────────────────────────────────────────────

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.dng', '.heic', '.webp', '.tiff', '.tif', '.bmp'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.mkv', '.avi', '.3gp', '.m4v', '.webm'}

# Default frame sampling rate for video (frames per second to extract)
DEFAULT_VIDEO_SAMPLE_FPS = 2.0
# Maximum frames to extract from a single video to avoid memory overload
MAX_VIDEO_FRAMES = 300


# ─────────────────────────────────────────────
# EXIF parsing
# ─────────────────────────────────────────────

# Standard EXIF tag IDs we care about
_EXIF_TAGS = {
    0x010F: 'make',
    0x0110: 'model',
    0x9003: 'datetime_original',
    0x9004: 'datetime_digitized',
    0x0132: 'datetime',
    0x920A: 'focal_length',
    0xA405: 'focal_length_35mm',
    0x8827: 'iso',
    0x829A: 'exposure_time',
    0x829D: 'f_number',
    0xA002: 'image_width',
    0xA003: 'image_height',
    0x0100: 'pixel_x_dimension',
    0x0101: 'pixel_y_dimension',
    0xA210: 'focal_plane_x_res',
    0xA20E: 'focal_plane_y_res',
    0xA301: 'scene_type',
    0xA300: 'file_source',
    0x9209: 'flash',
    0x9208: 'light_source',
    0xA401: 'custom_rendered',
    0xA406: 'scene_capture_type',
    0xA432: 'lens_info',
    0xA433: 'lens_make',
    0xA434: 'lens_model',
    0x0213: 'ycbcr_positioning',
}


def _rational_to_float(rational: Any) -> Optional[float]:
    """Convert EXIF rational (numerator, denominator) tuple to float."""
    try:
        if isinstance(rational, tuple) and len(rational) == 2:
            num, den = rational
            return float(num) / float(den) if den != 0 else None
        return float(rational)
    except (TypeError, ZeroDivisionError, ValueError):
        return None


def _parse_exif_bytes(data: bytes) -> Dict[str, Any]:
    """
    Parse raw EXIF bytes without Pillow dependency.
    Handles both Motorola (big-endian) and Intel (little-endian) byte order.
    Returns a flat dict of tag_name -> value.
    """
    result: Dict[str, Any] = {}

    if len(data) < 8:
        return result

    # Check for EXIF header
    header = data[:6]
    if header not in (b'Exif\x00\x00', b'Exif\x00\xff'):
        # Try starting directly at the TIFF header
        offset = 0
    else:
        offset = 6

    if len(data) < offset + 8:
        return result

    byte_order = data[offset:offset + 2]
    if byte_order == b'II':
        endian = '<'
    elif byte_order == b'MM':
        endian = '>'
    else:
        return result

    try:
        magic = struct.unpack_from(endian + 'H', data, offset + 2)[0]
        if magic != 42:
            return result

        ifd_offset = struct.unpack_from(endian + 'I', data, offset + 4)[0]

        def read_ifd(ifd_off: int, depth: int = 0) -> None:
            if depth > 3 or ifd_off + 2 > len(data):
                return
            count = struct.unpack_from(endian + 'H', data, offset + ifd_off)[0]
            entry_offset = ifd_off + 2
            for _ in range(min(count, 512)):
                if offset + entry_offset + 12 > len(data):
                    break
                tag_id = struct.unpack_from(endian + 'H', data, offset + entry_offset)[0]
                type_id = struct.unpack_from(endian + 'H', data, offset + entry_offset + 2)[0]
                n_values = struct.unpack_from(endian + 'I', data, offset + entry_offset + 4)[0]
                value_offset = struct.unpack_from(endian + 'I', data, offset + entry_offset + 8)[0]

                if tag_id in _EXIF_TAGS:
                    tag_name = _EXIF_TAGS[tag_id]
                    try:
                        val = _read_value(data, offset, endian, type_id, n_values, value_offset)
                        if val is not None:
                            result[tag_name] = val
                    except Exception:
                        pass

                # Follow sub-IFD pointers
                if tag_id in (0x8769, 0x8825) and type_id == 4:
                    sub_offset = struct.unpack_from(endian + 'I', data, offset + entry_offset + 8)[0]
                    read_ifd(sub_offset, depth + 1)

                entry_offset += 12

        read_ifd(ifd_offset)
    except struct.error:
        pass

    return result


def _read_value(data: bytes, base: int, endian: str, type_id: int, count: int, val_offset: int) -> Any:
    """Read a typed EXIF value."""
    type_sizes = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 9: 4, 10: 8}
    type_fmts = {1: 'B', 2: 's', 3: 'H', 4: 'I', 5: 'II', 7: 'B', 9: 'i', 10: 'ii'}

    if type_id not in type_sizes:
        return None

    size = type_sizes[type_id] * count
    if size <= 4:
        buf = data[base + val_offset: base + val_offset + 4]
    else:
        if base + val_offset + size > len(data):
            return None
        buf = data[base + val_offset: base + val_offset + size]

    if type_id == 2:  # ASCII string
        raw = buf[:count]
        return raw.rstrip(b'\x00').decode('ascii', errors='replace').strip()

    if type_id in (5, 10):  # Rational
        if len(buf) < 8:
            return None
        fmt = endian + type_fmts[type_id]
        a, b = struct.unpack_from(fmt, buf)
        return (a, b)

    fmt = endian + str(count) + type_fmts[type_id]
    try:
        vals = struct.unpack_from(fmt, buf)
        return vals[0] if count == 1 else list(vals)
    except struct.error:
        return None


def _extract_exif_from_jpeg(path: Path) -> Dict[str, Any]:
    """Extract raw EXIF data from a JPEG file."""
    try:
        with open(path, 'rb') as f:
            data = f.read()

        # Find APP1 marker (0xFFE1) which contains EXIF
        i = 2  # Skip SOI
        while i < len(data) - 1:
            marker = struct.unpack_from('>H', data, i)[0]
            if marker == 0xFFE1:  # APP1
                segment_len = struct.unpack_from('>H', data, i + 2)[0]
                app1_data = data[i + 4: i + 2 + segment_len]
                return _parse_exif_bytes(app1_data)
            elif marker == 0xFFDA:  # SOS - start of scan, no more metadata
                break
            elif (marker & 0xFF00) == 0xFF00 and marker != 0xFF00:
                segment_len = struct.unpack_from('>H', data, i + 2)[0]
                i += 2 + segment_len
            else:
                i += 1
    except Exception:
        pass
    return {}


def _try_pillow_exif(path: Path) -> Dict[str, Any]:
    """Try to use Pillow for EXIF if available (richer data)."""
    try:
        from PIL import Image
        img = Image.open(path)
        exif_data = img.getexif()
        if not exif_data:
            return {}
        result: Dict[str, Any] = {}
        for tag_id, value in exif_data.items():
            if tag_id in _EXIF_TAGS:
                result[_EXIF_TAGS[tag_id]] = value
        # Also try EXIF IFD
        try:
            exif_ifd = exif_data.get_ifd(0x8769)
            for tag_id, value in exif_ifd.items():
                if tag_id in _EXIF_TAGS:
                    result[_EXIF_TAGS[tag_id]] = value
        except Exception:
            pass
        return result
    except ImportError:
        return {}
    except Exception:
        return {}


def extract_file_exif(path: Path) -> Dict[str, Any]:
    """
    Extract EXIF metadata from an image file.
    Tries Pillow first (richer), falls back to manual JPEG parser.
    Returns empty dict for files with no EXIF (PNG, video, etc).
    """
    suffix = path.suffix.lower()
    if suffix in {'.jpg', '.jpeg'}:
        pillow_result = _try_pillow_exif(path)
        if pillow_result:
            return pillow_result
        return _extract_exif_from_jpeg(path)
    elif suffix in {'.tiff', '.tif', '.dng'}:
        return _try_pillow_exif(path)
    else:
        return _try_pillow_exif(path)


def build_camera_metadata(exif: Dict[str, Any], path: Path, frame_index: int = 0) -> Dict[str, Any]:
    """
    Build the camera_metadata dict expected by phoxel schema from raw EXIF.
    Handles Samsung S23 and generic Android/phone EXIF shapes.
    """
    make = str(exif.get('make', '')).strip()
    model = str(exif.get('model', '')).strip()

    focal_raw = exif.get('focal_length')
    focal_mm = _rational_to_float(focal_raw) if focal_raw else None

    focal_35mm = exif.get('focal_length_35mm')
    if isinstance(focal_35mm, (int, float)):
        focal_35mm = float(focal_35mm)
    else:
        focal_35mm = None

    iso_raw = exif.get('iso')
    iso = int(iso_raw) if iso_raw and str(iso_raw).isdigit() else (
        int(iso_raw[0]) if isinstance(iso_raw, (list, tuple)) else None
    )

    f_number_raw = exif.get('f_number')
    f_number = _rational_to_float(f_number_raw)

    exposure_raw = exif.get('exposure_time')
    exposure = _rational_to_float(exposure_raw)

    width = exif.get('image_width') or exif.get('pixel_x_dimension')
    height = exif.get('image_height') or exif.get('pixel_y_dimension')

    lens_model = str(exif.get('lens_model', '')).strip() or None
    lens_make = str(exif.get('lens_make', '')).strip() or None

    # Samsung S23 series identification
    is_samsung = 'samsung' in make.lower()
    is_s23_series = any(s in model.upper() for s in ('SM-S91', 'SM-S90', 'SM-S93'))

    # Infer which lens based on focal length (Samsung S23 Ultra has 4 cameras)
    lens_id = _infer_samsung_lens(focal_mm, focal_35mm) if is_samsung else 'main'

    # Parse datetime
    dt_str = exif.get('datetime_original') or exif.get('datetime_digitized') or exif.get('datetime')
    image_timestamp: Optional[str] = None
    if dt_str and isinstance(dt_str, str):
        try:
            dt = datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S')
            image_timestamp = dt.isoformat()
        except ValueError:
            image_timestamp = dt_str

    return {
        'make': make or 'unknown',
        'model': model or 'unknown',
        'is_samsung': is_samsung,
        'is_s23_series': is_s23_series,
        'lens_id': lens_id,
        'lens_model': lens_model,
        'lens_make': lens_make,
        'focal_length_mm': focal_mm,
        'focal_length_35mm_equiv': focal_35mm,
        'iso': iso,
        'f_number': f_number,
        'exposure_time_seconds': exposure,
        'image_width': int(width) if width else None,
        'image_height': int(height) if height else None,
        'source_file': path.name,
        'source_path': str(path),
        'frame_index': frame_index,
        'exif_present': bool(exif),
        'measurement_origin': 'camera-observation',
        'image_timestamp': image_timestamp,
    }


def _infer_samsung_lens(focal_mm: Optional[float], focal_35mm: Optional[float]) -> str:
    """
    Infer which Samsung S23 lens based on focal length.
    S23 Ultra: ~2.2mm wide, ~1.0mm ultrawide, ~6.0mm 3x tele, ~10mm periscope
    35mm equiv:  ~24mm,        ~13mm,          ~70mm,          ~230mm
    """
    ref = focal_35mm or (focal_mm * 4.5 if focal_mm else None)
    if ref is None:
        return 'main'
    if ref < 18:
        return 'ultrawide'
    if ref < 35:
        return 'wide_main'
    if ref < 100:
        return 'telephoto_3x'
    return 'periscope_10x'


# ─────────────────────────────────────────────
# Phoxel record construction
# ─────────────────────────────────────────────

def build_phoxel_record(
    camera_metadata: Dict[str, Any],
    frame_index: int,
    source_id: str,
    pixel_coordinates: Tuple[int, int] = (0, 0),
) -> Dict[str, Any]:
    """
    Build a canonical phoxel record from camera metadata.
    Passes phoxel_schema validation.
    Marks synthetic=False and evidence_tier=REAL_CAPTURE.
    """
    image_timestamp = camera_metadata.get('image_timestamp') or datetime.now().isoformat()

    record = {
        'image_anchor': {
            'pixel_coordinates': pixel_coordinates,
        },
        'world_anchor_state': {
            'status': 'unknown',
            'world_coordinates': None,
            'evidence_status': 'image-grounded-only',
        },
        'photonic_signature': {
            'pixel_data_available': True,
            'camera_metadata': camera_metadata,
            'measurement_origin': 'camera-observation',
        },
        'time_slice': {
            'image_timestamp': image_timestamp,
        },
        'relation_set': [],
        'integrity_state': {
            'evidence_chain': [f'{source_id}_frame_{frame_index}'],
            'synthetic': False,
            'traceable': True,
        },
    }

    errors = validate_phoxel_schema(record)
    return {
        'record': record,
        'schema_errors': errors,
        'schema_valid': len(errors) == 0,
        'evidence_tier': EvidenceTier.REAL_CAPTURE.value,
    }


# ─────────────────────────────────────────────
# Frame extraction
# ─────────────────────────────────────────────

def frames_from_image(path: Path) -> Iterator[Tuple[np.ndarray, int, Dict[str, Any]]]:
    """
    Yield (frame_array, frame_index, camera_metadata) for a single image file.
    Always yields exactly one frame.
    """
    frame = cv2.imread(str(path))
    if frame is None:
        return

    exif = extract_file_exif(path)
    camera_meta = build_camera_metadata(exif, path, frame_index=0)
    yield frame, 0, camera_meta


def frames_from_video(
    path: Path,
    sample_fps: float = DEFAULT_VIDEO_SAMPLE_FPS,
    max_frames: int = MAX_VIDEO_FRAMES,
) -> Iterator[Tuple[np.ndarray, int, Dict[str, Any]]]:
    """
    Yield (frame_array, frame_index, camera_metadata) sampled from a video file.
    Samples at sample_fps regardless of the video's native frame rate.
    Stops after max_frames to avoid memory overload.
    """
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return

    native_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Build a synthetic camera_metadata for video (no EXIF on video files usually)
    camera_meta = {
        'make': 'unknown',
        'model': 'unknown',
        'is_samsung': False,
        'is_s23_series': False,
        'lens_id': 'main',
        'lens_model': None,
        'lens_make': None,
        'focal_length_mm': None,
        'focal_length_35mm_equiv': None,
        'iso': None,
        'f_number': None,
        'exposure_time_seconds': None,
        'image_width': width,
        'image_height': height,
        'source_file': path.name,
        'source_path': str(path),
        'native_fps': native_fps,
        'total_frames': total_frames,
        'exif_present': False,
        'measurement_origin': 'camera-observation',
        'image_timestamp': datetime.now().isoformat(),
        'video_source': True,
    }

    # Calculate frame step to achieve desired sample_fps
    step = max(1, int(round(native_fps / sample_fps)))
    frame_index = 0
    extracted = 0

    try:
        while extracted < max_frames:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_index % step == 0:
                meta = dict(camera_meta)
                meta['frame_index'] = frame_index
                meta['image_timestamp'] = datetime.now().isoformat()
                yield frame, extracted, meta
                extracted += 1

            frame_index += 1
    finally:
        cap.release()


def frames_from_file(
    path: Path,
    sample_fps: float = DEFAULT_VIDEO_SAMPLE_FPS,
    max_video_frames: int = MAX_VIDEO_FRAMES,
) -> Iterator[Tuple[np.ndarray, int, Dict[str, Any]]]:
    """
    Route a file to the right extractor based on extension.
    Yields (frame, frame_index, camera_metadata) tuples.
    """
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        yield from frames_from_image(path)
    elif suffix in VIDEO_EXTENSIONS:
        yield from frames_from_video(path, sample_fps=sample_fps, max_frames=max_video_frames)


# ─────────────────────────────────────────────
# Full pipeline: file → IR
# ─────────────────────────────────────────────

def file_to_ir(
    path: Path,
    primitives: List[Dict[str, Any]],
    camera_metadata: Dict[str, Any],
    frame_index: int,
) -> Dict[str, Any]:
    """
    Take extracted primitives (from RobustCVExtractor) + camera metadata
    and run them through the full Aurexis pipeline to IR.

    This is the replacement for camera_input_to_ir() in the stub,
    but enriched with real phoxel records and evidence tier stamping.
    """
    source_id = Path(camera_metadata.get('source_file', 'unknown')).stem

    # Build phoxel record for this frame
    # Use centroid of first primitive as anchor, or image center
    if primitives:
        first_prim = primitives[0]
        centroid = first_prim.get('attributes', {}).get('centroid', (0, 0))
        pixel_coords = tuple(int(c) for c in centroid) if centroid else (0, 0)
    else:
        w = camera_metadata.get('image_width') or 0
        h = camera_metadata.get('image_height') or 0
        pixel_coords = (w // 2, h // 2)

    phoxel = build_phoxel_record(camera_metadata, frame_index, source_id, pixel_coords)

    # Tokenize
    observations = [
        PrimitiveObservation(
            primitive_type=p.get('primitive_type', 'unknown'),
            attributes={k: str(v) for k, v in p.get('attributes', {}).items()},
            confidence=float(p.get('confidence', 0.5)),
        )
        for p in primitives
    ]
    tokens = primitives_to_tokens(observations)
    ast = parse_tokens_expanded(tokens)
    ir_raw = ast_to_ir(ast)

    # Run all 6 optimization passes with phoxel context
    ir_optimized, opt_report = optimize_ir(ir_raw, phoxel_context=phoxel)

    result = {
        'source_file': camera_metadata.get('source_file'),
        'frame_index': frame_index,
        'camera_metadata': camera_metadata,
        'phoxel_record': phoxel,
        'primitive_count': len(primitives),
        'token_count': len(tokens),
        'ast_root': str(ast.node_type),
        'ir_root': ir_optimized.op,
        'ir_optimization': optimization_report_to_dict(opt_report),
        'tokens': [
            {'type': t.token_type, 'value': t.value, 'confidence': t.confidence}
            for t in tokens
        ],
        'schema_valid': phoxel['schema_valid'],
        'schema_errors': phoxel['schema_errors'],
        'evidence_tier': EvidenceTier.REAL_CAPTURE.value,
        'ir_promotion_eligible_count': opt_report.promotion_eligible_count,
        'ir_active_node_count': opt_report.active_node_count,
        'processing_timestamp': datetime.now().isoformat(),
    }

    return stamp_result(
        result,
        EvidenceTier.REAL_CAPTURE,
        source_tiers=[EvidenceTier.REAL_CAPTURE],
        earned_proof=False,
        note='file-based real camera input',
        requires_real_capture=True,
    )
