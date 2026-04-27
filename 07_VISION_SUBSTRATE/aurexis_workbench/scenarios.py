"""Scenario builder — produces FieldBundles for the substrate.

A *scenario* is a named situation the substrate has to evaluate
predicates over. v2.0 supports two ways to produce scenarios:

  - Synthetic-internal: hand-build a FieldBundle from numpy. Used
    for unit tests and for sanity scenarios with known truth.
  - Sim-pull: pull a probe from the simulator package, run capture
    chain, derive a small set of measured fields, return as a
    FieldBundle. Used for richer scenarios that exercise the
    substrate against the simulator's evidence.

Sim-pull is best-effort. If the simulator isn't importable from
PYTHONPATH the scenario builder falls back to synthetic-internal
so the substrate is testable in isolation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from .fields import FieldBundle


@dataclass
class ScenarioSpec:
    name: str
    truth: Dict[str, Any]
    builder: Callable[[], FieldBundle]


# =================================================================
# Synthetic-internal scenarios (always available)
# =================================================================

def _bundle_with_blobs(name: str, n: int) -> FieldBundle:
    rng = np.random.default_rng(0)
    img = np.full((96, 96), 0.10, dtype=np.float32)
    yy, xx = np.mgrid[0:96, 0:96]
    placements = [(20, 20), (20, 75), (75, 20), (75, 75),
                    (48, 48), (10, 50), (85, 50), (50, 10)]
    for i, (cy, cx) in enumerate(placements[:n]):
        m = (yy - cy) ** 2 + (xx - cx) ** 2 <= 36
        img[m] = 0.85
    img += rng.normal(0.0, 0.005, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)
    b = FieldBundle(name=name)
    b.add_value("image", "image", img,
                 description="captured luminance map (synthetic)")
    b.meta["truth"] = {"count": n}
    return b


def _bundle_repetition(name: str, period: int, row_y: int) -> FieldBundle:
    img = np.full((96, 96), 0.10, dtype=np.float32)
    img[row_y - 4:row_y + 4, :] = 0.30
    for x in range(0, 96, period):
        img[row_y - 4:row_y + 4, x:x + max(2, period // 4)] = 0.95
    b = FieldBundle(name=name)
    b.add_value("image", "image", img,
                 description="repetition strip (synthetic)")
    b.add_value("row_y", "int", int(row_y),
                 description="row index for autocorrelation")
    b.add_value("target_period", "scalar", float(period),
                 description="declared truth period in pixels")
    b.meta["truth"] = {"period": int(period), "row_y": int(row_y)}
    return b


def _bundle_symmetry(name: str, axis: str) -> FieldBundle:
    img = np.full((96, 96), 0.15, dtype=np.float32)
    yy, xx = np.mgrid[0:96, 0:96]
    pts = [(20, 18, 0.85), (50, 12, 0.65), (70, 25, 0.50),
            (35, 8, 0.40)]
    for (cy, cx, v) in pts:
        m = (yy - cy) ** 2 + (xx - cx) ** 2 <= 16
        img[m] = v
    if axis == "vertical":
        img[:, 48:] = img[:, 47::-1][:, :48]
    else:
        img[48:, :] = img[47::-1, :][:48, :]
    b = FieldBundle(name=name)
    b.add_value("image", "image", img,
                 description="symmetric pattern (synthetic)")
    b.add_value("vertical_label", "label", "vertical")
    b.add_value("horizontal_label", "label", "horizontal")
    b.meta["truth"] = {"axis": axis}
    return b


def _bundle_orientation(name: str, angle_deg: float) -> FieldBundle:
    img = np.full((96, 96), 0.10, dtype=np.float32)
    yy, xx = np.mgrid[0:96, 0:96].astype(np.float32)
    rad = np.deg2rad(float(angle_deg))
    ux, uy = float(np.cos(rad)), float(np.sin(rad))
    vx, vy = -uy, ux
    cy, cx = 48, 48
    dx = xx - cx; dy = yy - cy
    pu = dx * ux + dy * uy
    pv = dx * vx + dy * vy
    mask = (np.abs(pu) <= 24) & (np.abs(pv) <= 2)
    img[mask] = 0.85
    b = FieldBundle(name=name)
    b.add_value("image", "image", img,
                 description="oriented stroke (synthetic)")
    b.add_value("target_angle", "scalar", float(angle_deg),
                 description="declared truth angle (degrees)")
    b.meta["truth"] = {"angle_deg": float(angle_deg)}
    return b


SYNTHETIC_SCENARIOS: List[ScenarioSpec] = [
    ScenarioSpec("blobs_n2",  {"count": 2},
                  lambda: _bundle_with_blobs("blobs_n2", 2)),
    ScenarioSpec("blobs_n4",  {"count": 4},
                  lambda: _bundle_with_blobs("blobs_n4", 4)),
    ScenarioSpec("blobs_n6",  {"count": 6},
                  lambda: _bundle_with_blobs("blobs_n6", 6)),
    ScenarioSpec("repetition_p16",
                  {"period": 16, "row_y": 48},
                  lambda: _bundle_repetition("repetition_p16", 16, 48)),
    ScenarioSpec("repetition_p24",
                  {"period": 24, "row_y": 48},
                  lambda: _bundle_repetition("repetition_p24", 24, 48)),
    ScenarioSpec("symmetry_v",  {"axis": "vertical"},
                  lambda: _bundle_symmetry("symmetry_v", "vertical")),
    ScenarioSpec("symmetry_h",  {"axis": "horizontal"},
                  lambda: _bundle_symmetry("symmetry_h", "horizontal")),
    ScenarioSpec("orientation_45", {"angle_deg": 45.0},
                  lambda: _bundle_orientation("orientation_45", 45.0)),
    ScenarioSpec("orientation_0",  {"angle_deg": 0.0},
                  lambda: _bundle_orientation("orientation_0", 0.0)),
]


def build_all() -> List[FieldBundle]:
    return [s.builder() for s in SYNTHETIC_SCENARIOS]


def by_name(name: str) -> Optional[FieldBundle]:
    for s in SYNTHETIC_SCENARIOS:
        if s.name == name:
            return s.builder()
    return None
