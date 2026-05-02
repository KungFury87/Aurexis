"""T6 MCP server — wraps the Phoxelis substrate as an MCP-protocol-compliant
stdio JSON-RPC server.

Reuses the R72 in-process runtime: boots vocab.aurex once on startup,
serves one JSON-RPC request per line on stdin, writes responses on stdout.

Implements MCP protocol version 2024-11-05:
  initialize          — handshake + capability negotiation
  initialized         — notification, no response
  tools/list          — return tool schemas
  tools/call          — invoke a tool, return result envelope
  notifications/*     — silent ignore

8 tools (5 from R115 design + 3 R169 grounded-reasoning):
  phoxelis_list_predicates
  phoxelis_describe_predicate
  phoxelis_evaluate_image
  phoxelis_compare_images
  phoxelis_install_predicate
  phoxelis_find_outlier_in_set     (R169)
  phoxelis_cluster_property        (R169)
  phoxelis_verify_claim            (R169)

Usage:
  python3 mcp_server.py
  (then send JSON-RPC requests one-per-line on stdin)

Logs go to stderr, never stdout (stdout is reserved for protocol).
"""
from __future__ import annotations
import sys, json, traceback, warnings
from pathlib import Path
import numpy as np
from PIL import Image

warnings.filterwarnings("ignore")

# --- locate Phoxelis core ---------------------------------------------------
HERE = Path(__file__).resolve().parent
CORE = HERE.parent  # 07_VISION_SUBSTRATE
sys.path.insert(0, str(CORE))

from aurexis_workbench import dsl, vision_ops, predicates as P, runtime as RT
from aurexis_workbench.fields import FieldBundle

# --- protocol constants -----------------------------------------------------
PROTO_VERSION = "2024-11-05"
SERVER_NAME = "phoxelis"
SERVER_VERSION = "0.1.0"

# --- bootstrap substrate ----------------------------------------------------
def _log(msg):
    sys.stderr.write(f"[mcp_server] {msg}\n"); sys.stderr.flush()

vision_ops.register_all()
RT_GLOBAL = RT.Runtime()
PRED_OBJS = {}  # name -> Predicate

def _install_vocab():
    src = (CORE / "data/vision/vocab.aurex").read_text()
    names = []
    for pp in dsl.parse_source(src):
        if not pp.ok: continue
        try:
            P.type_check(pp.pred)
            RT_GLOBAL.install(pp.pred)
            PRED_OBJS[pp.pred.name] = pp.pred
            names.append(pp.pred.name)
        except Exception: pass
    return names

INSTALLED = _install_vocab()
_log(f"booted; {len(INSTALLED)} predicates installed")

# --- helpers ----------------------------------------------------------------
def _load_rgb(path):
    p = Path(path)
    if p.suffix.lower() == ".npy":
        arr = np.load(p)
    else:
        arr = np.asarray(Image.open(p).convert("RGB"))
    if arr.ndim != 3 or arr.shape[-1] != 3:
        raise ValueError(f"image must be HxWx3 RGB; got shape {arr.shape}")
    img = Image.fromarray(arr.astype(np.uint8))
    img.thumbnail((320, 320), Image.LANCZOS)
    return np.asarray(img)

