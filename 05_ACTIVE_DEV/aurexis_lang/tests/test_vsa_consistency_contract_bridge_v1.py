"""
Pytest suite for VSA Consistency / Contract Bridge V1 (40th bridge).
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import pytest
from aurexis_lang.vsa_cleanup_profile_bridge_v1 import (
    V1_CLEANUP_PROFILE, FROZEN_TARGETS, FROZEN_SYMBOL_IDS,
)
from aurexis_lang.hypervector_binding_bundling_bridge_v1 import V1_CODEBOOK
from aurexis_lang.vsa_consistency_contract_bridge_v1 import (
    CONSISTENCY_VERSION, CONSISTENCY_FROZEN,
    ConsistencyVerdict, check_consistency, check_all_consistency,
    make_mismatch_query, make_random_noise_query,
    EXPECTED_CONSISTENT_COUNT,
)

class TestModuleVersion:
    def test_version(self): assert CONSISTENCY_VERSION == "V1.0"
    def test_frozen(self): assert CONSISTENCY_FROZEN is True

class TestCleanConsistency:
    @pytest.mark.parametrize("target", FROZEN_TARGETS)
    def test_consistent(self, target):
        vec = V1_CODEBOOK.get_vector(target.symbol_id)
        r = check_consistency(target.substrate_name, vec)
        assert r.consistency_verdict == ConsistencyVerdict.CONSISTENT

class TestBatchConsistency:
    def test_all_clean(self):
        results = check_all_consistency(noise_fraction=0.0)
        assert all(r.consistency_verdict == ConsistencyVerdict.CONSISTENT for r in results)
    def test_all_10pct(self):
        results = check_all_consistency(noise_fraction=0.1)
        assert all(r.consistency_verdict == ConsistencyVerdict.CONSISTENT for r in results)

class TestMismatch:
    def test_wrong_symbol(self):
        wrong_vec = make_mismatch_query(FROZEN_TARGETS[0].symbol_id, FROZEN_TARGETS[5].symbol_id)
        r = check_consistency(FROZEN_TARGETS[0].substrate_name, wrong_vec)
        assert r.consistency_verdict == ConsistencyVerdict.MISMATCH

class TestVSAFailed:
    def test_random(self):
        r = check_consistency(FROZEN_TARGETS[0].substrate_name, make_random_noise_query())
        assert r.consistency_verdict in (ConsistencyVerdict.VSA_FAILED, ConsistencyVerdict.MISMATCH)

class TestUnknownTarget:
    def test_unknown(self):
        vec = V1_CODEBOOK.get_vector(FROZEN_SYMBOL_IDS[0])
        r = check_consistency("nonexistent", vec)
        assert r.consistency_verdict == ConsistencyVerdict.UNKNOWN_TARGET

class TestSerialization:
    def test_result(self):
        vec = V1_CODEBOOK.get_vector(FROZEN_TARGETS[0].symbol_id)
        r = check_consistency(FROZEN_TARGETS[0].substrate_name, vec)
        d = r.to_dict()
        assert d["consistency_verdict"] == "CONSISTENT"

class TestImmutability:
    def test_frozen(self):
        vec = V1_CODEBOOK.get_vector(FROZEN_TARGETS[0].symbol_id)
        r = check_consistency(FROZEN_TARGETS[0].substrate_name, vec)
        with pytest.raises((AttributeError, TypeError)):
            r.consistency_verdict = ConsistencyVerdict.ERROR
