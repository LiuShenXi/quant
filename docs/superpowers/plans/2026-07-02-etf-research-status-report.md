# ETF Research Status Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a static HTML visual report summarizing the current ETF rotation research status from existing repository evidence.

**Architecture:** Create one self-contained HTML file under `research/reports/`. Use embedded CSS and SVG/CSS charts so the report opens directly from disk without a dev server or external network dependency.

**Tech Stack:** HTML, CSS, inline SVG, existing markdown/CSV/JSON research artifacts.

## Global Constraints

- Do not modify strategy, risk, paper, live, or data-generation code.
- Do not present the report as investment advice, trading permission, paper approval, QMT approval, or real-money approval.
- Use existing research artifacts only; if evidence is missing, mark it as missing.
- Main conclusion must reflect the latest ETF family disposition: `RETIRE_ETF_ROTATION_V1_FAMILY`.

---

### Task 1: Evidence Extraction

**Files:**
- Read: `research/runs/2026-07-01__etf_rotation_long_history_robustness/17_etf_rotation_v1_family_final_disposition.md`
- Read: `research/runs/2026-07-01__etf_rotation_long_history_robustness/01_data_audit_long_history.md`
- Read: `research/runs/2026-07-01__etf_rotation_long_history_robustness/02_backtest_validation_long_history.md`
- Read: `research/runs/2026-07-01__etf_rotation_long_history_robustness/03_risk_review.md`
- Read: `research/runs/2026-07-01__etf_rotation_long_history_robustness/artifacts/*.json`

**Interfaces:**
- Consumes: existing research artifacts.
- Produces: selected metrics and conclusions for the HTML report.

- [x] **Step 1: Inspect core disposition, data audit, backtest, and risk review files**

Run: `sed -n '1,260p' <file>`

Expected: files contain explicit status, metrics, and gate conclusions.

- [x] **Step 2: Inspect backtest artifact integrity**

Run: `.venv/bin/python scripts/inspect_backtest_artifacts.py research/runs/2026-07-01__etf_rotation_long_history_robustness/backtest/etf_regime_rotation_v1_long_history`

Expected: `status` is `PASS` for artifact completeness.

### Task 2: Static HTML Report

**Files:**
- Create: `research/reports/2026-07-02-etf-research-status.html`

**Interfaces:**
- Consumes: extracted metrics from Task 1.
- Produces: a standalone HTML report file.

- [ ] **Step 1: Create the report file**

Use `apply_patch` to add the HTML file with embedded styles and charts.

- [ ] **Step 2: Verify static file exists and has required sections**

Run: `test -s research/reports/2026-07-02-etf-research-status.html && rg -n "RETIRE_ETF_ROTATION_V1_FAMILY|不是投资建议|数据审查|回测审查|风控审查" research/reports/2026-07-02-etf-research-status.html`

Expected: command exits 0 and prints all required matches.

### Task 3: Visual QA

**Files:**
- Read: `research/reports/2026-07-02-etf-research-status.html`

**Interfaces:**
- Consumes: HTML report from Task 2.
- Produces: verification evidence that the file is parseable and locally viewable.

- [ ] **Step 1: Parse the HTML**

Run: `.venv/bin/python - <<'PY' ... HTMLParser ... PY`

Expected: parser exits 0 and confirms key sections exist.

- [ ] **Step 2: Open or serve locally for visual check**

Use file open or a temporary static server as needed.

Expected: report renders with visible title, status block, charts, and evidence sections.
