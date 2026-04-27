# Aurexis Research Workbench v2.1

**Composable-measurement substrate / surface DSL + constrained authoring loop.**

This is a separate package from the Aurexis Research Simulation
Suite. The simulator is *evidence infrastructure*; this Workbench
is the local empirical place where the claim "predicates over
composed measurements can carry runtime meaning" is exercised
computationally.

v2.1 adds a surface predicate language and an authoring loop on top
of the v2.0 substrate (typed fields, primitive operator registry,
predicate compiler, runtime, vocabulary, Independence Ratio).

Authoring is no longer Python-only. A `.aurex` file expresses
candidate predicates as text; the workbench parses each block,
type-checks against the registered operators, and emits explicit
accept / reject diagnostics. Accepted candidates extend the
baseline vocabulary; the IR runner reports the delta.

## End-to-end

1. **Author** candidate predicates in a `.aurex` file (see
   `data/candidates.aurex`).
2. **Run** `python -m aurexis_workbench.cli_intake` — parses,
   type-checks, accepts/rejects, and runs the IR runner against the
   baseline vocabulary AND the baseline-extended-with-accepted
   vocabulary.
3. **Read** `reports/AUTHORING_DOSSIER.md` (parse diagnostics,
   accept/reject lists, IR before/after, per-task transitions).

## Bundled run on this checkback

The bundled `data/candidates.aurex` contains 9 candidates:

- 4 well-formed (`count_eq_8`, `count_lt_5`, `period_within_8`,
  `orientation_within_90`) — should be accepted and grow the
  vocabulary.
- 5 deliberately malformed (`bad_arity`, `bad_op_unknown`,
  `bad_type`, `bad_field`, `bad_dtype_in_expects`) — should each
  produce a distinct diagnostic.

Authoring-loop result on this checkback:

    parsed:    9
    accepted:  4
    rejected:  5
    Independence Ratio: 0.56 -> 0.78  (+0.22)

The IR delta is the empirical signal that the authoring step
actually moved the substrate's coverage. The simulator's
deliberate-block goals (ordering / adjacency / hierarchy) remain
UNCOVERED — those are honest gaps the authoring loop did not
attempt to fill, in line with the simulator's REJECT and
PROPOSAL_QUALITY_LIMIT findings.

## DSL reference

Block-level grammar:

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

DTypes: `image`, `scalar`, `int`, `bool`, `regions`, `vector`,
`label`. Numbers without a dot are `int`; with a dot, `scalar`.
Double-quoted strings are `label`. `true` / `false` are `bool`.

Diagnostics surfaced on rejection (one or more):

    TOK_UNRECOGNISED       unparseable character
    UNKNOWN_KEYWORD        line outside expects/returns/intent/body
    BAD_NAME               invalid predicate name
    EXPECTS_BAD            expects entry without `<field>:<dtype>`
    UNKNOWN_DTYPE          dtype not in the allowed set
    UNKNOWN_FIELD          body references a field not in expects
    EXPECT_RPAREN          unbalanced parentheses
    UNEXPECTED_TOKEN       token doesn't fit the grammar
    TRAILING_TOKENS        extra tokens after body expression
    BODY_MISSING           predicate has no `body` line
    RETURNS_MISSING        predicate has no `returns` line
    TYPE_ERROR             operator arity / type / unknown-op

## Install + run

    pip install -r requirements.txt
    python -m pytest tests -q                       # expect 40 passed
    python -m aurexis_workbench.cli                 # baseline IR run
    python -m aurexis_workbench.cli_intake          # v2.1 authoring loop
    python -m aurexis_workbench.cli_intake \
        --intake path/to/your.aurex                 # custom intake

The authoring CLI writes:

- `reports/authoring_dossier.json` and `AUTHORING_DOSSIER.md`
- `reports/IR_BEFORE_AFTER.md`

The baseline CLI still writes:

- `reports/independence_ratio.json` and `INDEPENDENCE_RATIO.md`
- `reports/VOCABULARY.md`
- `reports/vocabulary.json`

## What v2.1 proves that v2.0 did not

1. **Authoring without Python.** A predicate can enter the
   vocabulary through a text file. The substrate has a real
   surface, not just an AST API.
2. **Constrained accept/reject with diagnostics.** Every reject
   reason is named and located (line/col, code, message,
   predicate). Authoring is a closed loop with explicit feedback.
3. **Empirical authoring effect.** IR is reported before and
   after intake. The delta is the authoring loop's measurable
   contribution; on this checkback that delta is +0.22.

## What v2.1 is NOT claiming

- Not a final language. The DSL is intentionally compact: one
  predicate per block, a single body expression, no control flow.
- Not perception — operators remain the simulator-validated set
  plus comparators.
- Not a proof that the IR will rise on every authoring round. v2.1
  ships an example intake that does rise; arbitrary intakes can
  produce flat or even negative deltas if their candidates don't
  match runtime tasks or fail at evaluation.
- Still not an Engine, not E/D, not a runtime, not a camera app.

## Folder layout (v2.1)

    aurexis_workbench/
        __init__.py     v2.1.0
        fields.py       typed-field model (v2.0)
        operators.py    24 ops (v2.1 adds lt_int/gt_int/leq_int/geq_int)
        predicates.py   AST + type-checker + compiler (v2.0)
        runtime.py      install + evaluate + record (v2.0)
        vocabulary.py   JSON-backed vocabulary store (v2.0)
        scenarios.py    9 synthetic scenarios (v2.0)
        independence.py IR runner (v2.0)
        starter.py      starter vocab + runtime-task set (v2.0)
        cli.py          baseline IR runner (v2.0)
        dsl.py          v2.1 surface DSL parser + diagnostics
        intake.py       v2.1 candidate intake + IR before/after
        cli_intake.py   v2.1 authoring CLI
    data/
        candidates.aurex  example intake file
    tests/                 40 tests (v2.1 adds 16 dsl + intake tests)
    reports/
        INDEPENDENCE_RATIO.md          baseline IR report
        independence_ratio.json
        VOCABULARY.md
        vocabulary.json
        AUTHORING_DOSSIER.md           v2.1 authoring run
        authoring_dossier.json
        IR_BEFORE_AFTER.md             v2.1 compact delta view
        SUBSTRATE_OVERVIEW.md          layer doc
