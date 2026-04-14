#!/usr/bin/env python3
"""
Aurexis Core — Unified Substrate Entrypoint Bridge V1 — Standalone Test Runner
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from aurexis_lang.unified_substrate_entrypoint_bridge_v1 import (
    ENTRYPOINT_VERSION, ENTRYPOINT_FROZEN,
    SubstrateRoute, RouteResult, ImportResult,
    BRIDGE_REGISTRY, ROUTE_BRIDGE_RANGES,
    UnifiedSubstrateEntrypoint, V1_ENTRYPOINT,
    EXPECTED_ROUTE_COUNT, EXPECTED_BRIDGE_REGISTRY_SIZE,
    EXPECTED_BRANCH_ROUTE_COUNT,
)

PASS_COUNT = 0
FAIL_COUNT = 0

def section(name):
    print(f"\n{'='*60}\n  {name}\n{'='*60}")

def check(cond, label):
    global PASS_COUNT, FAIL_COUNT
    s = "PASS" if cond else "FAIL"
    if cond: PASS_COUNT += 1
    else: FAIL_COUNT += 1
    print(f"  [{s}] {label}")

section("1. Module Version and Frozen State")
check(ENTRYPOINT_VERSION == "V1.0", "Version V1.0")
check(ENTRYPOINT_FROZEN is True, "Module frozen")

section("2. Expected Counts")
check(EXPECTED_ROUTE_COUNT == 7, f"7 routes expected (got {EXPECTED_ROUTE_COUNT})")
check(EXPECTED_BRIDGE_REGISTRY_SIZE == 40, "40 bridges in registry")
check(EXPECTED_BRANCH_ROUTE_COUNT == 5, "5 branch routes")

section("3. Bridge Registry")
check(len(BRIDGE_REGISTRY) == 40, f"Registry has 40 entries (got {len(BRIDGE_REGISTRY)})")
check(set(BRIDGE_REGISTRY.keys()) == set(range(1, 41)), "Keys are 1..40")
check(len(set(BRIDGE_REGISTRY.values())) == 40, "All module names unique")

section("4. Route Enumeration")
routes = V1_ENTRYPOINT.list_routes()
check(len(routes) == 7, f"7 routes (got {len(routes)})")
check(SubstrateRoute.STATIC_SUBSTRATE in routes, "STATIC_SUBSTRATE route exists")
check(SubstrateRoute.MANIFEST in routes, "MANIFEST route exists")
check(SubstrateRoute.COMPATIBILITY in routes, "COMPATIBILITY route exists")

section("5. List Bridges by Route")
static = V1_ENTRYPOINT.list_bridges(SubstrateRoute.STATIC_SUBSTRATE)
check(len(static) == 18, f"18 static bridges (got {len(static)})")
temporal = V1_ENTRYPOINT.list_bridges(SubstrateRoute.TEMPORAL_TRANSPORT)
check(len(temporal) == 10, f"10 temporal bridges (got {len(temporal)})")
coherence = V1_ENTRYPOINT.list_bridges(SubstrateRoute.HIGHER_ORDER_COHERENCE)
check(len(coherence) == 4, f"4 coherence bridges (got {len(coherence)})")
view = V1_ENTRYPOINT.list_bridges(SubstrateRoute.VIEW_DEPENDENT)
check(len(view) == 4, f"4 view-dependent bridges (got {len(view)})")
vsa = V1_ENTRYPOINT.list_bridges(SubstrateRoute.VSA_CLEANUP)
check(len(vsa) == 4, f"4 VSA bridges (got {len(vsa)})")

section("6. Import Bridge by Number")
r = V1_ENTRYPOINT.import_bridge(1)
check(r.success, "Bridge 1 imports successfully")
check(r.module_name == "raster_law_bridge_v1", "Bridge 1 is raster_law_bridge_v1")
r40 = V1_ENTRYPOINT.import_bridge(40)
check(r40.success, "Bridge 40 imports successfully")
check(r40.module_name == "vsa_consistency_contract_bridge_v1", "Bridge 40 is vsa_consistency_contract")

section("7. Import Bridge by Name")
r = V1_ENTRYPOINT.import_bridge_by_name("substrate_v1")
check(not r.success, "substrate_v1 not in bridge registry (it's a foundation module)")
r = V1_ENTRYPOINT.import_bridge_by_name("raster_law_bridge_v1")
check(r.success, "raster_law_bridge_v1 found by name")
check(r.bridge_number == 1, "Correct bridge number for raster_law")

section("8. Unknown Bridge Handling")
r = V1_ENTRYPOINT.import_bridge(999)
check(not r.success, "Bridge 999 fails gracefully")
check("Unknown" in r.error, "Error mentions 'Unknown'")
r = V1_ENTRYPOINT.import_bridge_by_name("nonexistent_v1")
check(not r.success, "Nonexistent module fails gracefully")

section("9. Route into Branch Routes")
for route_name in [SubstrateRoute.STATIC_SUBSTRATE, SubstrateRoute.TEMPORAL_TRANSPORT,
                   SubstrateRoute.HIGHER_ORDER_COHERENCE, SubstrateRoute.VIEW_DEPENDENT,
                   SubstrateRoute.VSA_CLEANUP]:
    r = V1_ENTRYPOINT.route(route_name)
    check(r.success, f"{route_name.value}: success")
    check(r.bridge_count > 0, f"{route_name.value}: bridge_count > 0")
    check(len(r.modules_loaded) == r.bridge_count, f"{route_name.value}: all bridges loaded")

section("10. Route into Cross-Cutting Routes")
r = V1_ENTRYPOINT.route(SubstrateRoute.MANIFEST)
check(r.success, "MANIFEST route succeeds")
check("unified_capability_manifest" in r.modules_loaded[0], "Manifest module loaded")
r = V1_ENTRYPOINT.route(SubstrateRoute.COMPATIBILITY)
check(r.success, "COMPATIBILITY route succeeds")
check("cross_branch_compatibility" in r.modules_loaded[0], "Compatibility module loaded")

section("11. Route All")
all_results = V1_ENTRYPOINT.route_all()
check(len(all_results) == 7, f"7 route results (got {len(all_results)})")
check(all(r.success for r in all_results.values()), "All routes succeed")

section("12. Entrypoint Hash")
h1 = V1_ENTRYPOINT.entrypoint_hash()
h2 = V1_ENTRYPOINT.entrypoint_hash()
check(h1 == h2, "Hash deterministic")
check(len(h1) == 64, "Hash is 64 hex chars")

section("13. RouteResult Hash")
r = V1_ENTRYPOINT.route(SubstrateRoute.STATIC_SUBSTRATE)
rh1 = r.result_hash
rh2 = r.result_hash
check(rh1 == rh2, "RouteResult hash deterministic")
check(len(rh1) == 64, "RouteResult hash is 64 hex chars")

section("14. Route Bridge Ranges Consistency")
for route, (lo, hi) in ROUTE_BRIDGE_RANGES.items():
    bridges = V1_ENTRYPOINT.list_bridges(route)
    check(len(bridges) == hi - lo + 1, f"{route.value}: range ({lo},{hi}) → {len(bridges)} bridges")

# ── Summary ──
print(f"\n{'='*60}")
print(f"  TOTAL: {PASS_COUNT} passed, {FAIL_COUNT} failed")
print(f"{'='*60}")
if FAIL_COUNT > 0:
    sys.exit(1)
