"""Phoxelis project self-audit.

Walks the project's tracking files and recent round reports, surfaces drift,
stale promises, untracked tools, and inconsistencies. Run this at the start
of every round.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CORE = ROOT / "Aurexis_Core_WORKING_20260414-1339" / "07_VISION_SUBSTRATE"
REPORTS = CORE / "reports"

CHARTER     = ROOT / "PHOXELIS_CHARTER.md"
BENCHMARKS  = ROOT / "PHOXELIS_BENCHMARKS.md"
PROMISES    = ROOT / "PHOXELIS_PROMISES.md"
TOOL_LADDER = ROOT / "PHOXELIS_TOOL_LADDER.md"


@dataclass
class Promise:
    id: str
    text: str
    opened: str
    target: str
    status: str
    track: str = ""


@dataclass
class Tool:
    name: str
    status: str
    notes: str = ""


@dataclass
class Round:
    n: int
    title: str
    file_path: str
    has_measurement: bool
    has_doc: bool


@dataclass
class AuditReport:
    timestamp: str
    n_predicates: int
    n_operators: int
    n_promises_pending: int
    n_promises_completed: int
    n_promises_abandoned: int
    n_promises_stale: int
    n_tools_active: int
    n_tools_stagnant: int
    rounds: list
    flags: list
    last_round: int


def _clean_md(s):
    s = s.strip()
    while len(s) >= 4 and s.startswith("**") and s.endswith("**"):
        s = s[2:-2].strip()
    while len(s) >= 2 and s.startswith("*") and s.endswith("*") and not s.startswith("**"):
        s = s[1:-1].strip()
    return s.strip("`").strip()


def round_id_to_int(s):
    m = re.search(r"R?(\d+)", s)
    return int(m.group(1)) if m else 0


def parse_promises(text):
    promises = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [_clean_md(c) for c in line.strip("|").split("|")]
        if len(cells) < 5:
            continue
        if cells[0].lower() in ("id", "") or all(c == "" or set(c) <= set("- ") for c in cells):
            continue
        pid = cells[0]
        if not (pid.startswith("P-") or pid.startswith("C-") or pid.startswith("X-")):
            continue
        if len(cells) >= 7:
            promises.append(Promise(
                id=pid, text=cells[1], opened=cells[2],
                track=cells[3], target=cells[4], status=cells[5].lower(),
            ))
        elif len(cells) >= 5:
            implied = "completed" if pid.startswith("C-") else ("abandoned" if pid.startswith("X-") else "pending")
            promises.append(Promise(
                id=pid, text=cells[1], opened=cells[2],
                target=cells[3], status=implied, track="",
            ))
    return promises


def parse_tools(text):
    tools = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [_clean_md(c) for c in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        if cells[0].lower().startswith("tool") or all(c == "" or set(c) <= set("- ") for c in cells):
            continue
        if cells[0] in ("", "-"):
            continue
        status_cell = ""
        for c in cells[1:]:
            cl = c.lower()
            if any(k in cl for k in ("active", "permanent", "stagnant", "scaffold", "planned")):
                status_cell = c
                break
        if not status_cell:
            continue
        tools.append(Tool(name=cells[0], status=status_cell, notes=cells[-1]))
    return tools


def find_round_docs():
    rounds = []
    if not REPORTS.exists():
        return rounds
    pat = re.compile(r"ROUND_(\d+)_")
    for md in sorted(REPORTS.glob("ROUND_*.md")):
        m = pat.match(md.name)
        if not m:
            continue
        n = int(m.group(1))
        text = md.read_text(encoding="utf-8", errors="ignore")
        has_measurement = bool(re.search(
            r"\b\d+\s*(?:bits|bytes|%|BER|frames|cells|errors|trials|predicates|images)\b",
            text))
        title = ""
        for line in text.splitlines()[:5]:
            if line.startswith("#"):
                title = line.lstrip("# ").strip()
                break
        rounds.append(Round(n=n, title=title, file_path=str(md),
                            has_measurement=has_measurement, has_doc=True))
    return rounds


def parse_predicate_count_from_charter(text):
    n_p = 0; n_o = 0
    m = re.search(r"(\d+)\s+predicates", text, re.I)
    if m: n_p = int(m.group(1))
    m = re.search(r"(\d+)\s+operators", text, re.I)
    if m: n_o = int(m.group(1))
    return n_p, n_o


def audit():
    flags = []
    for f in (CHARTER, BENCHMARKS, PROMISES, TOOL_LADDER):
        if not f.exists():
            flags.append({"severity": "FATAL",
                          "msg": f"missing scaffolding file: {f.name}"})
            return AuditReport(
                timestamp=datetime.utcnow().isoformat(timespec="seconds") + "Z",
                n_predicates=0, n_operators=0,
                n_promises_pending=0, n_promises_completed=0,
                n_promises_abandoned=0, n_promises_stale=0,
                n_tools_active=0, n_tools_stagnant=0,
                rounds=[], flags=flags, last_round=0,
            )

    charter_text = CHARTER.read_text(encoding="utf-8")
    promises_text = PROMISES.read_text(encoding="utf-8")
    tools_text = TOOL_LADDER.read_text(encoding="utf-8")

    n_pred, n_ops = parse_predicate_count_from_charter(charter_text)
    promises = parse_promises(promises_text)
    tools = parse_tools(tools_text)
    rounds = find_round_docs()

    last_round = max((r.n for r in rounds), default=0)

    n_pending = sum(1 for p in promises if p.status == "pending")
    n_done    = sum(1 for p in promises if p.status == "completed")
    n_aban    = sum(1 for p in promises if p.status == "abandoned")

    n_stale = 0
    for p in promises:
        if p.status == "pending":
            opened_n = round_id_to_int(p.opened)
            if last_round - opened_n >= 5 and opened_n > 0:
                n_stale += 1
                flags.append({"severity": "WARN",
                              "msg": f"PROMISE {p.id} pending since {p.opened} (>{last_round-opened_n} rounds): {p.text[:70]}"})

    n_active = sum(1 for t in tools
                   if "active" in t.status.lower() and "permanent" not in t.status.lower())
    n_stagnant = 0
    for t in tools:
        if "stagnant" in t.status.lower():
            n_stagnant += 1
            flags.append({"severity": "WARN", "msg": f"TOOL stagnant: {t.name}"})

    for r in rounds:
        if not r.has_measurement:
            flags.append({"severity": "INFO",
                          "msg": f"R{r.n} doc has no obvious numeric measurement (heuristic)"})

    if rounds:
        ns = sorted({r.n for r in rounds})
        for missing in range(ns[0], last_round + 1):
            if missing not in ns:
                flags.append({"severity": "INFO",
                              "msg": f"no ROUND_{missing}_*.md in reports/"})

    return AuditReport(
        timestamp=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        n_predicates=n_pred, n_operators=n_ops,
        n_promises_pending=n_pending,
        n_promises_completed=n_done,
        n_promises_abandoned=n_aban,
        n_promises_stale=n_stale,
        n_tools_active=n_active,
        n_tools_stagnant=n_stagnant,
        rounds=[asdict(r) for r in rounds],
        flags=flags,
        last_round=last_round,
    )


def render_text(report):
    L = []
    L.append("=" * 78)
    L.append(f"PHOXELIS AUDIT  -  {report.timestamp}")
    L.append("=" * 78)
    L.append("")
    L.append(f"  vocabulary:  {report.n_predicates} predicates, {report.n_operators} operators")
    L.append(f"  rounds:      {len(report.rounds)} round docs found, last = R{report.last_round}")
    L.append(f"  promises:    {report.n_promises_pending} pending, "
             f"{report.n_promises_completed} completed, "
             f"{report.n_promises_abandoned} abandoned, "
             f"{report.n_promises_stale} STALE (>5 rounds)")
    L.append(f"  tools:       {report.n_tools_active} active scaffolding, "
             f"{report.n_tools_stagnant} stagnant")
    L.append("")
    fatal = [f for f in report.flags if f["severity"] == "FATAL"]
    warn  = [f for f in report.flags if f["severity"] == "WARN"]
    info  = [f for f in report.flags if f["severity"] == "INFO"]
    L.append(f"  flags:       {len(fatal)} FATAL, {len(warn)} WARN, {len(info)} INFO")
    L.append("")
    if fatal:
        L.append("  FATAL:")
        for f in fatal: L.append(f"    {f['msg']}")
    if warn:
        L.append("  WARN:")
        for f in warn: L.append(f"    {f['msg']}")
    if info:
        L.append(f"  INFO ({len(info)} entries - first 10 shown):")
        for f in info[:10]: L.append(f"    {f['msg']}")
    L.append("")
    return "\n".join(L)


HTML_TEMPLATE = """<!doctype html>
<html><head><meta charset='utf-8'><title>Phoxelis Dashboard</title>
<style>
body{font-family:-apple-system,sans-serif;max-width:1100px;margin:2em auto;padding:0 1em;color:#222}
h1{margin-bottom:0}
.timestamp{color:#888;font-size:0.9em}
.row{display:grid;grid-template-columns:repeat(4,1fr);gap:1em;margin:1em 0}
.card{padding:1em;border:1px solid #ddd;border-radius:6px;background:#fafafa}
.card .v{font-size:2em;font-weight:bold}
.card .k{color:#666;font-size:0.9em}
table{width:100%;border-collapse:collapse;margin:1em 0}
th,td{text-align:left;padding:0.4em 0.6em;border-bottom:1px solid #eee;font-size:0.9em}
.no_measure{color:#aa6600}
.sev-FATAL{background:#fdd}
.sev-WARN{background:#ffd}
.sev-INFO{color:#666}
.headline{padding:1em;background:#eef;border-left:4px solid #66f;margin:1em 0}
</style></head>
<body>
<h1>Phoxelis Dashboard</h1>
<div class='timestamp'>audit timestamp: __TS__</div>
<div class='headline'>
<strong>Categorical first (Round 44-45):</strong> Phoxelis is the first
image-encoding system whose embedded data survives byte-exact recovery
through the standard color-grading filter set. 11/12 named Instagram
filters preserve byte-exact recovery on a 604-byte payload through a
768x768 PNG. No QR/Aztec/JAB/libcimbar can do this.
</div>
<div class='row'>
  <div class='card'><div class='v'>__NPRED__</div><div class='k'>predicates</div></div>
  <div class='card'><div class='v'>__NOPS__</div><div class='k'>operators</div></div>
  <div class='card'><div class='v'>R__LAST__</div><div class='k'>last round</div></div>
  <div class='card'><div class='v'>__NDOCS__</div><div class='k'>round docs</div></div>
</div>
<div class='row'>
  <div class='card'><div class='v'>__NPEND__</div><div class='k'>promises pending</div></div>
  <div class='card'><div class='v' style='color:__STALECOL__'>__NSTALE__</div><div class='k'>promises STALE (&gt;5 rounds)</div></div>
  <div class='card'><div class='v'>__NDONE__</div><div class='k'>promises completed</div></div>
  <div class='card'><div class='v'>__NABAN__</div><div class='k'>promises abandoned</div></div>
</div>
<div class='row'>
  <div class='card'><div class='v'>__NACTIVE__</div><div class='k'>active scaffolding</div></div>
  <div class='card'><div class='v' style='color:__STAGCOL__'>__NSTAG__</div><div class='k'>stagnant tools</div></div>
  <div class='card'><div class='v'>__NFATAL__</div><div class='k'>FATAL flags</div></div>
  <div class='card'><div class='v'>__NWARN__</div><div class='k'>WARN flags</div></div>
</div>
<h2>Recent rounds (last 30)</h2>
<table><tr><th>round</th><th>title</th><th>measurement?</th></tr>
__ROWS__
</table>
<h2>Flags</h2>
<table><tr><th>severity</th><th>message</th></tr>
__FLAGROWS__
</table>
<p style='color:#888;font-size:0.85em'>Generated by phoxelis_audit.py.</p>
</body></html>
"""


def render_dashboard_html(report):
    rounds = sorted(report.rounds, key=lambda r: r["n"])
    fatal = [f for f in report.flags if f["severity"] == "FATAL"]
    warn  = [f for f in report.flags if f["severity"] == "WARN"]
    info  = [f for f in report.flags if f["severity"] == "INFO"]

    rows_html = []
    for r in rounds[-30:]:
        cls = "ok" if r["has_measurement"] else "no_measure"
        rows_html.append(
            "<tr class='" + cls + "'><td>R" + str(r["n"]) + "</td><td>" +
            (r["title"] or "") + "</td><td>" +
            ("yes" if r["has_measurement"] else "no") + "</td></tr>")
    rows = "\n".join(rows_html)

    flag_rows_list = []
    for f in fatal + warn + info[:20]:
        flag_rows_list.append(
            "<tr class='sev-" + f["severity"] + "'><td>" + f["severity"] +
            "</td><td>" + f["msg"] + "</td></tr>")
    flag_rows = "\n".join(flag_rows_list) or "<tr><td colspan='2'><em>none</em></td></tr>"

    out = HTML_TEMPLATE
    repl = {
        "__TS__": report.timestamp,
        "__NPRED__": str(report.n_predicates),
        "__NOPS__": str(report.n_operators),
        "__LAST__": str(report.last_round),
        "__NDOCS__": str(len(rounds)),
        "__NPEND__": str(report.n_promises_pending),
        "__NSTALE__": str(report.n_promises_stale),
        "__STALECOL__": "#c00" if report.n_promises_stale else "#080",
        "__NDONE__": str(report.n_promises_completed),
        "__NABAN__": str(report.n_promises_abandoned),
        "__NACTIVE__": str(report.n_tools_active),
        "__NSTAG__": str(report.n_tools_stagnant),
        "__STAGCOL__": "#c00" if report.n_tools_stagnant else "#080",
        "__NFATAL__": str(len(fatal)),
        "__NWARN__": str(len(warn)),
        "__ROWS__": rows,
        "__FLAGROWS__": flag_rows,
    }
    for k, v in repl.items():
        out = out.replace(k, v)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--regenerate-dashboard", action="store_true")
    args = ap.parse_args(argv)

    report = audit()

    if args.json:
        print(json.dumps(asdict(report), indent=2, default=str))
    else:
        print(render_text(report))

    if args.regenerate_dashboard:
        out = ROOT / "PHOXELIS_DASHBOARD.html"
        out.write_text(render_dashboard_html(report), encoding="utf-8")
        print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