def _build_bundle(rgb_u8, name="image", depth_path=None, spectral_path=None):
    luma = (0.299*rgb_u8[...,0] + 0.587*rgb_u8[...,1]
            + 0.114*rgb_u8[...,2]).astype(np.float64) / 255.0
    color = rgb_u8.astype(np.float64) / 255.0
    b = FieldBundle(name=name)
    b.add_value("scene", "image", luma, "luma channel")
    b.add_value("color_scene", "color_image", color, "RGB image")
    b.add_value("burst", "image_stack",
                 np.stack([luma, luma], axis=0),
                 "single image broadcast to 2-frame stack")
    b.add_value("patch_size", "int", 64, "ROI size")
    b.add_value("row_y", "int", luma.shape[0]//2, "reference row")
    b.add_value("foreground_threshold", "scalar", 0.4, "depth foreground threshold")
    if depth_path:
        d = np.load(depth_path) if Path(depth_path).suffix == ".npy" \
            else np.asarray(Image.open(depth_path).convert("L"), dtype=np.float64) / 255.0
        b.add_value("depth_field", "depth", d, "depth map")
    if spectral_path:
        s = np.load(spectral_path)
        b.add_value("spectral", "hyperspectral", s, "31-band cube")
    return b

def _eval_pred(name, bundle):
    rec = RT_GLOBAL.evaluate(name, bundle)
    if rec.error:
        return {"value": None, "error": str(rec.error)}
    return {"value": bool(rec.value), "error": None}

def _jaccard(set_a, set_b):
    if not set_a and not set_b: return 1.0
    if not set_a or not set_b:  return 0.0
    return len(set_a & set_b) / len(set_a | set_b)

# --- predicate metadata helpers --------------------------------------------
def _predicate_summary(name):
    """Return {name, intent, expects, returns, body_dsl} for one predicate."""
    pred = PRED_OBJS.get(name)
    if pred is None: return None
    expects = []
    for fname, ftype in pred.expects.items():
        expects.append({"name": fname, "dtype": ftype})
    return {
        "name": pred.name,
        "intent": pred.intent or "",
        "expects": expects,
        "returns": pred.return_type or "bool",
    }

def _predicate_full(name):
    """Like _predicate_summary but includes body DSL."""
    s = _predicate_summary(name)
    if s is None: return None
    pred = PRED_OBJS[name]
    # Best-effort DSL serialization — uses the AST repr
    try:
        from aurexis_workbench import predicates as PP
        body_dict = PP.to_dict(pred.body) if hasattr(pred, "body") else {}
        s["body_dsl"] = json.dumps(body_dict)
    except Exception:
        s["body_dsl"] = "<unavailable>"
    return s

# --- TOOLS ------------------------------------------------------------------
TOOLS = [
    {
        "name": "phoxelis_list_predicates",
        "description": (
            "List all installed predicates with their intent, expected fields, "
            "and return type. Use this to discover what perceptual capabilities "
            "the substrate exposes."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "description": "Optional substring filter on predicate names."
                }
            }
        }
    },
    {
        "name": "phoxelis_describe_predicate",
        "description": (
            "Return full information about a single predicate, including "
            "its DSL body (as a structured dict)."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string", "description": "Predicate name."}
            }
        }
    },
    {
        "name": "phoxelis_evaluate_image",
        "description": (
            "Run the substrate against an image and return which predicates "
            "fire. The fingerprint is a {predicate_name: bool} dict. "
            "Optional depth_path / spectral_path enable multi-modal predicates "
            "(R107). Predicates whose required fields aren't provided "
            "abstain (returned as null)."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["image_path"],
            "properties": {
                "image_path": {"type": "string", "description": "Path to RGB image (.png/.jpg/.npy)."},
                "depth_path": {"type": "string", "description": "Optional path to depth map (.npy or grayscale .png)."},
                "spectral_path": {"type": "string", "description": "Optional path to hyperspectral cube (.npy, HxWxN_bands)."},
                "predicate_filter": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Optional subset of predicate names; omit = all installed."
                }
            }
        }
    },
    {
        "name": "phoxelis_compare_images",
        "description": (
            "Compare two images via their substrate fingerprints. Returns "
            "Jaccard similarity, shared fires, and image-specific fires. "
            "Substrate similarity beats pHash and dHash on geometric "
            "transforms per R98/R99."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["image_a_path", "image_b_path"],
            "properties": {
                "image_a_path": {"type": "string"},
                "image_b_path": {"type": "string"},
                "predicate_filter": {"type": "array", "items": {"type": "string"}}
            }
        }
    },
    {
        "name": "phoxelis_install_predicate",
        "description": (
            "Install a new predicate from DSL source. Persists for the "
            "session. Returns the name and any type-check diagnostics."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["source"],
            "properties": {
                "source": {"type": "string", "description": "DSL predicate source text."}
            }
        }
    },
    {
        "name": "phoxelis_find_outlier_in_set",
        "description": (
            "Given a list of image paths, find the outlier (image whose substrate "
            "fingerprint has lowest mean Jaccard to the others). Returns outlier "
            "path, mean Jaccards per image, and the cluster (everything else). "
            "Per R167 grounded-reasoning."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["image_paths"],
            "properties": {
                "image_paths": {"type": "array", "items": {"type": "string"},
                                "description": "List of image paths (>= 3)."}
            }
        }
    },
    {
        "name": "phoxelis_cluster_property",
        "description": (
            "Given a list of image paths, return predicates fired by ALL images "
            "(cluster-shared) and predicates fired by NONE (cluster-rejected). "
            "Per R167."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["image_paths"],
            "properties": {
                "image_paths": {"type": "array", "items": {"type": "string"},
                                "description": "List of image paths (>= 2)."}
            }
        }
    },
    {
        "name": "phoxelis_verify_claim",
        "description": (
            "Verify a natural-language claim about an image by mapping the claim "
            "to a predicate constraint set and checking the substrate fingerprint. "
            "Returns verdict (bool), evidence_predicates (fired), and missing_predicates. "
            "Supports a fixed CLAIM_MAP (R168 vintage)."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["image_path", "claim"],
            "properties": {
                "image_path": {"type": "string"},
                "claim": {"type": "string", "description": "One of: 'is outdoors', 'is indoors', 'contains a person', 'is monochrome', 'has a horizon', 'has warm tones', 'has cool tones', 'is high contrast', 'has blue tones', 'has low-key lighting', 'is centered', 'has high frequency detail', 'is largely empty', 'has vegetation'."}
            }
        }
    }
]

