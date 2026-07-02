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
    YYYY-MM-DDTHHMM__topic/
  datasets/
  imported/
    usage_records/
  scratch/
  archive/
```

## How I Will Use This Workspace

- `runs/` is the default home for every non-trivial research task.
- `registries/` contains long-lived ledgers across all runs.
- `templates/` contains the required evidence package format.
- `datasets/` stores reusable research data snapshots or dataset manifests.
- `imported/` stores true external, historical, or temporarily unnormalized material.
- `imported/usage_records/` stores historical usage logs and their attached raw
  artifacts. These records are source material, not formal research runs.
- `scratch/` is temporary research work that is not evidence until promoted into a run.
- `archive/` stores retired or superseded packages.
- Strategies are linked through run metadata and registries, not used as the
  primary physical directory boundary. A single run may involve one strategy,
  several related strategies, baselines, shared datasets, or portfolio-level
  questions.

## Research Run Format

Every non-trivial strategy, cross-strategy, dataset, robustness, or portfolio
investigation gets its own run folder:

```text
research/runs/YYYY-MM-DDTHHMM__strategy_or_topic/
  run.yaml
  00_brief.md
  01_thesis.md
  02_data_requirements.md
  03_experiment_plan.md
  04_data_audit.md
  05_backtest_validation.md
  06_risk_review.md
  07_decision_record.md
  08_paper_observation.md
  09_cio_decision_package.md
  agents/
    thesis/
    data_requirements/
    experiment_plan/
    data_audit/
    backtest_validation/
    risk_review/
    cio_synthesis/
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

## Starting A Static Research Run

For a new opening research package, create a run folder and copy the static
template pack:

```bash
mkdir -p research/runs/YYYY-MM-DDTHHMM__short_topic
cp research/templates/run.yaml research/runs/YYYY-MM-DDTHHMM__short_topic/
cp research/templates/00_brief.md research/runs/YYYY-MM-DDTHHMM__short_topic/
cp research/templates/01_thesis.md research/runs/YYYY-MM-DDTHHMM__short_topic/
cp research/templates/02_data_requirements.md research/runs/YYYY-MM-DDTHHMM__short_topic/
cp research/templates/03_experiment_plan.md research/runs/YYYY-MM-DDTHHMM__short_topic/
cp research/templates/07_decision_record.md research/runs/YYYY-MM-DDTHHMM__short_topic/
```

Fill `run.yaml` before editing the Markdown files. A run can stay at
`THESIS_DRAFT` with only the opening pack completed. Formal `data_audit`,
`backtest_validation`, `risk_review`, `paper_observation`, and
`cio_decision_package` records are added only when those gates are actually
reviewed.

## Research Run Metadata

Each new multi-agent or non-trivial run should include `run.yaml` so the run can
be queried by strategy, evidence type, decision, agent, and parent run without
duplicating files into strategy-specific folders.

```yaml
run_id: 2026-07-01T1030__etf_rotation_robustness
research_type: single_strategy
related_strategies:
  - etf_regime_rotation_v1
agents:
  - strategy-thesis-tracker
  - data-audit-reviewer
  - backtest-validator
status: research-only
parent_runs:
  - 2026-06-29__etf_rotation_evidence_normalization
decision: HOLD_FOR_ROBUSTNESS
default_safe_action: keep research-only
```

For cross-strategy, benchmark, dataset, robustness, or portfolio research,
set `research_type` accordingly and list every related strategy or baseline.

## Naming Rules

- New run folders prefer `YYYY-MM-DDTHHMM__short_slug` so parallel agents do not
  collide on the same date. Existing `YYYY-MM-DD__short_slug` folders remain
  valid historical runs.
- Strategy slugs use lowercase English identifiers, for example
  `etf_regime_rotation_v1`.
- Artifact folders include the strategy slug, run ID, or evidence type when
  possible.
- Strategy-specific lookup belongs in `registries/strategy_registry.md`;
  evidence-specific lookup belongs in `registries/evidence_inventory.md`;
  decision history belongs in `registries/decision_log.md`.
- Do not store real credentials, account identifiers, broker tokens, or live
  overlays here.

## Current Imported Records

- `imported/usage_records/2026-06-26__quant_usage_record/`: early quant usage
  record moved from the old top-level folder. It is kept as historical source
  material because it is primarily a usage record, not a formal research run.
- `runs/cio/2026-06-27/`: existing CIO research package.
