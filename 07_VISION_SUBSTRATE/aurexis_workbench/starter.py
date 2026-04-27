"""Starter vocabulary + runtime-task set.

Seed predicates derived directly from the simulator's findings:

  - cardinality (PRIMITIVE_AWARE_HELPS, HOLD)
  - repetition  (PRIMITIVE_AWARE_HELPS, HOLD; strip-aware metric)
  - symmetry    (PRIMITIVE_AWARE_HELPS, HOLD; pixel-mirror only)
  - orientation (ARBITRATION_INVARIANT, HOLD)

ordering is NOT included (REJECT in the simulator).
adjacency / hierarchy are NOT included (PROPOSAL_QUALITY_LIMIT).

The starter vocabulary is intentionally narrow: it is a *substrate
pilot*, not a final language. The Independence Ratio it produces
is the empirical baseline.
"""
from __future__ import annotations

from typing import List

from . import predicates as P
from . import vocabulary as V
from . import independence as I


def _pred_count_eq(n: int) -> P.Predicate:
    return P.Predicate(
        name="count_eq_" + str(n),
        body=P.call("eq_int",
                     P.call("count_components",
                              P.call("threshold",
                                       P.field_("image"),
                                       P.const(1.5, "scalar"))),
                     P.const(int(n), "int")),
        expects={"image": "image"},
        intent="count_eq_" + str(n),
        return_type="bool",
        source="simulator: cardinality PRIMITIVE_AWARE_HELPS / HOLD",
    )


def _pred_repetition_period_within(p: int, tol: int = 2) -> P.Predicate:
    return P.Predicate(
        name="period_within_" + str(p) + "_tol" + str(tol),
        body=P.call("within_int",
                     P.call("autocorr_period",
                              P.field_("image"),
                              P.field_("row_y"),
                              P.field_("target_period")),
                     P.const(int(p), "int"),
                     P.const(int(tol), "int")),
        expects={"image": "image", "row_y": "int",
                  "target_period": "scalar"},
        intent="period_within_" + str(p),
        return_type="bool",
        source="simulator: repetition PRIMITIVE_AWARE_HELPS / "
                "WEAK_ROBUST (strip-aware metric needed)",
    )


def _pred_symmetry_axis_is(axis_label: str) -> P.Predicate:
    other = "horizontal" if axis_label == "vertical" else "vertical"
    label_field = (axis_label + "_label")
    other_field = (other + "_label")
    return P.Predicate(
        name="symmetry_axis_is_" + axis_label,
        body=P.call("gt",
                     P.call("mirror_correlation",
                              P.field_("image"),
                              P.field_(label_field)),
                     P.call("mirror_correlation",
                              P.field_("image"),
                              P.field_(other_field))),
        expects={"image": "image",
                  label_field: "label",
                  other_field: "label"},
        intent="symmetry_axis_is_" + axis_label,
        return_type="bool",
        source="simulator: symmetry PRIMITIVE_AWARE_HELPS / HOLD "
                "(pixel-mirror only)",
    )


def _pred_orientation_within(angle_deg: float,
                                tol_deg: float = 20.0) -> P.Predicate:
    return P.Predicate(
        name="orientation_within_" + str(int(angle_deg)),
        body=P.call("within",
                     P.call("structure_tensor_angle",
                              P.field_("image")),
                     P.field_("target_angle"),
                     P.const(float(tol_deg), "scalar")),
        expects={"image": "image", "target_angle": "scalar"},
        intent="orientation_within_" + str(int(angle_deg)),
        return_type="bool",
        source="simulator: orientation ARBITRATION_INVARIANT / HOLD",
    )


def build_starter_vocabulary() -> V.Vocabulary:
    v = V.Vocabulary(name="starter-v2.0")
    # cardinality predicates for n in {2, 4, 6}
    for n in (2, 4, 6):
        v.add(_pred_count_eq(n))
    # repetition predicates for periods {16, 24}
    for p in (16, 24):
        v.add(_pred_repetition_period_within(p))
    # symmetry predicates for axes
    v.add(_pred_symmetry_axis_is("vertical"))
    v.add(_pred_symmetry_axis_is("horizontal"))
    # orientation predicates for angles {0, 45}
    v.add(_pred_orientation_within(0.0))
    v.add(_pred_orientation_within(45.0))
    return v


def build_runtime_tasks() -> List[I.RuntimeTask]:
    """Runtime tasks the workbench is expected to answer.

    The set is deliberately broader than the starter vocabulary so
    the IR is not 1.0 by construction. Some tasks are deliberately
    UNCOVERED to demonstrate what the substrate cannot yet do.
    """
    T = I.RuntimeTask
    tasks: List[I.RuntimeTask] = []

    # Cardinality: covered for n in {2, 4, 6}
    tasks += [
        T("blobs_n2", "count_eq_2", True, "n=2 scenario, vocab has count_eq_2"),
        T("blobs_n4", "count_eq_4", True, "n=4 scenario, vocab has count_eq_4"),
        T("blobs_n6", "count_eq_6", True, "n=6 scenario, vocab has count_eq_6"),
        T("blobs_n4", "count_eq_2", False,  # truthful "no, n!=2"
          "negative — n=4 should not satisfy count_eq_2"),
        # NOT covered: count_eq_8 / count_eq_3 / count_lt_5
        T("blobs_n4", "count_eq_8", False,
          "uncovered — vocab does not declare count_eq_8"),
        T("blobs_n6", "count_lt_5", False,
          "uncovered — vocab does not declare count_lt_5"),
    ]

    # Repetition
    tasks += [
        T("repetition_p16", "period_within_16", True,
          "p=16 scenario, vocab has period_within_16"),
        T("repetition_p24", "period_within_24", True,
          "p=24 scenario, vocab has period_within_24"),
        T("repetition_p16", "period_within_8", False,
          "uncovered — vocab does not declare period_within_8"),
    ]

    # Symmetry
    tasks += [
        T("symmetry_v", "symmetry_axis_is_vertical", True, ""),
        T("symmetry_h", "symmetry_axis_is_horizontal", True, ""),
        # negatives
        T("symmetry_v", "symmetry_axis_is_horizontal", False,
          "negative — v scenario should not pass horizontal predicate"),
    ]

    # Orientation
    tasks += [
        T("orientation_0",  "orientation_within_0",  True, ""),
        T("orientation_45", "orientation_within_45", True, ""),
        T("orientation_0",  "orientation_within_90", False,
          "uncovered — vocab does not declare orientation_within_90"),
    ]

    # Goals deliberately blocked by simulator findings (not authored)
    tasks += [
        T("blobs_n4",   "ordering_is_ascending", False,
          "uncovered by design — ordering REJECT in simulator"),
        T("blobs_n4",   "adjacency_pairs_eq_2",  False,
          "uncovered — adjacency PROPOSAL_QUALITY_LIMIT"),
        T("blobs_n4",   "hierarchy_groups_eq_2", False,
          "uncovered — hierarchy PROPOSAL_QUALITY_LIMIT"),
    ]

    return tasks