# --- R168 CLAIM MAP -----------------------------------------------------------
CLAIM_MAP = {
    "is outdoors":              [('NOT_ANY', ['has_indoor_scene_signature'])],
    "is indoors":               [('OR', ['has_indoor_scene_signature'])],
    "contains a person":        [('OR', ['has_face_like_signature', 'has_human_subject_signature', 'has_skin_tone_signature'])],
    "is monochrome":            [('OR', ['has_monochrome', 'has_pure_grayscale_palette'])],
    "has a horizon":            [('OR', ['has_clear_horizon'])],
    "has warm tones":           [('OR', ['has_warm_palette', 'has_strongly_warm_palette'])],
    "has cool tones":           [('OR', ['has_cool_palette', 'has_dominant_blue_hue'])],
    "is high contrast":         [('OR', ['is_high_contrast_image'])],
    "has blue tones":           [('OR', ['has_dominant_blue_hue', 'has_significant_cyan_hue'])],
    "has low-key lighting":     [('OR', ['has_low_key', 'has_low_light_signature'])],
    "is centered":              [('OR', ['has_centered_subject'])],
    "has high frequency detail":[('OR', ['has_high_frequency_residual'])],
    "is largely empty":         [('OR', ['has_significant_negative_space'])],
    "has vegetation":           [('OR', ['has_vegetation_signature', 'has_green_dominant'])],
}

# --- TOOL HANDLERS ----------------------------------------------------------
def tool_list_predicates(args):
    flt = args.get("filter", "")
    out = []
    for n in INSTALLED:
        if flt and flt not in n: continue
        s = _predicate_summary(n)
        if s: out.append(s)
    return {"predicates": out, "total": len(INSTALLED)}

def tool_describe_predicate(args):
    name = args.get("name")
    if not name: raise ValueError("missing 'name'")
    full = _predicate_full(name)
    if full is None: raise ValueError(f"unknown predicate: {name}")
    return full

def tool_evaluate_image(args):
    path = args.get("image_path")
    if not path: raise ValueError("missing 'image_path'")
    rgb = _load_rgb(path)
    bundle = _build_bundle(rgb, name=Path(path).stem,
                            depth_path=args.get("depth_path"),
                            spectral_path=args.get("spectral_path"))
    flt = args.get("predicate_filter") or INSTALLED
    fp = {}; n_fired = 0; n_abstained = 0; errors = {}
    for name in flt:
        v = _eval_pred(name, bundle)
        if v["error"] is not None:
            # Abstention vs error: type-mismatch (missing field) = abstain
            if "required" in v["error"].lower() or "missing" in v["error"].lower() or "field" in v["error"].lower():
                fp[name] = None; n_abstained += 1
            else:
                fp[name] = None; errors[name] = v["error"]
        else:
            fp[name] = v["value"]
            if v["value"]: n_fired += 1
    fired_names = [n for n, v in fp.items() if v is True]
    intent_summary = ", ".join(sorted(fired_names)[:8])
    if len(fired_names) > 8:
        intent_summary += f", and {len(fired_names) - 8} more"
    return {
        "fingerprint": fp,
        "errors": errors,
        "n_evaluated": len(flt),
        "n_fired": n_fired,
        "n_abstained": n_abstained,
        "intent_summary": intent_summary or "(no predicates fired)",
    }

