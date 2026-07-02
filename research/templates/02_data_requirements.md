# Data Requirements

Status: DRAFT
Run ID:
Strategy ID:
Intended mode: research-only

## Intended Use

Describe whether this data is needed for thesis review, data audit, exploratory
research, formal backtest validation, benchmark comparison, or paper observation
planning.

## Required Datasets

| Dataset | Symbols | Frequency | Required fields | Source | Date range | Calendar | Adjustment | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bars |  |  | open, high, low, close, volume, timestamp |  |  |  |  | NOT_STARTED |
| instruments |  | n/a | symbol, name, exchange, start, end |  |  | n/a | n/a | NOT_STARTED |
| calendar |  | n/a | session, open, close, timezone |  |  |  | n/a | NOT_STARTED |
| adjustment_factors |  | n/a | symbol, date, factor |  |  |  |  | NOT_STARTED |

## Quality Requirements

- Data source must be named and reproducible.
- Timestamps must be timezone-aware or have a documented timezone.
- Missing, duplicate, stale, or future bars must be measurable.
- Calendar and adjustment assumptions must match the strategy frequency.
- Survivorship, delisting, corporate action, and quote-currency assumptions must
  be explicit when relevant.

## Reproducibility Requirements

Data snapshot path:
Dataset manifest path:
Build command:
Provider version or retrieval date:
Hash or row counts:

## Known Gaps

- No dataset is approved until data audit is complete.

## Data Audit Handoff

Data audit owner:
Audit template:
Expected audit output: `PASS`, `PASS_WITH_WARNINGS`, or `FAIL`
Next action:
