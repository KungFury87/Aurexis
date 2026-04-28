"""Vision Language Narrator.

Takes any visual input through the full vocabulary, then composes a
human-readable description from the verdict pattern. The narrator is
PURE rule-based composition over predicate verdicts - no ML, no
templates trained on captions. It simply enumerates which predicates
fired and assembles them into sentences.

This is the user-facing artifact of the language: instead of seeing
'has_centered_subject: True', you see 'A centered subject sits on a
clean background, painted with warm colors.'
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Tuple

from . import dsl, vision_ops, predicates as P, runtime as RT
from .visual_intake import bundle_from_path
from .vision_bridge import find_sessions, load_session_bundle


VOCAB_PATH = (Path(__file__).resolve().parent.parent
                / "data" / "vision" / "vocab.aurex")


def evaluate_all(bundle) -> Dict[str, bool]:
    """Run every predicate against the bundle, return name -> verdict
    dict (only non-error verdicts)."""
    vision_ops.register_all()
    parsed = dsl.parse_source(VOCAB_PATH.read_text())
    rt = RT.Runtime()
    for pp in parsed:
        if pp.ok:
            try:
                P.type_check(pp.pred)
                rt.install(pp.pred)
            except Exception:
                pass
    verdicts = {}
    for pp in parsed:
        if not pp.ok:
            continue
        rec = rt.evaluate(pp.pred.name, bundle)
        if rec.error is None:
            verdicts[pp.pred.name] = bool(rec.value)
    return verdicts


def _join_or(items: List[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _join_and(items: List[str]) -> str:
    return _join_or(items)


def _color_phrase(v: Dict[str, bool]) -> str:
    """Compose the color description sentence."""
    if v.get("has_monochrome", False):
        return "The scene is essentially greyscale."
    if v.get("has_largely_achromatic_scene", False):
        return "The scene is largely achromatic, with little saturated color."

    hue_buckets = []
    for h in ["red", "orange", "yellow", "green", "cyan", "blue", "violet", "magenta"]:
        if v.get(f"has_significant_{h}_hue", False):
            hue_buckets.append(h)

    palette = []
    if v.get("has_warm_palette", False):
        palette.append("warm")
    if v.get("has_cool_palette", False):
        palette.append("cool")
    if v.get("has_high_saturation", False):
        palette.append("highly saturated")
    if v.get("has_low_saturation", False) and not v.get("has_monochrome", False):
        palette.append("desaturated")

    parts = []
    if hue_buckets:
        parts.append(f"presents {_join_and(hue_buckets)} hues")
    if palette:
        parts.append("with a " + " ".join(palette) + " palette")
    if v.get("has_high_color_diversity", False):
        parts.append("across a varied color range")
    elif v.get("has_low_color_diversity", False):
        parts.append("within a narrow color range")

    if not parts:
        return ""
    return "It " + ", ".join(parts) + "."


def _structure_phrase(v: Dict[str, bool]) -> str:
    parts = []
    if v.get("has_face_like_signature", False) and v.get("face_is_dominant_concept", False):
        parts.append("a face-like subject")
    elif v.get("has_text_like_signature", False) and v.get("text_is_dominant_concept", False):
        parts.append("text-like content")
    elif v.get("has_screen_like_signature", False):
        parts.append("a screen-like surface")
    elif v.get("has_horizon_line_signature", False):
        parts.append("a horizon line")

    shapes = []
    if v.get("has_circular_signature", False):
        shapes.append("isotropic / round structure")
    if v.get("has_rectilinear_signature", False):
        shapes.append("rectilinear structure")
    if v.get("has_diagonal_signature", False):
        shapes.append("diagonal structure")
    if v.get("has_many_small_blobs", False):
        shapes.append("many small contrast regions")
    elif v.get("has_few_large_blobs", False):
        shapes.append("a few large contrast regions")

    if shapes:
        parts.append(_join_and(shapes))

    if v.get("has_repetitive_horizontal_structure", False):
        parts.append("horizontal repetition")
    if v.get("has_high_edge_density", False):
        parts.append("dense edge content")
    elif v.get("has_low_edge_density", False):
        parts.append("sparse edges")

    if not parts:
        return ""
    return "Its structure shows " + _join_and(parts) + "."


def _composition_phrase(v: Dict[str, bool]) -> str:
    parts = []
    if v.get("has_centered_subject", False):
        parts.append("a centered subject")

    thirds = []
    for label, position in [("top_left", "upper-left third"),
                              ("top_right", "upper-right third"),
                              ("bottom_left", "lower-left third"),
                              ("bottom_right", "lower-right third")]:
        if v.get(f"has_subject_at_thirds_{label}", False):
            thirds.append(position)
    if thirds:
        parts.append("subject content at the " + _join_or(thirds))

    if v.get("has_significant_negative_space", False):
        parts.append("significant negative space")

    horizon = []
    if v.get("has_horizon_at_top_third", False):
        horizon.append("a low horizon (sky-dominant view)")
    elif v.get("has_horizon_at_bottom_third", False):
        horizon.append("a high horizon (ground-dominant view)")
    elif v.get("has_horizon_at_middle", False):
        horizon.append("a centered horizon")

    if horizon:
        parts.extend(horizon)

    balance = []
    if v.get("has_horizontal_balance", False) and v.get("has_vertical_balance", False):
        balance.append("balanced left-right and top-bottom")
    elif v.get("has_horizontal_imbalance", False):
        balance.append("imbalanced top-vs-bottom")
    elif v.get("has_vertical_imbalance", False):
        balance.append("imbalanced left-vs-right")

    if balance:
        parts.append(_join_and(balance))

    if not parts:
        return ""
    return "Compositionally, it has " + _join_and(parts) + "."


def _depth_phrase(v: Dict[str, bool]) -> str:
    parts = []
    if v.get("has_atmospheric_haze", False):
        parts.append("atmospheric haze (distant features fade and shift cool)")
    if v.get("has_shallow_depth_of_field", False):
        parts.append("shallow depth of field (subject sharp, surround blurred)")
    if v.get("has_uniform_focus", False):
        parts.append("uniform focus throughout")
    if v.get("has_perspective_convergence", False):
        parts.append("converging perspective lines")
    if v.get("has_high_dynamic_range", False):
        parts.append("high contrast")

    if not parts:
        return ""
    return "Depth and tone: " + _join_and(parts) + "."


def _motion_phrase(v: Dict[str, bool]) -> str:
    if not v.get("has_subframe_motion", False):
        return ""
    if not v.get("has_real_motion_validated", False):
        return ("Frame-to-frame change is present but appears to be "
                "global brightness drift rather than real motion.")

    parts = []
    if v.get("has_coherent_motion", False):
        parts.append("coherent")
    if v.get("has_chaotic_motion", False):
        parts.append("chaotic / camera-shake")
    if v.get("has_fast_motion", False):
        parts.append("fast")

    direction = []
    if v.get("has_motion_rightward", False):
        direction.append("rightward")
    if v.get("has_motion_leftward", False):
        direction.append("leftward")
    if v.get("has_motion_upward", False):
        direction.append("upward")
    if v.get("has_motion_downward", False):
        direction.append("downward")

    sentence = "Motion is "
    if parts:
        sentence += _join_and(parts) + " "
    if direction:
        sentence += "in the " + " and ".join(direction) + " direction"
    sentence += "."
    return sentence


def narrate(bundle) -> str:
    """Run the full vocabulary on a bundle, return a paragraph."""
    v = evaluate_all(bundle)
    sentences = []
    for f in (_color_phrase, _structure_phrase, _composition_phrase,
                _depth_phrase, _motion_phrase):
        s = f(v)
        if s:
            sentences.append(s)
    if not sentences:
        return "(no predicates fired with confidence)"
    return " ".join(sentences)


def narrate_path(path: str | Path) -> str:
    """Convenience: load a path, narrate it."""
    p = Path(path)
    if str(p).endswith(".aurex-session.zip"):
        bundle, _ = load_session_bundle(p)
    else:
        bundle, _ = bundle_from_path(p)
    if "row_y" not in bundle.fields:
        bundle.add_value("row_y", "int", 128, "default row")
    return narrate(bundle)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        print("usage: python -m aurexis_workbench.narrator <PATH>")
        return 1
    print(narrate_path(argv[0]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
