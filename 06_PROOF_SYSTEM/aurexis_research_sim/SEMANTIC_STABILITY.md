# Aurexis Research Sim v0.6 - Semantic stability dossier

Per primitive: does the recovered semantic value (count, period) match the truth across capture scenarios?

Scenarios: `SIM_MILD`, `SIM_HOSTILE`

Verdicts:
- **SEMANTIC_STABLE**      all scenarios recover the truth value
- **SEMANTIC_DRIFT**       majority match, some drift
- **SEMANTIC_UNSTABLE**    majority do not match truth
- **SEMANTIC_UNRECOVERABLE** value not recovered under most scenarios

## Per-primitive semantic stability
| primitive | truth | recovered | stability_score | verdict |
|---|---|---|---|---|
| cardinality | 4 | SIM_MILD=4, SIM_HOSTILE=4 | 1.00 | **SEMANTIC_STABLE** |
| repetition | 21.333333333333332 | SIM_MILD=1, SIM_HOSTILE=1 | 0.00 | **SEMANTIC_UNSTABLE** |
