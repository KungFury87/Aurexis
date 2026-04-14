#!/usr/bin/env python3
"""
Aurexis Core — VSA Cleanup Profile Bridge V1 — Standalone Test Runner
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from aurexis_lang.vsa_cleanup_profile_bridge_v1 import (
    CLEANUP_PROFILE_VERSION, CLEANUP_PROFILE_FROZEN,
    CleanupTargetKind, CleanupTarget, CleanupProfile,
    V1_CLEANUP_PROFILE, FROZEN_TARGETS, FROZEN_SYMBOL_IDS,
    EXPECTED_SET_TARGET_COUNT, EXPECTED_SEQ_TARGET_COUNT,
    EXPECTED_COLL_TARGET_COUNT, EXPECTED_TOTAL_TARGET_COUNT,
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
check(CLEANUP_PROFILE_VERSION == "V1.0", "Version V1.0")
check(CLEANUP_PROFILE_FROZEN is True, "Module frozen")

section("2. Expected Counts")
check(EXPECTED_SET_TARGET_COUNT == 5, "5 set targets expected")
check(EXPECTED_SEQ_TARGET_COUNT == 3, "3 sequence targets expected")
check(EXPECTED_COLL_TARGET_COUNT == 3, "3 collection targets expected")
check(EXPECTED_TOTAL_TARGET_COUNT == 11, "11 total targets expected")

section("3. Profile Target Count")
check(V1_CLEANUP_PROFILE.target_count == 11, f"Profile has 11 targets (got {V1_CLEANUP_PROFILE.target_count})")
check(len(FROZEN_TARGETS) == 11, "FROZEN_TARGETS has 11 entries")
check(len(FROZEN_SYMBOL_IDS) == 11, "11 frozen symbol IDs")

section("4. Target Kinds Distribution")
sets = V1_CLEANUP_PROFILE.get_targets_by_kind(CleanupTargetKind.SET_CONTRACT)
seqs = V1_CLEANUP_PROFILE.get_targets_by_kind(CleanupTargetKind.SEQUENCE_CONTRACT)
colls = V1_CLEANUP_PROFILE.get_targets_by_kind(CleanupTargetKind.COLLECTION_CONTRACT)
check(len(sets) == 5, f"5 SET_CONTRACT targets (got {len(sets)})")
check(len(seqs) == 3, f"3 SEQUENCE_CONTRACT targets (got {len(seqs)})")
check(len(colls) == 3, f"3 COLLECTION_CONTRACT targets (got {len(colls)})")

section("5. Symbol ID Uniqueness")
ids = set(FROZEN_SYMBOL_IDS)
check(len(ids) == 11, "All 11 symbol IDs unique")

section("6. Substrate Name Uniqueness")
names = set(t.substrate_name for t in FROZEN_TARGETS)
check(len(names) == 11, "All 11 substrate names unique")

section("7. Lookup by Symbol ID")
for t in FROZEN_TARGETS:
    found = V1_CLEANUP_PROFILE.get_target(t.symbol_id)
    check(found is not None and found.symbol_id == t.symbol_id, f"Lookup {t.symbol_id}")
check(V1_CLEANUP_PROFILE.get_target("NONEXISTENT") is None, "Unknown symbol returns None")

section("8. Lookup by Substrate Name")
for t in FROZEN_TARGETS:
    found = V1_CLEANUP_PROFILE.get_target_by_substrate_name(t.substrate_name)
    check(found is not None and found.substrate_name == t.substrate_name, f"Lookup {t.substrate_name}")
check(V1_CLEANUP_PROFILE.get_target_by_substrate_name("nonexistent") is None, "Unknown substrate returns None")

section("9. Set Contract Targets")
expected_set_names = ["two_horizontal_adj_cont", "two_vertical_adj_three", "three_row_all",
                      "two_horizontal_cont_three", "two_vertical_three_adj"]
for name in expected_set_names:
    t = V1_CLEANUP_PROFILE.get_target_by_substrate_name(name)
    check(t is not None and t.kind == CleanupTargetKind.SET_CONTRACT, f"Set target: {name}")

section("10. Sequence Contract Targets")
expected_seq_names = ["two_page_horizontal_vertical", "three_page_all_families", "two_page_mixed_reversed"]
for name in expected_seq_names:
    t = V1_CLEANUP_PROFILE.get_target_by_substrate_name(name)
    check(t is not None and t.kind == CleanupTargetKind.SEQUENCE_CONTRACT, f"Seq target: {name}")

section("11. Collection Contract Targets")
expected_coll_names = ["two_seq_hv_mixed", "three_seq_all", "two_seq_all_mixed"]
for name in expected_coll_names:
    t = V1_CLEANUP_PROFILE.get_target_by_substrate_name(name)
    check(t is not None and t.kind == CleanupTargetKind.COLLECTION_CONTRACT, f"Coll target: {name}")

section("12. Serialization")
d = V1_CLEANUP_PROFILE.to_dict()
check(d["target_count"] == 11, "Profile to_dict target_count")
check(len(d["targets"]) == 11, "Profile to_dict targets length")
check(d["version"] == "V1.0", "Profile to_dict version")
for t in FROZEN_TARGETS:
    td = t.to_dict()
    check(td["symbol_id"] == t.symbol_id, f"{t.symbol_id} to_dict")

section("13. Immutability")
try:
    FROZEN_TARGETS[0].symbol_id = "HACKED"
    check(False, "CleanupTarget should be immutable")
except (AttributeError, TypeError):
    check(True, "CleanupTarget is immutable")

print(f"\n{'='*60}")
print(f"  RESULTS: {PASS_COUNT} passed, {FAIL_COUNT} failed, {PASS_COUNT + FAIL_COUNT} total")
print(f"{'='*60}")
if FAIL_COUNT > 0:
    print("  *** FAILURES DETECTED ***"); sys.exit(1)
else:
    print("  ALL PASS"); sys.exit(0)
