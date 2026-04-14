"""
Pytest — Unified Substrate Entrypoint Bridge V1
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import pytest
from aurexis_lang.unified_substrate_entrypoint_bridge_v1 import (
    ENTRYPOINT_VERSION, ENTRYPOINT_FROZEN,
    SubstrateRoute, RouteResult, ImportResult,
    BRIDGE_REGISTRY, ROUTE_BRIDGE_RANGES,
    V1_ENTRYPOINT,
    EXPECTED_ROUTE_COUNT, EXPECTED_BRIDGE_REGISTRY_SIZE,
)

def test_version(): assert ENTRYPOINT_VERSION == "V1.0"
def test_frozen(): assert ENTRYPOINT_FROZEN is True
def test_route_count(): assert len(V1_ENTRYPOINT.list_routes()) == 7
def test_registry_size(): assert len(BRIDGE_REGISTRY) == 40
def test_registry_keys(): assert set(BRIDGE_REGISTRY.keys()) == set(range(1, 41))

def test_import_bridge_1():
    r = V1_ENTRYPOINT.import_bridge(1)
    assert r.success
    assert r.module_name == "raster_law_bridge_v1"

def test_import_bridge_40():
    r = V1_ENTRYPOINT.import_bridge(40)
    assert r.success

def test_import_unknown_bridge():
    r = V1_ENTRYPOINT.import_bridge(999)
    assert not r.success

def test_import_by_name():
    r = V1_ENTRYPOINT.import_bridge_by_name("raster_law_bridge_v1")
    assert r.success and r.bridge_number == 1

def test_import_by_unknown_name():
    r = V1_ENTRYPOINT.import_bridge_by_name("nonexistent_v1")
    assert not r.success

@pytest.mark.parametrize("route", [
    SubstrateRoute.STATIC_SUBSTRATE,
    SubstrateRoute.TEMPORAL_TRANSPORT,
    SubstrateRoute.HIGHER_ORDER_COHERENCE,
    SubstrateRoute.VIEW_DEPENDENT,
    SubstrateRoute.VSA_CLEANUP,
])
def test_branch_route(route):
    r = V1_ENTRYPOINT.route(route)
    assert r.success
    assert r.bridge_count > 0

def test_manifest_route():
    r = V1_ENTRYPOINT.route(SubstrateRoute.MANIFEST)
    assert r.success

def test_compatibility_route():
    r = V1_ENTRYPOINT.route(SubstrateRoute.COMPATIBILITY)
    assert r.success

def test_route_all():
    results = V1_ENTRYPOINT.route_all()
    assert len(results) == 7
    assert all(r.success for r in results.values())

def test_entrypoint_hash():
    assert V1_ENTRYPOINT.entrypoint_hash() == V1_ENTRYPOINT.entrypoint_hash()
    assert len(V1_ENTRYPOINT.entrypoint_hash()) == 64

def test_list_bridges_static():
    assert len(V1_ENTRYPOINT.list_bridges(SubstrateRoute.STATIC_SUBSTRATE)) == 18

def test_list_bridges_temporal():
    assert len(V1_ENTRYPOINT.list_bridges(SubstrateRoute.TEMPORAL_TRANSPORT)) == 10

def test_list_bridges_all():
    assert len(V1_ENTRYPOINT.list_bridges()) == 40

def test_route_result_hash():
    r = V1_ENTRYPOINT.route(SubstrateRoute.STATIC_SUBSTRATE)
    assert len(r.result_hash) == 64
