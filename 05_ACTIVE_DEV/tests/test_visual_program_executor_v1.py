"""
Aurexis Core — Visual Program Executor V1 Test Suite (pytest format)
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "aurexis_lang", "src"))

from aurexis_lang.visual_grammar_v1 import (
    PrimitiveKind, OperationKind, ExecutionStatus,
    BoundingBox, VisualPrimitive, GrammarFrame,
)
from aurexis_lang.visual_executor_v1 import execute_frame
from aurexis_lang.visual_parse_rules_v1 import ProgramNodeKind, parse_frame_to_program
from aurexis_lang.visual_program_executor_v1 import (
    execute_program, execute_image_as_program,
    ProgramVerdict, StepKind, EXECUTOR_VERSION,
)


def _prim(kind, x, y, w, h, conf=1.0):
    return VisualPrimitive(kind=kind, bbox=BoundingBox(x, y, w, h),
                           source_confidence=conf)


class TestExecutorSpec:
    def test_version(self):
        assert EXECUTOR_VERSION == "V1.0"


class TestVerdicts:
    def test_empty(self):
        frame = GrammarFrame(frame_index=0)
        result = execute_program(parse_frame_to_program(frame))
        assert result.verdict == ProgramVerdict.EMPTY

    def test_pass(self):
        a = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
        b = _prim(PrimitiveKind.REGION, 100, 0, 100, 100)
        frame = execute_frame(0, [a, b],
                              operations=[{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}])
        result = execute_program(parse_frame_to_program(frame))
        assert result.verdict == ProgramVerdict.PASS
        assert result.is_proof is True

    def test_fail(self):
        a = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
        b = _prim(PrimitiveKind.REGION, 200, 0, 100, 100)
        frame = execute_frame(0, [a, b],
                              operations=[{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}])
        result = execute_program(parse_frame_to_program(frame))
        assert result.verdict == ProgramVerdict.FAIL

    def test_partial(self):
        a = _prim(PrimitiveKind.REGION, 0, 0, 100, 100, conf=0.7)
        b = _prim(PrimitiveKind.REGION, 100, 0, 100, 100)
        frame = execute_frame(0, [a, b],
                              operations=[{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}])
        result = execute_program(parse_frame_to_program(frame))
        assert result.verdict == ProgramVerdict.PARTIAL


class TestEndToEnd:
    def test_image_as_program(self):
        raw = [
            {"type": "region", "bbox": [0, 0, 100, 100], "confidence": 1.0},
            {"type": "region", "bbox": [100, 0, 100, 100], "confidence": 1.0},
        ]
        result = execute_image_as_program(
            raw,
            bindings={"a": 0, "b": 1},
            operations=[{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}],
        )
        assert result.verdict == ProgramVerdict.PASS
        assert result.is_proof is True

    def test_determinism(self):
        raw = [
            {"type": "region", "bbox": [0, 0, 100, 100], "confidence": 1.0},
            {"type": "region", "bbox": [100, 0, 100, 100], "confidence": 1.0},
        ]
        dicts = [
            execute_image_as_program(raw, operations=[
                {"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}
            ]).to_dict()
            for _ in range(10)
        ]
        assert all(d == dicts[0] for d in dicts)
