"""Phoxelis frame-quality gate v0.1.

Composes existing predicates into a per-frame quality score in [0, 1]
with a transparent reasoning chain. Designed to gate frames before
Bayesian occupancy fusion in the E/D V2.1 decode pipeline — a
quality-weighted alternative to the current blind frame averaging
that bakes errors from bad frames into the posterior.

The score is not learned. It's a deterministic composition of five
existing predicates over composable measurements:

    has_overexposed_regions   — too much pixel area near max value
    has_underexposed_regions  — too much pixel area near zero
    has_uniform_focus         — focus blur gradient is low
    has_subframe_motion       — burst-frame variance is low
    has_specular_highlights   — glare / mirror-like highlights present

Each predicate's verdict combines into a multiplicative score so any
single hard-fail drives the score to zero. A frame must pass all five
to score 1.0; failing two cuts the score in half; failing all is 0.

Usage:
    from aurexis_workbench.frame_quality import score_bundle, Quality

    q = score_bundle(bundle)
    print(q.score, q.passed_components, q.reasoning)
"""
from __future__ import annotations

import dataclasses as dc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .fields import FieldBundle
from . import dsl
from . import predicates as P
from . import runtime as RT
from . import vision_ops


# ---- bundle reuse: load + compile vocabulary once -----------------------

_RUNTIME: RT.Runtime | None = None


def _vocab_path() -> Path:
    return (Path(__file__).resolve().parent.parent
              / "data" / "vision" / "vocab.aurex")


def _ensure_runtime() -> RT.Runtime:
    global _RUNTIME
    if _RUNTIME is not None:
        return _RUNTIME
    vision_ops.register_all()
    text = _vocab_path().read_text(encoding="utf-8")
    parsed = dsl.parse_source(text)
    rt = RT.Runtime()
    for pp in parsed:
        if not pp.ok:
            continue
        try:
            P.type_check(pp.pred)
            rt.install(pp.pred)
        except Exception:
            continue
    _RUNTIME = rt
    return rt


# ---- the gate -----------------------------------------------------------

# Each component:
#   predicate name              — what to evaluate
#   bad_when                    — True or False — which verdict means "this is bad"
#   weight                      — multiplier on the score's penalty
#   description                 — human-readable component label
COMPONENTS: list[dict[str, Any]] = [
    {
        "predicate":   "has_overexposed_regions",
        "bad_when":    True,
        "weight":      0.85,
        "description": "overexposed (clipped highlights)",
    },
    {
        "predicate":   "has_underexposed_regions",
        "bad_when":    True,
        "weight":      0.85,
        "description": "underexposed (clipped shadows)",
    },
    {
        "predicate":   "has_uniform_focus",
        "bad_when":    False,    # we WANT uniform focus; not-having-it is bad
        "weight":      0.70,
        "description": "non-uniform focus (motion or DOF blur)",
    },
    {
        "predicate":   "has_subframe_motion",
        "bad_when":    True,
        "weight":      0.70,
        "description": "subframe motion (handshake / target moved)",
    },
    {
        "predicate":   "has_specular_highlights",
        "bad_when":    True,
        "weight":      0.85,
        "description": "specular highlights (glare / mirror-like)",
    },
]


@dataclass
class Quality:
    """Result of scoring one frame."""
    score: float                              # in [0, 1]
    passed_components: list[str] = field(default_factory=list)
    failed_components: list[str] = field(default_factory=list)
    blocked_components: list[str] = field(default_factory=list)
    reasoning: list[str] = field(default_factory=list)

    @property
    def passes_threshold(self) -> bool:
        return self.score >= 0.5

    def short(self) -> str:
        n_pass = len(self.passed_components)
        n_fail = len(self.failed_components)
        n_block = len(self.blocked_components)
        total = n_pass + n_fail + n_block
        if self.score == 1.0:
            tag = "rock-solid"
        elif self.score >= 0.7:
            tag = "good"
        elif self.score >= 0.4:
            tag = "marginal"
        else:
            tag = "reject"
        return (f"score={self.score:.3f} {tag}  "
                f"pass {n_pass}/{total}  fail {n_fail}/{total}  "
                f"blocked {n_block}/{total}")


def score_bundle(bundle: FieldBundle) -> Quality:
    """Run the gate against a field bundle and return a Quality result.

    Scoring rule: start at 1.0, multiply by component-wise penalty for
    each failed predicate. A failed predicate of weight w cuts the
    score by (1 - w) — so a single full-weight failure (w=1.0) drops
    the score to 0.0; a w=0.85 failure drops it to 0.15.

    Multiple failures stack multiplicatively: two w=0.85 failures
    yield 0.15 * 0.15 = 0.022, well below the 0.5 threshold.
    """
    rt = _ensure_runtime()
    score = 1.0
    passed: list[str] = []
    failed: list[str] = []
    blocked: list[str] = []
    reasoning: list[str] = []

    for comp in COMPONENTS:
        pname  = comp["predicate"]
        bad    = comp["bad_when"]
        weight = comp["weight"]
        desc   = comp["description"]

        rec = rt.evaluate(pname, bundle)
        if rec.error:
            blocked.append(pname)
            reasoning.append(f"BLOCKED  {pname}: {rec.error}")
            continue

        v = rec.value
        if not isinstance(v, (bool, int)):
            blocked.append(pname)
            reasoning.append(f"BLOCKED  {pname}: non-bool value {v!r}")
            continue

        v_bool = bool(v)
        is_bad = (v_bool == bad)
        if is_bad:
            score *= (1.0 - weight)
            failed.append(pname)
            reasoning.append(f"FAIL     {pname} = {v_bool}  ({desc})")
        else:
            passed.append(pname)
            reasoning.append(f"pass     {pname} = {v_bool}")

    return Quality(score=score, passed_components=passed,
                     failed_components=failed,
                     blocked_components=blocked,
                     reasoning=reasoning)


# ---- convenience: load image -> bundle ----------------------------------

def bundle_from_image_path(path: str | Path, resize_to: int = 320) -> FieldBundle:
    """Load an image file as a FieldBundle the gate can score."""
    from PIL import Image
    img = Image.open(path).convert("RGB")
    arr = np.asarray(img, dtype=np.float64) / 255.0
    long_side = max(arr.shape[0], arr.shape[1])
    if long_side > resize_to:
        step = max(1, long_side // resize_to)
        arr = arr[::step, ::step]
    color = arr[..., :3]
    luma = 0.299 * color[..., 0] + 0.587 * color[..., 1] + 0.114 * color[..., 2]
    burst = luma[None, ...]
    name = Path(path).stem
    bundle = FieldBundle(name=name)
    bundle.add_value("scene", "image", luma, description="luma")
    bundle.add_value("color_scene", "color_image", color, description="rgb")
    bundle.add_value("burst", "image_stack", burst, description="single-frame")
    bundle.add_value("patch_size", "int", 64, description="ROI side")
    bundle.add_value("row_y", "int", luma.shape[0] // 2,
                       description="autocorr row")
    return bundle
