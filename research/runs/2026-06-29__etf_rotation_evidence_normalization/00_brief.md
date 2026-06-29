# Research Brief - ETF Rotation Evidence Normalization

Run ID: `2026-06-29__etf_rotation_evidence_normalization`
Created: 2026-06-29
Mode: research-only
Strategy ID: `etf_regime_rotation_v1`

## Objective

Normalize the existing ETF regime rotation evidence into the current research
workspace structure and define the next robustness work package.

This is not a new strategy promotion request. It is a research hygiene and
evidence packaging run.

## Why This Today

The research registry already identified two unfinished items:

- extract strategy evidence from `imported/usage_records/2026-06-26__quant_usage_record`
- normalize the existing CIO package in `runs/cio/2026-06-27`

The highest-value next step is to make `etf_regime_rotation_v1` auditable under
the new `research/runs/YYYY-MM-DD__topic` convention before adding more
strategy ideas.

## Source Evidence

- `research/imported/usage_records/2026-06-26__quant_usage_record`
- `research/runs/cio/2026-06-27`
- `config/costs/cn_etf.yaml`
- `config/risk/global.yaml`
- `src/quant/data/service.py`
- `src/quant/risk/pipeline.py`
- `src/quant/backtest/engine.py`

## Current Decision

Decision: `HOLD_FOR_ROBUSTNESS`

Default safe action: keep the strategy research-only.

Blocking issues:

- no longer-history test
- no sample split
- no cost sensitivity
- no documented universe-selection rule
- no formal risk-governor package for paper admission
- no paper observation for this strategy
- M4/QMT/live work remains blocked by repository gates