def tool_compare_images(args):
    a = tool_evaluate_image({"image_path": args["image_a_path"],
                              "predicate_filter": args.get("predicate_filter")})
    b = tool_evaluate_image({"image_path": args["image_b_path"],
                              "predicate_filter": args.get("predicate_filter")})
    fired_a = {n for n, v in a["fingerprint"].items() if v is True}
    fired_b = {n for n, v in b["fingerprint"].items() if v is True}
    J = _jaccard(fired_a, fired_b)
    shared = sorted(fired_a & fired_b)
    a_only = sorted(fired_a - fired_b)
    b_only = sorted(fired_b - fired_a)
    return {
        "jaccard": round(J, 4),
        "shared_fires": shared,
        "a_only": a_only,
        "b_only": b_only,
        "near_duplicate": J >= 0.80,
    }

def tool_install_predicate(args):
    src = args.get("source", "")
    if not src: raise ValueError("missing 'source'")
    parsed = list(dsl.parse_source(src))
    if not parsed or not parsed[0].ok:
        diags = [{"code": d.code, "message": d.message}
                 for d in (parsed[0].diagnostics if parsed else [])]
        return {"name": None, "type_check_passed": False, "diagnostics": diags}
    pred = parsed[0].pred
    try:
        P.type_check(pred)
        RT_GLOBAL.install(pred)
        if pred.name not in INSTALLED:
            INSTALLED.append(pred.name)
        PRED_OBJS[pred.name] = pred
        return {"name": pred.name, "type_check_passed": True, "diagnostics": []}
    except Exception as e:
        return {"name": pred.name, "type_check_passed": False,
                "diagnostics": [{"code": "TYPE_FAIL", "message": str(e)}]}

def tool_find_outlier_in_set(args):
    paths = args.get("image_paths") or []
    if len(paths) < 2:
        raise ValueError("'image_paths' must contain at least 2 paths")
    fingerprints = []
    for p in paths:
        e = tool_evaluate_image({"image_path": p})
        fired = {n for n, v in e["fingerprint"].items() if v is True}
        fingerprints.append(fired)
    n = len(paths)
    mean_J = []
    for i in range(n):
        others = [_jaccard(fingerprints[i], fingerprints[j]) for j in range(n) if j != i]
        mean_J.append(sum(others) / len(others) if others else 0.0)
    outlier_idx = mean_J.index(min(mean_J))
    cluster = [paths[i] for i in range(n) if i != outlier_idx]
    return {
        "outlier": paths[outlier_idx],
        "outlier_mean_jaccard": round(mean_J[outlier_idx], 4),
        "mean_jaccard_per_image": [round(x, 4) for x in mean_J],
        "cluster": cluster,
        "cluster_mean_jaccard": round(sum(mean_J[i] for i in range(n) if i != outlier_idx) / max(1, n-1), 4),
    }

def tool_cluster_property(args):
    paths = args.get("image_paths") or []
    if len(paths) < 2:
        raise ValueError("'image_paths' must contain at least 2 paths")
    fingerprints = []
    for p in paths:
        e = tool_evaluate_image({"image_path": p})
        fired = {n for n, v in e["fingerprint"].items() if v is True}
        fingerprints.append(fired)
    shared = set(fingerprints[0])
    for fp in fingerprints[1:]:
        shared = shared & fp
    union_fired = set()
    for fp in fingerprints:
        union_fired = union_fired | fp
    rejected = [p for p in INSTALLED if p not in union_fired]
    return {
        "shared_predicates": sorted(shared),
        "rejected_predicates": sorted(rejected)[:20],
        "n_shared": len(shared),
        "n_rejected": len(rejected),
        "n_images": len(paths),
    }

