"""
Aurexis Core — Type System V1 (FROZEN)

Type-checks V1 visual programs to prevent ill-formed compositions.

V1 type rules:
  1. ADJACENT(a, b): both operands must be valid primitives (any kind).
     ADJACENT is kind-agnostic — pure geometry.
  2. CONTAINS(a, b): operand A must have area >= operand B's area.
     A POINT cannot contain a REGION (physical impossibility).
  3. BIND(name, primitive): name must be a non-empty string,
     primitive must be valid. Names must be unique within a frame.
  4. Frame: no duplicate bindings, all primitives valid,
     all operations type-correct.

The type checker runs BEFORE execution. If a program fails type
checking, it should not be executed — the type error is the result.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from enum import Enum

from aurexis_lang.visual_grammar_v1 import (
    PrimitiveKind, OperationKind, BoundingBox, VisualPrimitive,
    GrammarLaw, V1_LAW, GrammarFrame, Relation, Binding,
    ExecutionStatus, GRAMMAR_VERSION,
)
from aurexis_lang.visual_parse_rules_v1 import (
    ProgramNodeKind, ProgramNode,
)


# ════════════════════════════════════════════════════════════
# TYPE SYSTEM VERSION
# ════════════════════════════════════════════════════════════

TYPE_SYSTEM_VERSION = "V1.0"
TYPE_SYSTEM_FROZEN = True


# ════════════════════════════════════════════════════════════
# TYPE ERROR
# ════════════════════════════════════════════════════════════

class TypeErrorKind(str, Enum):
    """Categories of type errors."""
    INVALID_PRIMITIVE = "INVALID_PRIMITIVE"
    CONTAINS_AREA_VIOLATION = "CONTAINS_AREA_VIOLATION"
    DUPLICATE_BINDING = "DUPLICATE_BINDING"
    EMPTY_BINDING_NAME = "EMPTY_BINDING_NAME"
    INVALID_OPERAND_COUNT = "INVALID_OPERAND_COUNT"
    SELF_RELATION = "SELF_RELATION"


@dataclass
class TypeError:
    """One type error found during checking."""
    kind: TypeErrorKind
    message: str
    location: str = ""  # Description of where the error was found
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind.value,
            "message": self.message,
            "location": self.location,
            "details": self.details,
        }


# ════════════════════════════════════════════════════════════
# TYPE CHECK RESULT
# ════════════════════════════════════════════════════════════

class TypeCheckVerdict(str, Enum):
    """Result of type checking."""
    WELL_TYPED = "WELL_TYPED"     # No type errors
    ILL_TYPED = "ILL_TYPED"       # At least one type error
    EMPTY = "EMPTY"               # Nothing to check


@dataclass
class TypeCheckResult:
    """Complete result of type checking a program."""
    verdict: TypeCheckVerdict = TypeCheckVerdict.EMPTY
    errors: List[TypeError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    primitives_checked: int = 0
    operations_checked: int = 0
    bindings_checked: int = 0
    type_system_version: str = TYPE_SYSTEM_VERSION
    grammar_version: str = GRAMMAR_VERSION

    @property
    def is_well_typed(self) -> bool:
        return self.verdict == TypeCheckVerdict.WELL_TYPED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "is_well_typed": self.is_well_typed,
            "error_count": len(self.errors),
            "errors": [e.to_dict() for e in self.errors],
            "warnings": self.warnings,
            "primitives_checked": self.primitives_checked,
            "operations_checked": self.operations_checked,
            "bindings_checked": self.bindings_checked,
            "type_system_version": self.type_system_version,
            "grammar_version": self.grammar_version,
        }


# ════════════════════════════════════════════════════════════
# TYPE RULES — frozen
# ════════════════════════════════════════════════════════════

def check_primitive_valid(
    prim: VisualPrimitive,
    index: int,
    law: GrammarLaw = V1_LAW,
) -> Optional[TypeError]:
    """
    Rule: Every primitive must pass V1 validity (area >= 4px², positive dims).
    """
    if not prim.is_valid(law):
        return TypeError(
            kind=TypeErrorKind.INVALID_PRIMITIVE,
            message=f"Primitive {index} fails validity: area={prim.bbox.area}, "
                    f"width={prim.bbox.width}, height={prim.bbox.height}",
            location=f"primitive[{index}]",
            details={
                "area": prim.bbox.area,
                "min_area": law.min_primitive_area_px2,
                "width": prim.bbox.width,
                "height": prim.bbox.height,
            },
        )
    return None


def check_contains_type(
    a: VisualPrimitive,
    b: VisualPrimitive,
    a_index: int,
    b_index: int,
) -> Optional[TypeError]:
    """
    Rule: CONTAINS(a, b) requires a's area >= b's area.
    A smaller primitive cannot contain a larger one.
    """
    if a.bbox.area < b.bbox.area:
        return TypeError(
            kind=TypeErrorKind.CONTAINS_AREA_VIOLATION,
            message=f"CONTAINS({a_index}, {b_index}): operand A "
                    f"(area={a.bbox.area}) is smaller than operand B "
                    f"(area={b.bbox.area}). Smaller cannot contain larger.",
            location=f"CONTAINS(primitive[{a_index}], primitive[{b_index}])",
            details={
                "a_area": a.bbox.area,
                "b_area": b.bbox.area,
                "a_kind": a.kind.name,
                "b_kind": b.kind.name,
            },
        )
    return None


def check_self_relation(
    a_index: int,
    b_index: int,
    operation: OperationKind,
) -> Optional[TypeError]:
    """
    Rule: A primitive cannot be related to itself.
    ADJACENT(x, x) and CONTAINS(x, x) are nonsensical.
    """
    if a_index == b_index:
        return TypeError(
            kind=TypeErrorKind.SELF_RELATION,
            message=f"{operation.name}({a_index}, {b_index}): "
                    f"cannot relate a primitive to itself.",
            location=f"{operation.name}(primitive[{a_index}], primitive[{a_index}])",
        )
    return None


def check_binding_name(name: str) -> Optional[TypeError]:
    """
    Rule: Binding names must be non-empty strings.
    """
    if not name or not name.strip():
        return TypeError(
            kind=TypeErrorKind.EMPTY_BINDING_NAME,
            message="Binding name is empty or whitespace-only.",
            location=f"BIND('{name}', ...)",
        )
    return None


def check_duplicate_bindings(
    bindings: Dict[str, Any],
) -> List[TypeError]:
    """
    Rule: No duplicate binding names within a frame.
    (Dicts enforce this by default, but we check the program tree.)
    """
    # In V1, dict keys are unique by definition, so this is a no-op
    # for GrammarFrame.bindings. However, if someone constructs a
    # ProgramNode tree manually, duplicates could exist.
    return []


# ════════════════════════════════════════════════════════════
# FRAME TYPE CHECKER
# ════════════════════════════════════════════════════════════

def type_check_frame(
    frame: GrammarFrame,
    law: GrammarLaw = V1_LAW,
) -> TypeCheckResult:
    """
    Type-check a GrammarFrame before execution.

    Checks:
    1. All primitives are valid
    2. All CONTAINS operations have correct area ordering
    3. No self-relations
    4. All binding names are non-empty
    """
    result = TypeCheckResult()

    if not frame.primitives and not frame.bindings and not frame.relations:
        result.verdict = TypeCheckVerdict.EMPTY
        return result

    # Check primitives
    for i, prim in enumerate(frame.primitives):
        result.primitives_checked += 1
        err = check_primitive_valid(prim, i, law)
        if err:
            result.errors.append(err)

    # Check relations
    for rel in frame.relations:
        result.operations_checked += 1

        # Find operand indices
        a_idx = _find_primitive_index(frame.primitives, rel.operand_a)
        b_idx = _find_primitive_index(frame.primitives, rel.operand_b)

        # Self-relation check
        if a_idx is not None and b_idx is not None:
            err = check_self_relation(a_idx, b_idx, rel.operation)
            if err:
                result.errors.append(err)

        # CONTAINS area check
        if rel.operation == OperationKind.CONTAINS:
            err = check_contains_type(rel.operand_a, rel.operand_b,
                                       a_idx or 0, b_idx or 0)
            if err:
                result.errors.append(err)

    # Check bindings
    for name, binding in frame.bindings.items():
        result.bindings_checked += 1
        err = check_binding_name(name)
        if err:
            result.errors.append(err)

    # Set verdict
    if result.errors:
        result.verdict = TypeCheckVerdict.ILL_TYPED
    else:
        result.verdict = TypeCheckVerdict.WELL_TYPED

    return result


def _find_primitive_index(
    primitives: List[VisualPrimitive],
    target: VisualPrimitive,
) -> Optional[int]:
    """Find the index of a primitive in the list (by identity)."""
    for i, p in enumerate(primitives):
        if p is target:
            return i
    return None


# ════════════════════════════════════════════════════════════
# PROGRAM TYPE CHECKER
# ════════════════════════════════════════════════════════════

def type_check_program(program: ProgramNode) -> TypeCheckResult:
    """
    Type-check a ProgramNode tree.

    Checks:
    1. Root is PROGRAM
    2. Binding targets are non-empty
    3. CONTAINS expressions have correct area ordering
    4. No structural anomalies
    """
    result = TypeCheckResult()

    if program.kind != ProgramNodeKind.PROGRAM:
        result.errors.append(TypeError(
            kind=TypeErrorKind.INVALID_OPERAND_COUNT,
            message=f"Expected PROGRAM root, got {program.kind.value}",
            location="root",
        ))
        result.verdict = TypeCheckVerdict.ILL_TYPED
        return result

    if not program.children:
        result.verdict = TypeCheckVerdict.EMPTY
        return result

    seen_names: Set[str] = set()

    for child in program.children:
        if child.kind == ProgramNodeKind.BINDING_STMT:
            result.bindings_checked += 1
            target = child.value.get("target", "")

            # Empty name check
            err = check_binding_name(target)
            if err:
                result.errors.append(err)

            # Duplicate name check
            if target in seen_names:
                result.errors.append(TypeError(
                    kind=TypeErrorKind.DUPLICATE_BINDING,
                    message=f"Duplicate binding name '{target}'",
                    location=f"BIND('{target}', ...)",
                ))
            seen_names.add(target)

        elif child.kind == ProgramNodeKind.RELATION_EXPR:
            result.operations_checked += 1
            operation = child.value.get("operation", "")

            # Operand count check
            if len(child.children) != 2:
                result.errors.append(TypeError(
                    kind=TypeErrorKind.INVALID_OPERAND_COUNT,
                    message=f"{operation} requires exactly 2 operands, "
                            f"got {len(child.children)}",
                    location=f"{operation}(...)",
                ))
            elif operation == "CONTAINS":
                # Area check via bbox from child values
                a_bbox = child.children[0].value.get("bbox", {})
                b_bbox = child.children[1].value.get("bbox", {})
                a_area = a_bbox.get("width", 0) * a_bbox.get("height", 0)
                b_area = b_bbox.get("width", 0) * b_bbox.get("height", 0)

                if a_area < b_area:
                    result.errors.append(TypeError(
                        kind=TypeErrorKind.CONTAINS_AREA_VIOLATION,
                        message=f"CONTAINS: operand A (area={a_area}) is smaller "
                                f"than operand B (area={b_area})",
                        location="CONTAINS(...)",
                        details={"a_area": a_area, "b_area": b_area},
                    ))

    if result.errors:
        result.verdict = TypeCheckVerdict.ILL_TYPED
    else:
        result.verdict = TypeCheckVerdict.WELL_TYPED

    return result


# ════════════════════════════════════════════════════════════
# COMBINED: type check + execute (safe execution)
# ════════════════════════════════════════════════════════════

def safe_execute_image_as_program(
    raw_primitives: List[Dict[str, Any]],
    bindings: Optional[Dict[str, int]] = None,
    operations: Optional[List[Dict]] = None,
    frame_index: int = 0,
) -> Dict[str, Any]:
    """
    Type-check FIRST, then execute only if well-typed.

    Returns a dict with both type_check and execution results.
    If ill-typed, execution is skipped.
    """
    from aurexis_lang.visual_parser_v1 import parse_frame
    from aurexis_lang.visual_executor_v1 import execute_frame
    from aurexis_lang.visual_parse_rules_v1 import parse_frame_to_program
    from aurexis_lang.visual_program_executor_v1 import execute_program

    # Parse and build frame
    primitives = parse_frame(raw_primitives)
    binding_map = None
    if bindings:
        binding_map = {
            name: primitives[idx]
            for name, idx in bindings.items()
            if 0 <= idx < len(primitives)
        }

    grammar_frame = execute_frame(
        frame_index, primitives,
        bindings=binding_map, operations=operations,
    )

    # Type check the frame
    frame_tc = type_check_frame(grammar_frame)

    # Parse to program
    program = parse_frame_to_program(grammar_frame)

    # Type check the program
    program_tc = type_check_program(program)

    # Merge errors
    all_errors = frame_tc.errors + program_tc.errors
    is_well_typed = len(all_errors) == 0

    result = {
        "type_check": {
            "is_well_typed": is_well_typed,
            "frame_verdict": frame_tc.verdict.value,
            "program_verdict": program_tc.verdict.value,
            "errors": [e.to_dict() for e in all_errors],
            "primitives_checked": frame_tc.primitives_checked,
            "operations_checked": frame_tc.operations_checked + program_tc.operations_checked,
            "bindings_checked": frame_tc.bindings_checked + program_tc.bindings_checked,
        },
    }

    if is_well_typed:
        execution = execute_program(program)
        result["execution"] = execution.to_dict()
        result["executed"] = True
    else:
        result["execution"] = None
        result["executed"] = False

    return result
