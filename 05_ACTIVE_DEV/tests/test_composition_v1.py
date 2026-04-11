"""Aurexis Core — Composition V1 Test Suite (pytest format)
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved."""
import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "aurexis_lang", "src"))
from aurexis_lang.visual_grammar_v1 import *
from aurexis_lang.visual_executor_v1 import execute_frame
from aurexis_lang.visual_parse_rules_v1 import parse_frame_to_program, ProgramNodeKind, ProgramNode
from aurexis_lang.visual_program_executor_v1 import execute_program, ProgramVerdict
from aurexis_lang.type_system_v1 import type_check_program, TypeCheckVerdict
from aurexis_lang.composition_v1 import *

def _p(k, x, y, w, h, c=1.0): return VisualPrimitive(k, BoundingBox(x,y,w,h), c)

def _make_module(name, prims, bindings=None, ops=None):
    bmap = {n: prims[i] for n, i in bindings.items()} if bindings else None
    frame = execute_frame(0, prims, bindings=bmap, operations=ops)
    prog = parse_frame_to_program(frame)
    return ProgramModule(name=name, program=prog)

class TestSpec:
    def test_version(self): assert COMPOSITION_VERSION == "V1.0"
    def test_frozen(self): assert COMPOSITION_FROZEN is True

class TestProgramModule:
    def test_well_typed(self):
        m = _make_module("m", [_p(PrimitiveKind.REGION,0,0,100,100), _p(PrimitiveKind.REGION,100,0,100,100)],
            bindings={"a":0,"b":1}, ops=[{"op":OperationKind.ADJACENT,"a_index":0,"b_index":1}])
        assert m.is_well_typed
        assert "a" in m.exports and "b" in m.exports

    def test_ill_typed(self):
        m = _make_module("m", [_p(PrimitiveKind.POINT,50,50,5,5), _p(PrimitiveKind.REGION,0,0,200,200)],
            ops=[{"op":OperationKind.CONTAINS,"a_index":0,"b_index":1}])
        assert not m.is_well_typed

    def test_to_dict(self):
        m = _make_module("m", [_p(PrimitiveKind.REGION,0,0,100,100)], bindings={"x":0})
        d = m.to_dict()
        assert d["name"] == "m"
        assert d["is_well_typed"] is True

class TestComposeSuccess:
    def test_shared_bindings(self):
        a = _make_module("a", [_p(PrimitiveKind.REGION,0,0,100,100), _p(PrimitiveKind.REGION,100,0,100,100)],
            bindings={"left":0,"center":1}, ops=[{"op":OperationKind.ADJACENT,"a_index":0,"b_index":1}])
        b = _make_module("b", [_p(PrimitiveKind.REGION,100,0,100,100), _p(PrimitiveKind.REGION,200,0,100,100)],
            bindings={"center":0,"right":1}, ops=[{"op":OperationKind.ADJACENT,"a_index":0,"b_index":1}])
        cr = compose(a, b)
        assert cr.verdict == CompositionVerdict.SUCCESS
        assert "center" in cr.shared_bindings

    def test_no_shared_ok(self):
        a = _make_module("a", [_p(PrimitiveKind.REGION,0,0,100,100)], bindings={"alpha":0})
        b = _make_module("b", [_p(PrimitiveKind.REGION,200,0,100,100)], bindings={"beta":0})
        cr = compose(a, b, require_shared=False)
        assert cr.verdict == CompositionVerdict.SUCCESS

class TestComposeFail:
    def test_require_shared(self):
        a = _make_module("a", [_p(PrimitiveKind.REGION,0,0,100,100)], bindings={"alpha":0})
        b = _make_module("b", [_p(PrimitiveKind.REGION,200,0,100,100)], bindings={"beta":0})
        cr = compose(a, b, require_shared=True)
        assert cr.verdict == CompositionVerdict.FAILED
        assert any(e.kind == CompositionErrorKind.NO_SHARED_BINDINGS for e in cr.errors)

    def test_ill_typed_module(self):
        ill = _make_module("ill", [_p(PrimitiveKind.POINT,50,50,5,5), _p(PrimitiveKind.REGION,0,0,200,200)],
            ops=[{"op":OperationKind.CONTAINS,"a_index":0,"b_index":1}])
        ok = _make_module("ok", [_p(PrimitiveKind.REGION,0,0,100,100)], bindings={"x":0})
        cr = compose(ill, ok)
        assert cr.verdict == CompositionVerdict.FAILED
        assert any(e.kind == CompositionErrorKind.ILL_TYPED_MODULE for e in cr.errors)

    def test_kind_mismatch(self):
        a = _make_module("a", [_p(PrimitiveKind.REGION,0,0,100,100)], bindings={"shared":0})
        b = _make_module("b", [_p(PrimitiveKind.EDGE,0,0,200,5)], bindings={"shared":0})
        cr = compose(a, b)
        assert cr.verdict == CompositionVerdict.FAILED
        assert any(e.kind == CompositionErrorKind.BINDING_KIND_MISMATCH for e in cr.errors)

class TestProgramLibrary:
    def test_register_and_lookup(self):
        lib = ProgramLibrary()
        m = _make_module("m", [_p(PrimitiveKind.REGION,0,0,100,100)], bindings={"x":0})
        assert lib.register(m) is True
        assert lib.register(m) is False
        assert lib.get("m") is m
        assert lib.get("ghost") is None

    def test_compose_by_name(self):
        lib = ProgramLibrary()
        a = _make_module("a", [_p(PrimitiveKind.REGION,0,0,100,100)], bindings={"x":0})
        b = _make_module("b", [_p(PrimitiveKind.REGION,200,0,100,100)], bindings={"y":0})
        lib.register(a); lib.register(b)
        cr = lib.compose_by_name("a", "b")
        assert cr.verdict == CompositionVerdict.SUCCESS
        assert "a+b" in lib.list_modules()

    def test_compose_missing(self):
        lib = ProgramLibrary()
        cr = lib.compose_by_name("a", "b")
        assert cr.verdict == CompositionVerdict.FAILED

class TestDeterminism:
    def test_compose_deterministic(self):
        a = _make_module("a", [_p(PrimitiveKind.REGION,0,0,100,100), _p(PrimitiveKind.REGION,100,0,100,100)],
            bindings={"left":0,"right":1}, ops=[{"op":OperationKind.ADJACENT,"a_index":0,"b_index":1}])
        b = _make_module("b", [_p(PrimitiveKind.REGION,100,0,100,100)], bindings={"right":0})
        results = [compose(a, b).to_dict() for _ in range(5)]
        assert all(r == results[0] for r in results)
