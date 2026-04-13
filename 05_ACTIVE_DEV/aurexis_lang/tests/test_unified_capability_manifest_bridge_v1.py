"""
Pytest — Unified Capability Manifest Bridge V1
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import json
import pytest
from aurexis_lang.unified_capability_manifest_bridge_v1 import (
    MANIFEST_VERSION, MANIFEST_FROZEN,
    BranchStatus, BridgeKind,
    BridgeDescriptor, BranchDescriptor, ExcludedItem,
    CapabilityManifest,
    V1_MANIFEST, FROZEN_BRIDGES, FROZEN_BRANCHES, FROZEN_EXCLUSIONS,
    FOUNDATION_MODULES,
    verify_manifest,
    EXPECTED_BRIDGE_COUNT, EXPECTED_BRANCH_COUNT,
    EXPECTED_FOUNDATION_MODULE_COUNT, EXPECTED_TOTAL_MODULE_COUNT,
    EXPECTED_EXCLUSION_COUNT,
)

def test_version(): assert MANIFEST_VERSION == "V1.0"
def test_frozen(): assert MANIFEST_FROZEN is True
def test_bridge_count(): assert V1_MANIFEST.total_bridges == 40
def test_branch_count(): assert V1_MANIFEST.total_branches == 5
def test_total_modules(): assert V1_MANIFEST.total_modules == 52
def test_foundation_count(): assert len(FOUNDATION_MODULES) == 12
def test_exclusion_count(): assert len(FROZEN_EXCLUSIONS) == 4

def test_bridge_numbering():
    assert [b.bridge_number for b in V1_MANIFEST.bridges] == list(range(1, 41))

def test_module_names_unique():
    names = [b.module_name for b in V1_MANIFEST.bridges]
    assert len(set(names)) == 40

def test_all_branches_complete():
    for br in V1_MANIFEST.branches:
        assert br.status == BranchStatus.COMPLETE_ENOUGH

def test_branch_ranges_no_overlap():
    ranges = [(br.bridge_range[0], br.bridge_range[1]) for br in V1_MANIFEST.branches]
    for i in range(len(ranges)):
        for j in range(i + 1, len(ranges)):
            assert not (ranges[i][0] <= ranges[j][1] and ranges[j][0] <= ranges[i][1])

def test_branch_ranges_cover_all():
    covered = set()
    for br in V1_MANIFEST.branches:
        for n in range(br.bridge_range[0], br.bridge_range[1] + 1):
            covered.add(n)
    assert covered == set(range(1, 41))

def test_manifest_hash_deterministic():
    assert V1_MANIFEST.manifest_hash() == V1_MANIFEST.manifest_hash()
    assert len(V1_MANIFEST.manifest_hash()) == 64

def test_json_serialization():
    j = V1_MANIFEST.to_json()
    d = json.loads(j)
    assert d["totals"]["bridges"] == 40
    assert d["totals"]["modules"] == 52

def test_verify_manifest_all_pass():
    checks = verify_manifest(V1_MANIFEST)
    for k, v in checks.items():
        assert v, f"verify_manifest failed: {k}"

def test_static_bridges(): assert len(V1_MANIFEST.get_bridges_by_kind(BridgeKind.STATIC_SUBSTRATE)) == 18
def test_temporal_bridges(): assert len(V1_MANIFEST.get_bridges_by_kind(BridgeKind.TEMPORAL_TRANSPORT)) == 10
def test_coherence_bridges(): assert len(V1_MANIFEST.get_bridges_by_kind(BridgeKind.HIGHER_ORDER_COHERENCE)) == 4
def test_view_bridges(): assert len(V1_MANIFEST.get_bridges_by_kind(BridgeKind.VIEW_DEPENDENT)) == 4
def test_vsa_bridges(): assert len(V1_MANIFEST.get_bridges_by_kind(BridgeKind.VSA_CLEANUP)) == 4
def test_gate_pass_rate(): assert all(b.gate_pass_rate == 1.0 for b in V1_MANIFEST.bridges)

def test_get_branch_by_name():
    br = V1_MANIFEST.get_branch_by_name("Static Artifact Substrate")
    assert br is not None
    assert br.bridge_range == (1, 18)

def test_get_branch_not_found():
    assert V1_MANIFEST.get_branch_by_name("Nonexistent") is None

def test_all_module_names():
    names = V1_MANIFEST.all_module_names
    assert len(names) == 52
    assert len(set(names)) == 52

def test_naming_convention():
    for m in V1_MANIFEST.all_module_names:
        assert m.endswith("_v1")
