#!/usr/bin/env python3
"""
Aurexis Core — Unified Capability Manifest Bridge V1 — Standalone Test Runner
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

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
check(MANIFEST_VERSION == "V1.0", "Version V1.0")
check(MANIFEST_FROZEN is True, "Module frozen")

section("2. Expected Counts")
check(EXPECTED_BRIDGE_COUNT == 40, "Expected 40 bridges")
check(EXPECTED_BRANCH_COUNT == 5, "Expected 5 branches")
check(EXPECTED_FOUNDATION_MODULE_COUNT == 12, "Expected 12 foundation modules")
check(EXPECTED_TOTAL_MODULE_COUNT == 52, "Expected 52 total modules")
check(EXPECTED_EXCLUSION_COUNT == 4, "Expected 4 exclusions")

section("3. Manifest Totals")
check(V1_MANIFEST.total_bridges == 40, f"40 bridges (got {V1_MANIFEST.total_bridges})")
check(V1_MANIFEST.total_branches == 5, f"5 branches (got {V1_MANIFEST.total_branches})")
check(V1_MANIFEST.total_modules == 52, f"52 modules (got {V1_MANIFEST.total_modules})")
check(V1_MANIFEST.total_assertions > 5000, f"Assertions > 5000 (got {V1_MANIFEST.total_assertions})")

section("4. Bridge Numbering")
numbers = [b.bridge_number for b in V1_MANIFEST.bridges]
check(numbers == list(range(1, 41)), "Bridges numbered 1..40")
check(len(set(b.module_name for b in V1_MANIFEST.bridges)) == 40, "All module names unique")

section("5. Bridge Kind Distribution")
static = V1_MANIFEST.get_bridges_by_kind(BridgeKind.STATIC_SUBSTRATE)
temporal = V1_MANIFEST.get_bridges_by_kind(BridgeKind.TEMPORAL_TRANSPORT)
coherence = V1_MANIFEST.get_bridges_by_kind(BridgeKind.HIGHER_ORDER_COHERENCE)
view = V1_MANIFEST.get_bridges_by_kind(BridgeKind.VIEW_DEPENDENT)
vsa = V1_MANIFEST.get_bridges_by_kind(BridgeKind.VSA_CLEANUP)
check(len(static) == 18, f"18 static bridges (got {len(static)})")
check(len(temporal) == 10, f"10 temporal bridges (got {len(temporal)})")
check(len(coherence) == 4, f"4 coherence bridges (got {len(coherence)})")
check(len(view) == 4, f"4 view-dependent bridges (got {len(view)})")
check(len(vsa) == 4, f"4 VSA bridges (got {len(vsa)})")

section("6. Branch Status")
for br in V1_MANIFEST.branches:
    check(br.status == BranchStatus.COMPLETE_ENOUGH, f"{br.name} is COMPLETE_ENOUGH")

section("7. Branch Ranges Non-Overlapping")
ranges = [(br.bridge_range[0], br.bridge_range[1]) for br in V1_MANIFEST.branches]
overlap = False
for i in range(len(ranges)):
    for j in range(i+1, len(ranges)):
        if ranges[i][0] <= ranges[j][1] and ranges[j][0] <= ranges[i][1]:
            overlap = True
check(not overlap, "No branch range overlaps")
# Full coverage
covered = set()
for br in V1_MANIFEST.branches:
    for n in range(br.bridge_range[0], br.bridge_range[1]+1):
        covered.add(n)
check(covered == set(range(1, 41)), "Branch ranges cover all 40 bridges")

section("8. Foundation Modules")
check(len(FOUNDATION_MODULES) == 12, "12 foundation modules")
check(all(m.endswith("_v1") for m in FOUNDATION_MODULES), "All foundation names end with _v1")

section("9. Exclusions")
check(len(FROZEN_EXCLUSIONS) == 4, "4 exclusions defined")
names = [e.name for e in FROZEN_EXCLUSIONS]
check("OAM (Orbital Angular Momentum)" in names, "OAM excluded")
check("Optical Skyrmions" in names, "Skyrmions excluded")

section("10. Manifest Hash")
h1 = V1_MANIFEST.manifest_hash()
h2 = V1_MANIFEST.manifest_hash()
check(h1 == h2, "Hash deterministic")
check(len(h1) == 64, "Hash is 64 hex chars")

section("11. JSON Serialization")
j = V1_MANIFEST.to_json()
check('"bridges"' in j, "JSON contains bridges key")
check('"branches"' in j, "JSON contains branches key")
check('"exclusions"' in j, "JSON contains exclusions key")
import json
d = json.loads(j)
check(d["totals"]["bridges"] == 40, "JSON totals.bridges == 40")
check(d["totals"]["modules"] == 52, "JSON totals.modules == 52")

section("12. Verify Manifest (cross-check)")
checks = verify_manifest(V1_MANIFEST)
for k, v in checks.items():
    check(v, f"verify_manifest: {k}")

section("13. All Module Names")
all_mods = V1_MANIFEST.all_module_names
check(len(all_mods) == 52, f"52 total module names (got {len(all_mods)})")
check(len(set(all_mods)) == 52, "All module names unique across foundation+bridges")

section("14. Bridge Gate Pass Rates")
check(all(b.gate_pass_rate == 1.0 for b in V1_MANIFEST.bridges), "All bridges 100% gate pass rate")

# ── Summary ──
print(f"\n{'='*60}")
print(f"  TOTAL: {PASS_COUNT} passed, {FAIL_COUNT} failed")
print(f"{'='*60}")
if FAIL_COUNT > 0:
    sys.exit(1)
