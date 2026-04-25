# Aurexis Research Sim v0.6 - Calibration / confidence dossier

Per-family calibrated confidence state combining boundary tag
(from unlock dossier) and validation verdict (from v0.8 validation).

States: `TRUST`, `HOLD`, `DOWNGRADE`, `REJECT`, `NEED_MORE_EVIDENCE`

## Family confidence states

| family | boundary_tag | validation_verdict | confidence_state |
|---|---|---|---|
| adjacency | METRIC_GAP_ROI_INSENSITIVE | - | **NEED_MORE_EVIDENCE** |
| cardinality | PRIMITIVE_AWARE_HELPS | - | **HOLD** |
| hierarchy | METRIC_GAP_ROI_INSENSITIVE | - | **NEED_MORE_EVIDENCE** |
| ordering | PRIMITIVE_AWARE_HELPS | SUSPECT | **REJECT** |
| orientation | METRIC_GAP_ROI_INSENSITIVE | - | **NEED_MORE_EVIDENCE** |
| repetition | PRIMITIVE_AWARE_HELPS | WEAK_ROBUST | **HOLD** |
| role_zone | PRIMITIVE_AWARE_HELPS | WEAK_ROBUST | **HOLD** |
| symmetry | PRIMITIVE_AWARE_HELPS | - | **HOLD** |
