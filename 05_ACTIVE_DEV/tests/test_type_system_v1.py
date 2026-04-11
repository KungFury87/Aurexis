"""Aurexis Core — Type System V1 Test Suite (pytest format)
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved."""
import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "aurexis_lang", "src"))
from aurexis_lang.visual_grammar_v1 import *
from aurexis_lang.visual_executor_v1 import execute_frame
from aurexis_lang.visual_parse_rules_v1 import parse_frame_to_program
from aurexis_lang.type_system_v1 import *

def _p(k, x, y, w, h, c=1.0): return VisualPrimitive(k, BoundingBox(x,y,w,h), c)

class TestRules:
    def test_valid_prim(self): assert check_primitive_valid(_p(PrimitiveKind.REGION,0,0,10,10), 0) is None
    def test_invalid_prim(self): assert check_primitive_valid(_p(PrimitiveKind.POINT,0,0,1,1), 0) is not None
    def test_contains_ok(self): assert check_contains_type(_p(PrimitiveKind.REGION,0,0,200,200), _p(PrimitiveKind.POINT,50,50,5,5), 0, 1) is None
    def test_contains_fail(self): assert check_contains_type(_p(PrimitiveKind.POINT,50,50,5,5), _p(PrimitiveKind.REGION,0,0,200,200), 0, 1) is not None
    def test_self_relation(self): assert check_self_relation(0, 0, OperationKind.ADJACENT) is not None
    def test_binding_name(self): assert check_binding_name("") is not None

class TestSafeExecute:
    def test_well_typed(self):
        r = safe_execute_image_as_program(
            [{"type":"region","bbox":[0,0,100,100],"confidence":1.0},
             {"type":"region","bbox":[100,0,100,100],"confidence":1.0}],
            operations=[{"op":OperationKind.ADJACENT,"a_index":0,"b_index":1}])
        assert r["executed"] is True
    def test_ill_typed(self):
        r = safe_execute_image_as_program(
            [{"type":"point","bbox":[50,50,5,5],"confidence":1.0},
             {"type":"region","bbox":[0,0,200,200],"confidence":1.0}],
            operations=[{"op":OperationKind.CONTAINS,"a_index":0,"b_index":1}])
        assert r["executed"] is False
