"""Aurexis Core — Substrate V1 Test Suite (pytest format)
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved."""
import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "aurexis_lang", "src"))
from aurexis_lang.visual_grammar_v1 import OperationKind
from aurexis_lang.hardware_calibration_v1 import CameraProfile
from aurexis_lang.substrate_v1 import *

class TestSpec:
    def test_version(self): assert SUBSTRATE_VERSION == "V1.0"
    def test_frozen(self): assert SUBSTRATE_FROZEN is True
    def test_all_v1(self): assert all(v == "V1.0" for v in SUBSYSTEM_VERSIONS.values())
    def test_all_frozen(self): assert all(SUBSYSTEM_FROZEN.values())
    def test_subsystem_count(self): assert len(SUBSYSTEM_VERSIONS) == 9

class TestProcessImage:
    def test_basic(self):
        pr = process_image(
            [{"type":"region","bbox":[0,0,100,100],"confidence":1.0},
             {"type":"region","bbox":[100,0,100,100],"confidence":1.0}],
            operations=[{"op":OperationKind.ADJACENT,"a_index":0,"b_index":1}])
        assert pr.type_check_verdict == "WELL_TYPED"
        assert pr.execution_verdict == "PASS"

    def test_calibrated(self):
        pr = process_image(
            [{"type":"region","bbox":[0,0,100,100],"confidence":0.95}],
            camera_profile=CameraProfile(name="t", resolution_megapixels=12.0))
        assert pr.calibrated is True

    def test_ill_typed(self):
        pr = process_image(
            [{"type":"point","bbox":[50,50,5,5],"confidence":1.0},
             {"type":"region","bbox":[0,0,200,200],"confidence":1.0}],
            operations=[{"op":OperationKind.CONTAINS,"a_index":0,"b_index":1}])
        assert pr.type_check_verdict == "ILL_TYPED"
        assert pr.execution_verdict == "SKIPPED"

class TestVerifySubstrate:
    def test_complete(self):
        sp = verify_substrate()
        assert sp.verdict == SubstrateVerdict.COMPLETE
    def test_all_subsystems(self):
        sp = verify_substrate()
        assert sp.subsystems_passed == 9

class TestSubstrateV1:
    def test_verify_and_process(self):
        sub = SubstrateV1()
        sub.verify()
        assert sub.is_complete
        pr = sub.process(
            [{"type":"region","bbox":[0,0,100,100],"confidence":1.0},
             {"type":"region","bbox":[100,0,100,100],"confidence":1.0}],
            operations=[{"op":OperationKind.ADJACENT,"a_index":0,"b_index":1}])
        assert pr.execution_verdict == "PASS"

class TestDeterminism:
    def test_deterministic(self):
        results = [process_image(
            [{"type":"region","bbox":[0,0,100,100],"confidence":1.0},
             {"type":"region","bbox":[100,0,100,100],"confidence":1.0}],
            operations=[{"op":OperationKind.ADJACENT,"a_index":0,"b_index":1}]
        ).to_dict() for _ in range(5)]
        assert all(r == results[0] for r in results)
