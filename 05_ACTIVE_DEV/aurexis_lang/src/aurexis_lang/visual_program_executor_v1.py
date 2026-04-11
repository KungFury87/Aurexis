"""
Aurexis Core — Visual Program Executor V1 (DETERMINISTIC)

Executes a ProgramNode tree produced by V1 parse rules.
This is the proof that a photograph can be treated as source code:

  image → CV extraction → V1 primitives → V1 grammar evaluation →
  V1 parse rules → ProgramNode tree → THIS EXECUTOR → ExecutionResult

The executor walks the program tree and produces:
  1. A binding environment (name → primitive mappings)
  2. A list of evaluated assertions (spatial relationship claims)
  3. An execution trace (ordered log of every step taken)
  4. A final execution verdict (PASS/FAIL/PARTIAL)

V1 execution is assertion-based, not imperative. There are no side effects,
no control flow, no mutation. A V1 program is a set of:
  - Bindings: "this region is called X"
  - Assertions: "X is adjacent to Y" (TRUE or FALSE)

The execution PASSES if all assertions are TRUE.
It FAILS if any assertion is FALSE.
It is PARTIAL if the program had heuristic inputs (tracked but not blocking).

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

from aurexis_lang.visual_grammar_v1 import (
    ExecutionStatus, GRAMMAR_VERSION,
)
from aurexis_lang.visual_parse_rules_v1 import (
    ProgramNodeKind, ProgramNode, PARSE_RULES_VERSION,
)


# ════════════════════════════════════════════════════════════
# EXECUTION RESULT TYPES
# ════════════════════════════════════════════════════════════

EXECUTOR_VERSION = "V1.0"


class ProgramVerdict(str, Enum):
    """Final verdict of program execution."""
    PASS = "PASS"       # All assertions TRUE, all inputs deterministic
    FAIL = "FAIL"       # At least one assertion FALSE
    PARTIAL = "PARTIAL" # All assertions TRUE, but some inputs were heuristic
    EMPTY = "EMPTY"     # No assertions to evaluate


class StepKind(str, Enum):
    """Kind of execution step in the trace."""
    BIND = "BIND"
    ASSERT_TRUE = "ASSERT_TRUE"
    ASSERT_FALSE = "ASSERT_FALSE"
    PROGRAM_START = "PROGRAM_START"
    PROGRAM_END = "PROGRAM_END"


@dataclass
class ExecutionStep:
    """One step in the execution trace."""
    step_index: int
    kind: StepKind
    description: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_index": self.step_index,
            "kind": self.kind.value,
            "description": self.description,
            "details": self.details,
        }


@dataclass
class ExecutionResult:
    """
    Complete result of executing a V1 visual program.
    This is the final proof artifact: a deterministic trace
    from image data to execution verdict.
    """
    verdict: ProgramVerdict = ProgramVerdict.EMPTY
    bindings: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    assertions: List[Dict[str, Any]] = field(default_factory=list)
    trace: List[ExecutionStep] = field(default_factory=list)
    execution_status: ExecutionStatus = ExecutionStatus.DETERMINISTIC
    grammar_version: str = GRAMMAR_VERSION
    parse_rules_version: str = PARSE_RULES_VERSION
    executor_version: str = EXECUTOR_VERSION
    frame_index: int = 0
    total_bindings: int = 0
    total_assertions: int = 0
    true_assertions: int = 0
    false_assertions: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "grammar_version": self.grammar_version,
            "parse_rules_version": self.parse_rules_version,
            "executor_version": self.executor_version,
            "execution_status": self.execution_status.name,
            "frame_index": self.frame_index,
            "total_bindings": self.total_bindings,
            "total_assertions": self.total_assertions,
            "true_assertions": self.true_assertions,
            "false_assertions": self.false_assertions,
            "bindings": self.bindings,
            "assertions": self.assertions,
            "trace": [s.to_dict() for s in self.trace],
        }

    @property
    def is_proof(self) -> bool:
        """
        Is this a valid image-as-program proof?
        Requires: at least one assertion, all TRUE, deterministic inputs.
        """
        return (
            self.verdict == ProgramVerdict.PASS
            and self.total_assertions > 0
            and self.execution_status == ExecutionStatus.DETERMINISTIC
        )


# ════════════════════════════════════════════════════════════
# EXECUTOR — walks the program tree
# ════════════════════════════════════════════════════════════

def execute_program(program: ProgramNode) -> ExecutionResult:
    """
    Execute a V1 visual program (ProgramNode tree).

    Walks the tree depth-first, processing:
    - BINDING_STMT nodes → add to binding environment
    - RELATION_EXPR nodes → record as assertion (TRUE or FALSE)

    Returns an ExecutionResult with complete trace and verdict.
    """
    if program.kind != ProgramNodeKind.PROGRAM:
        raise ValueError(f"Expected PROGRAM root, got {program.kind.value}")

    result = ExecutionResult(
        frame_index=program.value.get("frame_index", 0),
    )

    step_counter = [0]

    def _step(kind: StepKind, description: str, details: Dict[str, Any] = None) -> ExecutionStep:
        s = ExecutionStep(
            step_index=step_counter[0],
            kind=kind,
            description=description,
            details=details or {},
        )
        step_counter[0] += 1
        result.trace.append(s)
        return s

    # Program start
    _step(StepKind.PROGRAM_START, "Begin V1 program execution", {
        "frame_index": result.frame_index,
        "total_children": len(program.children),
        "grammar_version": GRAMMAR_VERSION,
    })

    # Track heuristic status
    has_heuristic = program.execution_status == ExecutionStatus.HEURISTIC_INPUT

    # Process each child node
    for child in program.children:
        if child.kind == ProgramNodeKind.BINDING_STMT:
            _execute_binding(child, result, _step)
        elif child.kind == ProgramNodeKind.RELATION_EXPR:
            _execute_relation(child, result, _step)
            if child.execution_status == ExecutionStatus.HEURISTIC_INPUT:
                has_heuristic = True

    # Set execution status
    result.execution_status = (
        ExecutionStatus.HEURISTIC_INPUT if has_heuristic
        else ExecutionStatus.DETERMINISTIC
    )

    # Compute verdict
    result.verdict = _compute_verdict(result)

    # Program end
    _step(StepKind.PROGRAM_END, f"V1 program execution complete: {result.verdict.value}", {
        "verdict": result.verdict.value,
        "total_bindings": result.total_bindings,
        "total_assertions": result.total_assertions,
        "true_assertions": result.true_assertions,
        "false_assertions": result.false_assertions,
    })

    return result


def _execute_binding(
    node: ProgramNode,
    result: ExecutionResult,
    step_fn,
) -> None:
    """Process a BINDING_STMT node."""
    target = node.value.get("target", "?")
    prim_child = node.children[0] if node.children else None
    prim_kind = prim_child.value.get("primitive_kind", "?") if prim_child else "?"
    bbox = prim_child.value.get("bbox", {}) if prim_child else {}

    result.bindings[target] = {
        "primitive_kind": prim_kind,
        "bbox": bbox,
        "confidence": node.confidence,
        "execution_status": node.execution_status.name,
    }
    result.total_bindings += 1

    step_fn(StepKind.BIND, f"BIND '{target}' → {prim_kind}", {
        "target": target,
        "primitive_kind": prim_kind,
        "bbox": bbox,
        "confidence": node.confidence,
    })


def _execute_relation(
    node: ProgramNode,
    result: ExecutionResult,
    step_fn,
) -> None:
    """Process a RELATION_EXPR node."""
    operation = node.value.get("operation", "?")
    rel_result = node.value.get("result", "?")
    measured = node.value.get("measured_value", 0.0)
    threshold = node.value.get("law_threshold", 0.0)

    assertion = {
        "operation": operation,
        "result": rel_result,
        "measured_value": measured,
        "law_threshold": threshold,
        "confidence": node.confidence,
        "execution_status": node.execution_status.name,
    }

    # Add operand info from children
    if len(node.children) >= 2:
        assertion["operand_a"] = node.children[0].value.get("primitive_kind", "?")
        assertion["operand_b"] = node.children[1].value.get("primitive_kind", "?")

    result.assertions.append(assertion)
    result.total_assertions += 1

    if rel_result == "TRUE":
        result.true_assertions += 1
        step_fn(StepKind.ASSERT_TRUE,
                f"ASSERT {operation} → TRUE (measured={measured}, threshold={threshold})",
                assertion)
    else:
        result.false_assertions += 1
        step_fn(StepKind.ASSERT_FALSE,
                f"ASSERT {operation} → FALSE (measured={measured}, threshold={threshold})",
                assertion)


def _compute_verdict(result: ExecutionResult) -> ProgramVerdict:
    """Compute the final program verdict."""
    if result.total_assertions == 0:
        return ProgramVerdict.EMPTY

    if result.false_assertions > 0:
        return ProgramVerdict.FAIL

    # All assertions TRUE
    if result.execution_status == ExecutionStatus.HEURISTIC_INPUT:
        return ProgramVerdict.PARTIAL

    return ProgramVerdict.PASS


# ════════════════════════════════════════════════════════════
# END-TO-END: Raw CV dicts → execution result
# ════════════════════════════════════════════════════════════

def execute_image_as_program(
    raw_primitives: List[Dict[str, Any]],
    bindings: Optional[Dict[str, int]] = None,
    operations: Optional[List[Dict]] = None,
    frame_index: int = 0,
) -> ExecutionResult:
    """
    Full image-as-program pipeline in one call.

    Takes raw CV extraction dicts (the output of any CV extractor),
    runs them through the V1 grammar, parse rules, and executor.

    Parameters:
        raw_primitives: List of CV extraction dicts (same format as
            EnhancedCVExtractor output).
        bindings: Optional dict mapping names to primitive indices.
            If None, no bindings are created.
        operations: Optional list of operations to evaluate.
            Each: {"op": OperationKind, "a_index": int, "b_index": int}
            If None, evaluates all pairwise ADJACENT and CONTAINS.
        frame_index: Frame sequence number.

    Returns:
        ExecutionResult with complete trace and verdict.
    """
    from aurexis_lang.visual_parser_v1 import parse_frame
    from aurexis_lang.visual_executor_v1 import execute_frame
    from aurexis_lang.visual_parse_rules_v1 import parse_frame_to_program

    # Step 1: Parse raw dicts into typed V1 primitives
    primitives = parse_frame(raw_primitives)

    # Step 2: Build binding map (name → primitive reference)
    binding_map = None
    if bindings:
        binding_map = {}
        for name, idx in bindings.items():
            if 0 <= idx < len(primitives):
                binding_map[name] = primitives[idx]

    # Step 3: Execute grammar (evaluate relations)
    grammar_frame = execute_frame(
        frame_index, primitives,
        bindings=binding_map, operations=operations,
    )

    # Step 4: Parse frame to program tree
    program = parse_frame_to_program(grammar_frame)

    # Step 5: Execute program
    return execute_program(program)
