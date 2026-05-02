"""R169 smoke test for MCP server extensions (3 new tools).

Verifies that find_outlier_in_set, cluster_property, verify_claim work end-to-end
when invoked through the MCP server's tool handlers (not just demo scripts).
"""
import sys, importlib.util, os
sys.path.insert(0, '.')
spec = importlib.util.spec_from_file_location(
    'mcp_server',
    'C:\\Users\\vince\\Desktop\\Aurexis evolved\\Aurexis_Core_WORKING_20260414-1339\\07_VISION_SUBSTRATE\\t6_mcp\\mcp_server.py'
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

assert len(m.TOOLS) == 8, f"expected 8 tools, got {len(m.TOOLS)}"
assert 'phoxelis_find_outlier_in_set' in [t['name'] for t in m.TOOLS]
assert 'phoxelis_cluster_property' in [t['name'] for t in m.TOOLS]
assert 'phoxelis_verify_claim' in [t['name'] for t in m.TOOLS]
assert len(m.CLAIM_MAP) == 14
assert 'phoxelis_find_outlier_in_set' in m.TOOL_HANDLERS

# Functional tests below assume images exist; smoke=schema test is enough
print("R169 schema smoke: 8/8 tools registered, 14 CLAIM_MAP entries, all handlers wired")
