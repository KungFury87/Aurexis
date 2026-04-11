"""
Aurexis Core — Print/Scan Stability V1 Test Suite (pytest format)
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "aurexis_lang", "src"))

from aurexis_lang.visual_grammar_v1 import OperationKind
from aurexis_lang.visual_program_executor_v1 import execute_image_as_program, ProgramVerdict
from aurexis_lang.print_scan_stability_v1 import (
    V1_STABILITY, STABILITY_VERSION, STABILITY_FROZEN,
    degrade_primitive, degrade_frame, analyze_margins,
    prove_stability, StabilityVerdict,
)

class TestSpec:
    def test_version(self): assert STABILITY_VERSION == "V1.0"
    def test_frozen(self): assert STABILITY_FROZEN is True
    def test_immutable(self):
        with pytest.raises(AttributeError): V1_STABILITY.max_jitter_px = 20.0

class TestDegradation:
    def test_deterministic(self):
        d1 = degrade_primitive({"type":"region","bbox":[100,100,50,50],"confidence":0.9}, 5.0, 1.0, 0.1, 42)
        d2 = degrade_primitive({"type":"region","bbox":[100,100,50,50],"confidence":0.9}, 5.0, 1.0, 0.1, 42)
        assert d1 == d2

    def test_frame_deterministic(self):
        f = [{"type":"region","bbox":[0,0,100,100],"confidence":1.0}]
        assert degrade_frame(f, 3.0, 1.0, 0.0, 0) == degrade_frame(f, 3.0, 1.0, 0.0, 0)

class TestMargins:
    def test_touching_headroom(self):
        r = execute_image_as_program(
            [{"type":"region","bbox":[0,0,100,100],"confidence":1.0},
             {"type":"region","bbox":[100,0,100,100],"confidence":1.0}],
            operations=[{"op":OperationKind.ADJACENT,"a_index":0,"b_index":1}])
        m = analyze_margins(r)
        assert abs(m[0].headroom_px - 30.0) < 1e-9

class TestStabilityProof:
    def test_stable(self):
        p = prove_stability(
            [{"type":"region","bbox":[0,0,100,100],"confidence":1.0},
             {"type":"region","bbox":[100,0,100,100],"confidence":1.0}],
            operations=[{"op":OperationKind.ADJACENT,"a_index":0,"b_index":1}])
        assert p.verdict == StabilityVerdict.STABLE

    def test_fail_preserved(self):
        p = prove_stability(
            [{"type":"region","bbox":[0,0,100,100],"confidence":1.0},
             {"type":"region","bbox":[200,0,100,100],"confidence":1.0}],
            operations=[{"op":OperationKind.ADJACENT,"a_index":0,"b_index":1}])
        assert p.original_verdict == ProgramVerdict.FAIL
        assert p.verdict == StabilityVerdict.STABLE

    def test_determinism(self):
        args = dict(raw_primitives=[
            {"type":"region","bbox":[0,0,100,100],"confidence":1.0},
            {"type":"region","bbox":[100,0,100,100],"confidence":1.0}],
            operations=[{"op":OperationKind.ADJACENT,"a_index":0,"b_index":1}])
        dicts = [prove_stability(**args).to_dict() for _ in range(5)]
        assert all(d == dicts[0] for d in dicts)
