"""
Pytest suite for Cleanup Retrieval Bridge V1 (39th bridge).
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import pytest
from aurexis_lang.vsa_cleanup_profile_bridge_v1 import FROZEN_SYMBOL_IDS
from aurexis_lang.hypervector_binding_bundling_bridge_v1 import (
    V1_CODEBOOK, generate_atomic, add_noise, bind, unbind,
)
from aurexis_lang.cleanup_retrieval_bridge_v1 import (
    RETRIEVAL_VERSION, RETRIEVAL_FROZEN,
    CleanupVerdict, cleanup_single, cleanup_top_k,
    verify_noise_tolerance, verify_all_noise_tolerance,
    make_random_query, SUPPORTED_NOISE_LEVELS,
)

class TestModuleVersion:
    def test_version(self): assert RETRIEVAL_VERSION == "V1.0"
    def test_frozen(self): assert RETRIEVAL_FROZEN is True

class TestCleanRetrieval:
    @pytest.mark.parametrize("sid", FROZEN_SYMBOL_IDS)
    def test_clean(self, sid):
        r = cleanup_single(V1_CODEBOOK.get_vector(sid))
        assert r.verdict == CleanupVerdict.CLEAN_MATCH
        assert r.matched_symbol_id == sid
        assert r.similarity == 1.0

class TestNoisyRetrieval10:
    @pytest.mark.parametrize("sid", FROZEN_SYMBOL_IDS)
    def test_10pct(self, sid):
        noisy = add_noise(V1_CODEBOOK.get_vector(sid), 0.1, seed=42)
        r = cleanup_single(noisy)
        assert r.matched_symbol_id == sid

class TestNoisyRetrieval20:
    @pytest.mark.parametrize("sid", FROZEN_SYMBOL_IDS)
    def test_20pct(self, sid):
        noisy = add_noise(V1_CODEBOOK.get_vector(sid), 0.2, seed=43)
        r = cleanup_single(noisy)
        assert r.matched_symbol_id == sid

class TestRandomQuery:
    def test_no_match(self):
        r = cleanup_single(make_random_query())
        assert r.verdict in (CleanupVerdict.NO_MATCH, CleanupVerdict.WEAK_MATCH)

class TestTopK:
    def test_top3(self):
        top = cleanup_top_k(V1_CODEBOOK.get_vector(FROZEN_SYMBOL_IDS[0]), k=3)
        assert len(top) == 3
        assert top[0][0] == FROZEN_SYMBOL_IDS[0]

class TestNoiseVerification:
    def test_batch(self):
        results = verify_all_noise_tolerance()
        at_0 = [r for r in results if r.noise_fraction == 0.0]
        assert all(r.recovered_correctly for r in at_0)

class TestBindCleanup:
    def test_unbind_recover(self):
        a = V1_CODEBOOK.get_vector(FROZEN_SYMBOL_IDS[0])
        b = V1_CODEBOOK.get_vector(FROZEN_SYMBOL_IDS[1])
        recovered = unbind(bind(a, b), b)
        r = cleanup_single(recovered)
        assert r.matched_symbol_id == FROZEN_SYMBOL_IDS[0]

class TestSerialization:
    def test_result(self):
        r = cleanup_single(V1_CODEBOOK.get_vector(FROZEN_SYMBOL_IDS[0]))
        d = r.to_dict()
        assert d["verdict"] == "CLEAN_MATCH"

class TestImmutability:
    def test_frozen(self):
        r = cleanup_single(V1_CODEBOOK.get_vector(FROZEN_SYMBOL_IDS[0]))
        with pytest.raises((AttributeError, TypeError)):
            r.verdict = CleanupVerdict.ERROR
