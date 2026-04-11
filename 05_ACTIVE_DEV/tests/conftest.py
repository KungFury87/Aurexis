"""
Aurexis Core — pytest configuration and shared fixtures.

Provides:
  - Automatic sys.path setup for aurexis_lang imports
  - Synthetic test frames (numpy arrays simulating camera output)
  - Mock EXIF data for Samsung S23 lenses
  - Temp directory fixture for output files
  - Pipeline helper that runs a single frame through the full chain

Evidence tier for ALL test fixtures: AUTHORED.
These are synthetic test assets, never real camera captures.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

import cv2
import numpy as np
import pytest

# ── Path setup ──────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'aurexis_lang' / 'src'
for p in (str(ROOT), str(SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)


# ── Synthetic test frames ───────────────────────────────────

@pytest.fixture
def synthetic_frame_simple():
    """A 320x240 BGR frame with colored rectangles — simple scene."""
    img = np.zeros((240, 320, 3), dtype=np.uint8)
    # Red rectangle
    cv2.rectangle(img, (20, 20), (100, 100), (0, 0, 200), -1)
    # Blue rectangle
    cv2.rectangle(img, (150, 50), (280, 180), (200, 0, 0), -1)
    # Green circle
    cv2.circle(img, (160, 200), 30, (0, 200, 0), -1)
    return img


@pytest.fixture
def synthetic_frame_complex():
    """A 640x480 BGR frame with many features — complex scene."""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    # Multiple shapes for higher primitive count
    cv2.rectangle(img, (10, 10), (100, 80), (0, 0, 220), -1)
    cv2.rectangle(img, (120, 10), (250, 80), (220, 0, 0), -1)
    cv2.circle(img, (400, 60), 40, (0, 220, 0), -1)
    cv2.ellipse(img, (550, 60), (60, 30), 0, 0, 360, (0, 220, 220), -1)
    cv2.rectangle(img, (10, 120), (150, 250), (200, 200, 0), -1)
    cv2.rectangle(img, (180, 120), (350, 250), (200, 0, 200), -1)
    cv2.circle(img, (480, 200), 50, (0, 128, 255), -1)
    cv2.rectangle(img, (10, 300), (200, 450), (128, 128, 128), -1)
    cv2.rectangle(img, (250, 300), (450, 450), (255, 128, 0), -1)
    cv2.circle(img, (550, 400), 60, (128, 0, 255), -1)
    # Add some texture lines
    for y in range(0, 480, 40):
        cv2.line(img, (0, y), (640, y), (50, 50, 50), 1)
    return img


@pytest.fixture
def synthetic_frame_blank():
    """A blank black frame — edge case for zero features."""
    return np.zeros((240, 320, 3), dtype=np.uint8)


# ── Mock EXIF data ──────────────────────────────────────────

@pytest.fixture
def samsung_s23_exif_wide():
    """EXIF dict for Samsung S23 Ultra wide_main lens."""
    return {
        'make': 'SAMSUNG',
        'model': 'SM-S918B',
        'datetime_original': '2026:04:07 14:30:00',
        'focal_length': (22, 10),
        'focal_length_35mm': 24,
        'iso': 100,
        'f_number': (18, 10),
        'exposure_time': (1, 120),
        'image_width': 4000,
        'image_height': 3000,
        'lens_model': 'Galaxy S23 Ultra Main',
    }


@pytest.fixture
def samsung_s23_exif_telephoto():
    """EXIF dict for Samsung S23 Ultra telephoto_3x lens."""
    return {
        'make': 'SAMSUNG',
        'model': 'SM-S918B',
        'datetime_original': '2026:04:07 14:31:00',
        'focal_length': (69, 10),
        'focal_length_35mm': 70,
        'iso': 200,
        'f_number': (24, 10),
        'exposure_time': (1, 60),
        'image_width': 4000,
        'image_height': 3000,
        'lens_model': 'Galaxy S23 Ultra Telephoto',
    }


@pytest.fixture
def no_exif():
    """Empty EXIF — e.g., a screenshot or downloaded image."""
    return {}


# ── Temp output directory ───────────────────────────────────

@pytest.fixture
def tmp_output(tmp_path):
    """Temp directory for test outputs (auto-cleaned by pytest)."""
    out = tmp_path / 'test_output'
    out.mkdir()
    return out


# ── Synthetic test image file ───────────────────────────────

@pytest.fixture
def synthetic_image_path(tmp_path, synthetic_frame_complex):
    """Write a synthetic frame to a temp .jpg file and return the path."""
    img_path = tmp_path / 'test_synthetic.jpg'
    cv2.imwrite(str(img_path), synthetic_frame_complex)
    return img_path


@pytest.fixture
def synthetic_image_dir(tmp_path, synthetic_frame_simple, synthetic_frame_complex):
    """Directory with multiple synthetic images for batch testing."""
    img_dir = tmp_path / 'test_images'
    img_dir.mkdir()
    for i in range(5):
        # Alternate between simple and complex frames
        frame = synthetic_frame_simple if i % 2 == 0 else synthetic_frame_complex
        # Add slight variation to each
        varied = frame.copy()
        cv2.putText(varied, f'frame_{i}', (10, 30),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        path = img_dir / f'test_{i:03d}.jpg'
        cv2.imwrite(str(path), varied)
    return img_dir
