"""Aurexis Core — Temporal Law V1 Test Suite (pytest format)
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved."""
import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "aurexis_lang", "src"))
from aurexis_lang.visual_grammar_v1 import OperationKind
from aurexis_lang.visual_program_executor_v1 import execute_image_as_program, ProgramVerdict
from aurexis_lang.temporal_law_v1 import (
    V1_TEMPORAL, TEMPORAL_VERSION, TEMPORAL_FROZEN,
    TemporalVerdict, prove_temporal_consistency,
)

def _r(bbox_a, bbox_b, bindings=None):
    return execute_image_as_program(
        [{"type":"region","bbox":list(bbox_a),"confidence":1.0},
         {"type":"region","bbox":list(bbox_b),"confidence":1.0}],
        bindings=bindings,
        operations=[{"op":OperationKind.ADJACENT,"a_index":0,"b_index":1}])

class TestSpec:
    def test_version(self): assert TEMPORAL_VERSION == "V1.0"
    def test_frozen(self): assert TEMPORAL_FROZEN is True
    def test_immutable(self):
        with pytest.raises(AttributeError): V1_TEMPORAL.confirmation_window = 10

class TestVerdicts:
    def test_insufficient(self):
        assert prove_temporal_consistency([]).verdict == TemporalVerdict.INSUFFICIENT
    def test_consistent(self):
        assert prove_temporal_consistency([_r([0,0,100,100],[100,0,100,100])]*2).verdict == TemporalVerdict.CONSISTENT
    def test_confirmed(self):
        assert prove_temporal_consistency([_r([0,0,100,100],[100,0,100,100])]*3).verdict == TemporalVerdict.CONFIRMED
    def test_flipped(self):
        p = prove_temporal_consistency([_r([0,0,100,100],[100,0,100,100]), _r([0,0,100,100],[200,0,100,100])])
        assert p.verdict == TemporalVerdict.FLIPPED
    def test_determinism(self):
        rs = [_r([0,0,100,100],[100,0,100,100])]*3
        dicts = [prove_temporal_consistency(rs).to_dict() for _ in range(5)]
        assert all(d == dicts[0] for d in dicts)
