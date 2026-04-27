"""Surface DSL for predicate authoring.

A small, deliberately compact textual language over the predicate
substrate. Goals:

  - You can hand-write a candidate predicate without touching Python.
  - The parser produces the same AST the v2.0 substrate already
    type-checks, compiles, and runs.
  - Parse / type-check failures surface as readable diagnostics so
    the authoring loop can reject bad predicates with a reason.

Block-level grammar (one predicate per block, blank line between):

    predicate <NAME>
      expects <FIELD>:<DTYPE>[, <FIELD>:<DTYPE> ...]
      returns <DTYPE>
      intent  <IDENT_OR_QUOTED>
      body    <EXPR>

Expression grammar:

    expr      := call | const | field_ref
    call      := IDENT "(" arglist? ")"
    arglist   := expr ("," expr)*
    const     := NUMBER_INT | NUMBER_FLOAT | STRING | BOOL
    field_ref := IDENT      (only valid if IDENT is in expects)

Numbers: an INTEGER literal (no dot) is dtype `int`; a FLOAT literal
(with dot) is dtype `scalar`. Strings (double-quoted) are dtype
`label`. `true` / `false` are dtype `bool`.

Comments: lines beginning with `#` are ignored.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from . import predicates as P
from .fields import VALID_DTYPES


# ----- diagnostics --------------------------------------------------

@dataclass
class Diagnostic:
    line: int
    col: int
    code: str
    message: str
    predicate: Optional[str] = None

    def render(self) -> str:
        loc = "L" + str(self.line) + ":C" + str(self.col)
        nm = (" [" + self.predicate + "]") if self.predicate else ""
        return loc + nm + " " + self.code + ": " + self.message


class ParseError(Exception):
    def __init__(self, diag: Diagnostic):
        super().__init__(diag.render())
        self.diag = diag


# ----- tokenizer (expression-level only) ----------------------------

_TOKEN_RE = re.compile(
    r"""
    \s+                                  # whitespace
    | \#[^\n]*                            # line comment
    | (?P<LPAREN>\()
    | (?P<RPAREN>\))
    | (?P<COMMA>,)
    | (?P<FLOAT>-?\d+\.\d+)
    | (?P<INT>-?\d+)
    | (?P<STRING>"(?:[^"\\]|\\.)*")
    | (?P<IDENT>[A-Za-z_][A-Za-z_0-9]*)
    """,
    re.VERBOSE,
)


def _tokenize(source: str, line_no: int):
    """Tokenize a single body expression line."""
    pos = 0
    out: List[Tuple[str, str, int]] = []
    while pos < len(source):
        m = _TOKEN_RE.match(source, pos)
        if not m:
            raise ParseError(Diagnostic(
                line=line_no, col=pos + 1,
                code="TOK_UNRECOGNISED",
                message="unrecognised character: " + repr(source[pos])))
        if m.lastgroup is None:
            pos = m.end()
            continue
        out.append((m.lastgroup, m.group(m.lastgroup), pos + 1))
        pos = m.end()
    out.append(("EOF", "", pos + 1))
    return out


# ----- expression parser --------------------------------------------

class _Cursor:
    def __init__(self, tokens, line_no):
        self.tokens = tokens
        self.i = 0
        self.line = line_no

    def peek(self):
        return self.tokens[self.i]

    def take(self):
        t = self.tokens[self.i]
        self.i += 1
        return t

    def match(self, kind):
        if self.peek()[0] == kind:
            return self.take()
        return None

    def expect(self, kind, code, msg):
        t = self.match(kind)
        if t is None:
            actual = self.peek()
            raise ParseError(Diagnostic(
                line=self.line, col=actual[2], code=code,
                message=msg + " (got " + actual[0] + ")"))
        return t


def _parse_expr(cur: _Cursor, expects: Dict[str, str]):
    tok = cur.peek()
    if tok[0] == "INT":
        cur.take()
        return P.Const(value=int(tok[1]), dtype="int")
    if tok[0] == "FLOAT":
        cur.take()
        return P.Const(value=float(tok[1]), dtype="scalar")
    if tok[0] == "STRING":
        cur.take()
        # strip enclosing quotes and unescape
        raw = tok[1][1:-1]
        # very small unescape: \", \\, \n
        raw = raw.replace("\\\"", "\"").replace("\\\\", "\\").replace("\\n", "\n")
        return P.Const(value=raw, dtype="label")
    if tok[0] == "IDENT":
        if tok[1] == "true":
            cur.take(); return P.Const(value=True, dtype="bool")
        if tok[1] == "false":
            cur.take(); return P.Const(value=False, dtype="bool")
        # IDENT — call vs field_ref decided by lookahead
        ident = cur.take()
        if cur.peek()[0] == "LPAREN":
            cur.take()  # consume (
            args = []
            if cur.peek()[0] != "RPAREN":
                args.append(_parse_expr(cur, expects))
                while cur.peek()[0] == "COMMA":
                    cur.take()
                    args.append(_parse_expr(cur, expects))
            cur.expect("RPAREN", "EXPECT_RPAREN",
                          "expected ')' to close call to '" + ident[1] + "'")
            return P.Call(op=ident[1], args=args)
        # field_ref
        if ident[1] not in expects:
            raise ParseError(Diagnostic(
                line=cur.line, col=ident[2],
                code="UNKNOWN_FIELD",
                message="field '" + ident[1]
                          + "' is not declared in 'expects' "
                          + "(declared: "
                          + ", ".join(sorted(expects.keys())) + ")"))
        return P.FieldRef(name=ident[1])
    raise ParseError(Diagnostic(
        line=cur.line, col=tok[2],
        code="UNEXPECTED_TOKEN",
        message="unexpected token: " + tok[0] + " " + repr(tok[1])))


# ----- block-level parser ------------------------------------------

@dataclass
class ParsedPredicate:
    pred: Optional[P.Predicate]
    diagnostics: List[Diagnostic] = field(default_factory=list)
    source_block: str = ""
    name: str = ""

    @property
    def ok(self) -> bool:
        return self.pred is not None and not self.diagnostics


def _strip_comment(line: str) -> str:
    # remove comment but preserve string literals
    out = []
    i = 0
    in_str = False
    while i < len(line):
        c = line[i]
        if c == "\"":
            in_str = not in_str
            out.append(c)
        elif c == "#" and not in_str:
            break
        else:
            out.append(c)
        i += 1
    return "".join(out).rstrip()


def parse_source(text: str) -> List[ParsedPredicate]:
    """Parse a candidate-intake source. Returns one ParsedPredicate
    per `predicate ...` block, regardless of success."""
    lines = text.split("\n")
    n = len(lines)
    results: List[ParsedPredicate] = []
    i = 0
    while i < n:
        raw = lines[i]
        cleaned = _strip_comment(raw).strip()
        if not cleaned:
            i += 1; continue
        if cleaned.startswith("predicate "):
            block_start = i
            name = cleaned[len("predicate "):].strip()
            block_lines = [(i, raw)]
            i += 1
            # gather indented continuation lines (any lines that
            # aren't a new predicate or blank-after-content)
            while i < n:
                rl = lines[i]
                cl = _strip_comment(rl).strip()
                if not cl:
                    i += 1
                    # blank line ends block only if we had at least
                    # one continuation line collected. But to keep
                    # parsing forgiving, blank-after-block content
                    # ends the block.
                    break
                if cl.startswith("predicate "):
                    break
                block_lines.append((i, rl))
                i += 1
            results.append(_parse_block(name, block_lines))
        else:
            # stray text outside a predicate block
            results.append(ParsedPredicate(
                pred=None,
                diagnostics=[Diagnostic(
                    line=i + 1, col=1, code="STRAY",
                    message="text outside a predicate block: "
                              + repr(cleaned[:40]))],
                source_block=raw, name=""))
            i += 1
    return results


def _parse_block(name: str,
                   block_lines: List[Tuple[int, str]]) -> ParsedPredicate:
    """Parse one `predicate NAME ...` block."""
    diags: List[Diagnostic] = []
    expects: Dict[str, str] = {}
    returns: Optional[str] = None
    intent: str = ""
    body_text: str = ""
    body_line: int = block_lines[0][0] + 1
    block_src = "\n".join(rl for _, rl in block_lines)

    if not name or " " in name:
        diags.append(Diagnostic(
            line=block_lines[0][0] + 1, col=1, code="BAD_NAME",
            message="invalid predicate name: " + repr(name),
            predicate=name or "?"))

    for (ln, raw) in block_lines[1:]:
        cleaned = _strip_comment(raw).strip()
        if not cleaned:
            continue
        if cleaned.startswith("expects "):
            decl = cleaned[len("expects "):].strip()
            for part in decl.split(","):
                part = part.strip()
                if not part:
                    continue
                if ":" not in part:
                    diags.append(Diagnostic(
                        line=ln + 1, col=1, code="EXPECTS_BAD",
                        message="expected '<field>:<dtype>', got: "
                                  + repr(part), predicate=name))
                    continue
                fn, dt = part.split(":", 1)
                fn = fn.strip(); dt = dt.strip()
                if dt not in VALID_DTYPES:
                    diags.append(Diagnostic(
                        line=ln + 1, col=1, code="UNKNOWN_DTYPE",
                        message="unknown dtype: " + repr(dt),
                        predicate=name))
                    continue
                expects[fn] = dt
        elif cleaned.startswith("returns "):
            v = cleaned[len("returns "):].strip()
            if v not in VALID_DTYPES:
                diags.append(Diagnostic(
                    line=ln + 1, col=1, code="UNKNOWN_DTYPE",
                    message="unknown return dtype: " + repr(v),
                    predicate=name))
            else:
                returns = v
        elif cleaned.startswith("intent "):
            intent = cleaned[len("intent "):].strip()
            if intent.startswith("\"") and intent.endswith("\""):
                intent = intent[1:-1]
        elif cleaned.startswith("body "):
            body_text = cleaned[len("body "):].strip()
            body_line = ln + 1
        else:
            diags.append(Diagnostic(
                line=ln + 1, col=1, code="UNKNOWN_KEYWORD",
                message="expected expects/returns/intent/body, got: "
                          + repr(cleaned[:40]), predicate=name))

    if not body_text:
        diags.append(Diagnostic(
            line=block_lines[0][0] + 1, col=1, code="BODY_MISSING",
            message="predicate has no 'body' line", predicate=name))

    if returns is None:
        diags.append(Diagnostic(
            line=block_lines[0][0] + 1, col=1, code="RETURNS_MISSING",
            message="predicate has no 'returns' line", predicate=name))

    if diags:
        return ParsedPredicate(pred=None, diagnostics=diags,
                                 source_block=block_src, name=name)

    # Expression parse
    try:
        tokens = _tokenize(body_text, body_line)
        cur = _Cursor(tokens, body_line)
        ast = _parse_expr(cur, expects)
        # leftovers?
        if cur.peek()[0] != "EOF":
            t = cur.peek()
            diags.append(Diagnostic(
                line=body_line, col=t[2], code="TRAILING_TOKENS",
                message="trailing tokens after body expression",
                predicate=name))
            return ParsedPredicate(pred=None, diagnostics=diags,
                                     source_block=block_src, name=name)
    except ParseError as pe:
        d = pe.diag
        d.predicate = name
        return ParsedPredicate(pred=None, diagnostics=[d],
                                 source_block=block_src, name=name)

    pred = P.Predicate(
        name=name, body=ast, expects=expects,
        intent=intent or name,
        return_type=returns,
        source="surface_dsl",
    )
    # Type-check
    try:
        P.type_check(pred)
    except (P.TypeError_, KeyError) as te:
        diags.append(Diagnostic(
            line=body_line, col=1, code="TYPE_ERROR",
            message=str(te), predicate=name))
        return ParsedPredicate(pred=None, diagnostics=diags,
                                 source_block=block_src, name=name)

    return ParsedPredicate(pred=pred, diagnostics=[],
                             source_block=block_src, name=name)
