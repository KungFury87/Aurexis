"""
Pytest suite for Hypervector Binding / Bundling Bridge V1 (38th bridge).
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import pytest
from aurexis_lang.vsa_cleanup_profile_bridge_v1 import FROZEN_SYMBOL_IDS
from aurexis_lang.hypervector_binding_bundling_bridge_v1 import (
    BINDING_VERSION, BINDING_FROZEN, DIMENSION,
    generate_atomic, bind, unbind, bundle, permute, inverse_permute,
    cosine_similarity, add_noise,
    V1_CODEBOOK, encode_ordered_set, encode_bound_pair,
    EXPECTED_CODEBOOK_SIZE,
)

class TestModuleVersion:
    def test_version(self): assert BINDING_VERSION == "V1.0"
    def test_frozen(self): assert BINDING_FROZEN is True
    def test_dimension(self): assert DIMENSION == 1024

class TestCodebook:
    def test_size(self): assert V1_CODEBOOK.size == 11
    @pytest.mark.parametrize("sid", FROZEN_SYMBOL_IDS)
    def test_lookup(self, sid):
        v = V1_CODEBOOK.get_vector(sid)
        assert v is not None and len(v) == DIMENSION
    def test_unknown(self): assert V1_CODEBOOK.get_vector("X") is None

class TestAtomic:
    def test_dimension(self): assert len(generate_atomic("test")) == DIMENSION
    def test_bipolar(self): assert all(x in (-1, 1) for x in generate_atomic("test"))
    def test_deterministic(self): assert generate_atomic("a") == generate_atomic("a")
    def test_different(self): assert generate_atomic("a") != generate_atomic("b")

class TestSimilarity:
    def test_self(self): assert cosine_similarity(generate_atomic("a"), generate_atomic("a")) == 1.0
    def test_orthogonal(self):
        s = cosine_similarity(generate_atomic("a"), generate_atomic("b"))
        assert abs(s) < 0.15

class TestBind:
    def test_self_inverse(self):
        a, b = generate_atomic("a"), generate_atomic("b")
        assert cosine_similarity(unbind(bind(a, b), b), a) == 1.0
    def test_dissimilar(self):
        a, b = generate_atomic("a"), generate_atomic("b")
        assert abs(cosine_similarity(bind(a, b), a)) < 0.15

class TestBundle:
    def test_retains_similarity(self):
        a, b = generate_atomic("a"), generate_atomic("b")
        bun = bundle(a, b)
        assert cosine_similarity(bun, a) > 0.3
        assert cosine_similarity(bun, b) > 0.3

class TestPermute:
    def test_changes_vector(self):
        v = generate_atomic("test")
        assert permute(v, 1) != v
    def test_inverse(self):
        v = generate_atomic("test")
        assert inverse_permute(permute(v, 3), 3) == v
    def test_identity(self):
        v = generate_atomic("test")
        assert permute(v, 0) == v

class TestNoise:
    def test_deterministic(self):
        v = generate_atomic("test")
        assert add_noise(v, 0.1, 42) == add_noise(v, 0.1, 42)
    def test_reduces_similarity(self):
        v = generate_atomic("test")
        assert cosine_similarity(add_noise(v, 0.2, 42), v) < 1.0

class TestEncode:
    def test_ordered_set(self):
        v = encode_ordered_set(FROZEN_SYMBOL_IDS[:3])
        assert len(v) == DIMENSION
    def test_bound_pair_recover(self):
        bp = encode_bound_pair(FROZEN_SYMBOL_IDS[0], FROZEN_SYMBOL_IDS[1])
        recovered = unbind(bp, generate_atomic(FROZEN_SYMBOL_IDS[1]))
        assert cosine_similarity(recovered, generate_atomic(FROZEN_SYMBOL_IDS[0])) == 1.0

class TestCollisionResistance:
    def test_all_distinct(self):
        vecs = set(generate_atomic(s) for s in FROZEN_SYMBOL_IDS)
        assert len(vecs) == len(FROZEN_SYMBOL_IDS)