def tool_verify_claim(args):
    path = args.get("image_path")
    claim = args.get("claim")
    if not path: raise ValueError("missing 'image_path'")
    if not claim: raise ValueError("missing 'claim'")
    if claim not in CLAIM_MAP:
        return {
            "verdict": None,
            "error": f"unsupported claim: '{claim}'",
            "supported_claims": list(CLAIM_MAP.keys()),
        }
    e = tool_evaluate_image({"image_path": path})
    fp = e["fingerprint"]
    constraints = CLAIM_MAP[claim]
    overall = True
    evidence = []
    missing = []
    for op, preds in constraints:
        if op == 'OR':
            satisfied = any(fp.get(p) is True for p in preds)
            if satisfied:
                evidence.extend([p for p in preds if fp.get(p) is True])
            else:
                missing.extend(preds); overall = False
        elif op == 'AND':
            satisfied = all(fp.get(p) is True for p in preds)
            if satisfied:
                evidence.extend(preds)
            else:
                missing.extend([p for p in preds if fp.get(p) is not True]); overall = False
        elif op == 'NOT_ANY':
            violations = [p for p in preds if fp.get(p) is True]
            satisfied = not violations
            if satisfied:
                evidence.append(f"NOT_ANY({preds})")
            else:
                missing.extend(violations); overall = False
    return {
        "verdict": overall,
        "claim": claim,
        "image": path,
        "evidence_predicates": evidence,
        "missing_predicates": missing,
    }

TOOL_HANDLERS = {
    "phoxelis_list_predicates":     tool_list_predicates,
    "phoxelis_describe_predicate":  tool_describe_predicate,
    "phoxelis_evaluate_image":      tool_evaluate_image,
    "phoxelis_compare_images":      tool_compare_images,
    "phoxelis_install_predicate":   tool_install_predicate,
    "phoxelis_find_outlier_in_set": tool_find_outlier_in_set,
    "phoxelis_cluster_property":    tool_cluster_property,
    "phoxelis_verify_claim":        tool_verify_claim,
}

# --- PROTOCOL HANDLERS ------------------------------------------------------
def handle_initialize(params):
    return {
        "protocolVersion": PROTO_VERSION,
        "capabilities": {"tools": {}},
        "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
    }

def handle_tools_list(_params):
    return {"tools": TOOLS}

def handle_tools_call(params):
    name = params.get("name")
    args = params.get("arguments", {})
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return {
            "isError": True,
            "content": [{"type": "text", "text": f"unknown tool: {name}"}]
        }
    try:
        result = handler(args)
        return {"content": [{"type": "text", "text": json.dumps(result)}]}
    except Exception as e:
        return {
            "isError": True,
            "content": [{"type": "text",
                         "text": f"{type(e).__name__}: {e}\n{traceback.format_exc()}"}]
        }

# --- MAIN LOOP --------------------------------------------------------------
def send(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()

def serve():
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try:
            req = json.loads(line)
        except Exception as e:
            send({"jsonrpc": "2.0", "id": None,
                  "error": {"code": -32700, "message": f"parse error: {e}"}})
            continue
        rid = req.get("id")
        method = req.get("method", "")
        params = req.get("params", {})

        # Notifications (no id, no response)
        if rid is None and method.startswith("notifications/"):
            continue

        try:
            if method == "initialize":
                result = handle_initialize(params)
            elif method == "tools/list":
                result = handle_tools_list(params)
            elif method == "tools/call":
                result = handle_tools_call(params)
            else:
                send({"jsonrpc": "2.0", "id": rid,
                      "error": {"code": -32601, "message": f"unknown method: {method}"}})
                continue
            send({"jsonrpc": "2.0", "id": rid, "result": result})
        except Exception as e:
            send({"jsonrpc": "2.0", "id": rid,
                  "error": {"code": -32603, "message": str(e),
                            "data": traceback.format_exc()}})

if __name__ == "__main__":
    serve()
