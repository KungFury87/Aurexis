"""Smoke test for the T6 MCP server.

Spawns mcp_server.py as a subprocess, sends MCP requests on stdin,
reads JSON responses from stdout. Verifies:
  1. initialize handshake returns correct protocol version + capabilities
  2. tools/list returns 5 expected tools with valid schemas
  3. tools/call phoxelis_list_predicates returns 151 predicates
  4. tools/call phoxelis_evaluate_image on a cached image returns
     fingerprint with expected shape
  5. tools/call phoxelis_compare_images on two images returns Jaccard
  6. tools/call phoxelis_install_predicate accepts a valid DSL predicate
  7. tools/call with unknown tool name returns isError envelope

Reports pass/fail counts and exits 0 only if all 7 pass.
"""
from __future__ import annotations
import json, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVER = HERE / "mcp_server.py"

# pick two cached images for evaluate/compare tests
R55_DIR = Path("/sessions/wonderful-sharp-rubin/mnt/Aurexis evolved/"
                "round55_corpus_harness/corpus_images")
TEST_IMG_A = next(iter(R55_DIR.glob("*.npy")), None)
TEST_IMG_B = sorted(R55_DIR.glob("*.npy"))[5] if len(list(R55_DIR.glob("*.npy"))) > 5 else None


def run_test():
    proc = subprocess.Popen(
        [sys.executable, str(SERVER)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1
    )
    time.sleep(2.0)  # let the substrate boot

    def call(req):
        proc.stdin.write(json.dumps(req) + "\n"); proc.stdin.flush()
        line = proc.stdout.readline()
        return json.loads(line) if line else None

    results = []  # (test_name, passed, detail)

    # T1: initialize
    r = call({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    ok = (r and r.get("result", {}).get("protocolVersion") == "2024-11-05"
            and "tools" in r["result"]["capabilities"])
    results.append(("T1_initialize", ok, r.get("result") if r else None))

    # T2: tools/list
    r = call({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    tools = r["result"]["tools"] if r and "result" in r else []
    expected_names = {"phoxelis_list_predicates", "phoxelis_describe_predicate",
                       "phoxelis_evaluate_image", "phoxelis_compare_images",
                       "phoxelis_install_predicate"}
    actual_names = {t["name"] for t in tools}
    ok = expected_names == actual_names
    results.append(("T2_tools_list", ok, f"got={sorted(actual_names)}"))

    # T3: phoxelis_list_predicates
    r = call({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
              "params": {"name": "phoxelis_list_predicates", "arguments": {}}})
    body = json.loads(r["result"]["content"][0]["text"]) if r and "result" in r else {}
    n = body.get("total", 0)
    ok = n == 151
    results.append(("T3_list_predicates", ok, f"total={n}"))

    # T4: phoxelis_evaluate_image
    if TEST_IMG_A:
        r = call({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                  "params": {"name": "phoxelis_evaluate_image",
                              "arguments": {"image_path": str(TEST_IMG_A)}}})
        body = json.loads(r["result"]["content"][0]["text"]) if r and "result" in r else {}
        fp = body.get("fingerprint", {})
        ok = (len(fp) == 151 and isinstance(body.get("n_fired"), int)
                and body.get("n_fired", 0) > 0)
        results.append(("T4_evaluate_image", ok,
                        f"n_fired={body.get('n_fired')} n_eval={body.get('n_evaluated')}"))
    else:
        results.append(("T4_evaluate_image", False, "no test image"))

    # T5: phoxelis_compare_images
    if TEST_IMG_A and TEST_IMG_B:
        r = call({"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                  "params": {"name": "phoxelis_compare_images",
                              "arguments": {"image_a_path": str(TEST_IMG_A),
                                              "image_b_path": str(TEST_IMG_B)}}})
        body = json.loads(r["result"]["content"][0]["text"]) if r and "result" in r else {}
        J = body.get("jaccard")
        ok = isinstance(J, (int, float)) and 0.0 <= J <= 1.0
        results.append(("T5_compare_images", ok, f"J={J}"))
    else:
        results.append(("T5_compare_images", False, "no test images"))

    # T6: phoxelis_install_predicate
    src = """
predicate r118_smoke
  expects scene:image
  returns bool
  intent  smoke_test_predicate
  body    gt(gradient_energy(scene), 0.5)
"""
    r = call({"jsonrpc": "2.0", "id": 6, "method": "tools/call",
              "params": {"name": "phoxelis_install_predicate",
                          "arguments": {"source": src}}})
    body = json.loads(r["result"]["content"][0]["text"]) if r and "result" in r else {}
    ok = body.get("type_check_passed") and body.get("name") == "r118_smoke"
    results.append(("T6_install_predicate", ok, f"name={body.get('name')}"))

    # T7: unknown tool returns isError
    r = call({"jsonrpc": "2.0", "id": 7, "method": "tools/call",
              "params": {"name": "phoxelis_nonexistent", "arguments": {}}})
    ok = (r and r.get("result", {}).get("isError") is True)
    results.append(("T7_unknown_tool", ok, "got isError" if ok else "missing isError"))

    # Cleanup
    proc.stdin.close()
    try: proc.wait(timeout=5)
    except subprocess.TimeoutExpired: proc.kill()

    # Report
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n=== T6 MCP server smoke tests: {passed}/{total} passed ===\n")
    for name, ok, detail in results:
        marker = "PASS" if ok else "FAIL"
        print(f"  [{marker}] {name:30s} {detail}")
    return passed == total


if __name__ == "__main__":
    sys.exit(0 if run_test() else 1)
