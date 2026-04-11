"""Aurexis Core — Self-Hosting V1 Test Suite (pytest format)
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved."""
import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "aurexis_lang", "src"))
from aurexis_lang.visual_grammar_v1 import PrimitiveKind, OperationKind, V1_LAW
from aurexis_lang.visual_program_executor_v1 import ProgramVerdict, execute_program
from aurexis_lang.composition_v1 import compose, CompositionVerdict
from aurexis_lang.self_hosting_v1 import *

class TestSpec:
    def test_version(self): assert SELF_HOSTING_VERSION == "V1.0"
    def test_frozen(self): assert SELF_HOSTING_FROZEN is True

class TestPrimitiveMeta:
    @pytest.mark.parametrize("kind", list(PrimitiveKind))
    def test_valid(self, kind):
        mp = build_primitive_meta(kind)
        assert mp.is_valid
        assert mp.describes == kind.name

    @pytest.mark.parametrize("kind", list(PrimitiveKind))
    def test_executes(self, kind):
        mp = build_primitive_meta(kind)
        r = execute_program(mp.module.program)
        assert r.verdict in (ProgramVerdict.PASS, ProgramVerdict.PARTIAL, ProgramVerdict.EMPTY)

class TestOperationMeta:
    @pytest.mark.parametrize("op", list(OperationKind))
    def test_valid(self, op):
        mp = build_operation_meta(op)
        assert mp.is_valid

    @pytest.mark.parametrize("op", list(OperationKind))
    def test_executes(self, op):
        mp = build_operation_meta(op)
        r = execute_program(mp.module.program)
        assert r.verdict in (ProgramVerdict.PASS, ProgramVerdict.PARTIAL, ProgramVerdict.EMPTY)

class TestLawMeta:
    def test_valid(self):
        mp = build_law_meta()
        assert mp.is_valid
    def test_thresholds(self):
        mp = build_law_meta()
        assert mp.properties["adjacent_max_distance_px"] == V1_LAW.adjacent_max_distance_px

class TestSelfHostingProof:
    def test_self_hosted(self):
        proof = prove_self_hosting()
        assert proof.verdict == SelfHostingVerdict.SELF_HOSTED
    def test_all_valid(self):
        proof = prove_self_hosting()
        assert proof.valid_count == proof.total_count == 7
    def test_composition(self):
        proof = prove_self_hosting()
        assert proof.composition_succeeded

class TestRegistry:
    def test_bootstrap(self):
        reg = SelfDescriptionRegistry()
        reg.bootstrap()
        assert reg.is_self_hosted
        assert len(reg.list_descriptions()) == 7

class TestDeterminism:
    def test_deterministic(self):
        results = [prove_self_hosting().to_dict() for _ in range(5)]
        assert all(r == results[0] for r in results)
