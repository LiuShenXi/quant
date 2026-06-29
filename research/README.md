# Quant Research Workspace

This directory is the canonical workspace for quant research outputs.

Research here is evidence packaging, not trading permission. A strategy remains
research-only unless it passes the required thesis, data, backtest, risk, and
paper/live gates defined by the repository constitution.

## Directory Layout

```text
research/
  README.md
  INDEX.md
  registries/
    strategy_registry.md
    decision_log.md
    evidence_inventory.md
  templates/
  runs/
    YYYY-MM-DD__topic/
  datasets/
  imported/
    usage_records/
  scratch/
  archive/
```

## How I Will Use This Workspace

- `runs/` is the default home for every new research run.
- `registries/` contains long-lived ledgers across all runs.
- `templates/` contains the required evidence package format.
- `datasets/` stores reusable research data snapshots or dataset manifests.
- `imported/` stores true external, historical, or temporarily unnormalized material.
- `imported/usage_records/` stores historical usage logs and their attached raw
  artifacts. These records are source material, not formal research runs.
- `scratch/` is temporary research work that is not evidence until promoted into a run.
- `archive/` stores retired or superseded packages.

## Research Run Format

Every non-trivial strategy investigation gets its own run folder:

```text
research/runs/YYYY-MM-DD__strategy_or_topic/
  00_brief.md
  01_thesis.md
  02_data_audit.md
  03_backtest_validation.md
  04_risk_review.md
  05_paper_observation.md
  06_cio_decision_package.md
  artifacts/
  logs/
  refs/
```

The stage files follow the promotion order:

```text
idea
-> strategy thesis
-> data audit
-> backtest validation
-> risk review
-> paper observation
-> paper/live gate
-> human decision
```

If evidence is missing, the default decision is to keep the strategy in research.

## Naming Rules

- Run folders use `YYYY-MM-DD__short_slug`.
- Strategy slugs use lowercase English identifiers, for example
  `etf_regime_rotation_v1`.
- Artifact folders include the strategy slug and run date when possible.
- Do not store real credentials, account identifiers, broker tokens, or live
  overlays here.

## Current Imported Records

- `imported/usage_records/2026-06-26__quant_usage_record/`: early quant usage
  record moved from the old top-level folder. It is kept as historical source
  material because it is primarily a usage record, not a formal research run.
- `runs/cio/2026-06-27/`: existing CIO research package.
