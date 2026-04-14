"""
Pytest suite for VSA Cleanup Profile Bridge V1 (37th bridge).
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import pytest
from aurexis_lang.vsa_cleanup_profile_bridge_v1 import (
    CLEANUP_PROFILE_VERSION, CLEANUP_PROFILE_FROZEN,
    CleanupTargetKind, CleanupTarget, CleanupProfile,
    V1_CLEANUP_PROFILE, FROZEN_TARGETS, FROZEN_SYMBOL_IDS,
    EXPECTED_SET_TARGET_COUNT, EXPECTED_SEQ_TARGET_COUNT,
    EXPECTED_COLL_TARGET_COUNT, EXPECTED_TOTAL_TARGET_COUNT,
)

class TestModuleVersion:
    def test_version(self): assert CLEANUP_PROFILE_VERSION == "V1.0"
    def test_frozen(self): assert CLEANUP_PROFILE_FROZEN is True

class TestCounts:
    def test_total(self): assert V1_CLEANUP_PROFILE.target_count == 11
    def test_set(self): assert len(V1_CLEANUP_PROFILE.get_targets_by_kind(CleanupTargetKind.SET_CONTRACT)) == 5
    def test_seq(self): assert len(V1_CLEANUP_PROFILE.get_targets_by_kind(CleanupTargetKind.SEQUENCE_CONTRACT)) == 3
    def test_coll(self): assert len(V1_CLEANUP_PROFILE.get_targets_by_kind(CleanupTargetKind.COLLECTION_CONTRACT)) == 3

class TestUniqueness:
    def test_symbol_ids(self): assert len(set(FROZEN_SYMBOL_IDS)) == 11
    def test_substrate_names(self): assert len(set(t.substrate_name for t in FROZEN_TARGETS)) == 11

class TestLookup:
    @pytest.mark.parametrize("target", FROZEN_TARGETS)
    def test_by_symbol(self, target):
        assert V1_CLEANUP_PROFILE.get_target(target.symbol_id) is not None
    @pytest.mark.parametrize("target", FROZEN_TARGETS)
    def test_by_name(self, target):
        assert V1_CLEANUP_PROFILE.get_target_by_substrate_name(target.substrate_name) is not None
    def test_unknown_symbol(self): assert V1_CLEANUP_PROFILE.get_target("X") is None
    def test_unknown_name(self): assert V1_CLEANUP_PROFILE.get_target_by_substrate_name("X") is None

class TestSerialization:
    def test_profile(self):
        d = V1_CLEANUP_PROFILE.to_dict()
        assert d["target_count"] == 11
    @pytest.mark.parametrize("target", FROZEN_TARGETS)
    def test_target(self, target):
        d = target.to_dict()
        assert d["symbol_id"] == target.symbol_id

class TestImmutability:
    def test_frozen(self):
        with pytest.raises((AttributeError, TypeError)):
            FROZEN_TARGETS[0].symbol_id = "X"
