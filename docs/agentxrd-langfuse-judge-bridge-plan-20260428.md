# AgentXRD Langfuse Judge Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local Detrix command that ingests AgentXRD Langfuse-style judge score evidence while preserving deterministic PXRD gate authority over training/export eligibility.

**Architecture:** Detrix reuses the existing AXV2 artifact ingestion path for governed trajectories and audit gates, then layers Langfuse score evidence preservation and judge/gate reconciliation reporting on top. The command is local-only by default, requires no Langfuse credentials, and treats live Langfuse import as optional/default-off evidence acquisition rather than an eligibility authority.

**Tech Stack:** Python stdlib argparse/json/pathlib/sqlite, pytest, existing `detrix.adapters.axv2`, `AuditLog`, `TrajectoryStore`, and `TrainingExporter`; no new dependencies.

---

## External Langfuse Contract

Use Langfuse as a scalable score source and trace-review surface only.

- LLM-as-a-Judge evaluators can produce structured scores and reasoning for observations, traces, or experiments.
- Score objects can attach to traces, observations, sessions, or dataset runs.
- Experiments/datasets can run reproducible evaluator comparisons.
- Metrics API score views can query numeric/boolean and categorical score analytics.

Sources:

- `https://langfuse.com/docs/evaluation/evaluation-methods/overview`
- `https://langfuse.com/docs/evaluation/scores/overview`
- `https://langfuse.com/docs/evaluation/experiments/overview`
- `https://langfuse.com/docs/metrics/features/metrics-api`

## Hypothesis

Langfuse LLM-as-a-Judge scores can improve trace review coverage for AgentXRD, but only become useful governed evidence when Detrix reconciles them against deterministic PXRD eligibility gates.

## Files

- Create: `scripts/demo_agentxrd_langfuse_judge_bridge.py`
- Create: `tests/test_agentxrd_langfuse_judge_bridge.py`
- Create: `docs/agentxrd-langfuse-judge-bridge-20260428.md`
- Read/reuse: `scripts/demo_agentxrd_judge_yc.py`
- Read/reuse: `src/detrix/adapters/axv2.py`
- Read/reuse: `src/detrix/improvement/exporter.py`
- Read/reuse: `tests/test_agentxrd_yc_demo.py`
- Read input artifact: `/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/agentxrd_langfuse_judge_bridge_v0/detrix_run_artifact.json`

## Command Contract

```bash
uv run python scripts/demo_agentxrd_langfuse_judge_bridge.py \
  --artifact /home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/agentxrd_langfuse_judge_bridge_v0/detrix_run_artifact.json \
  --output-dir /tmp/detrix-agentxrd-langfuse-bridge \
  --local
```

Required outputs:

- `/tmp/detrix-agentxrd-langfuse-bridge/demo_summary.json`
- `/tmp/detrix-agentxrd-langfuse-bridge/trace_scores.jsonl`
- `/tmp/detrix-agentxrd-langfuse-bridge/governed_trajectories.jsonl`
- `/tmp/detrix-agentxrd-langfuse-bridge/audit_gates.jsonl`
- `/tmp/detrix-agentxrd-langfuse-bridge/export_eligibility_report.json`
- `/tmp/detrix-agentxrd-langfuse-bridge/langfuse_judge_report.md`

## Summary Schema

`demo_summary.json` must include:

- `row_count`
- `trace_count`
- `score_count`
- `governed_trajectory_count`
- `audit_gate_count`
- `sft_positive_count`
- `rejected_or_eval_only_count`
- `judge_gate_conflict_count`
- `judge_over_promote_count`
- `support_only_blocked_count`
- `accept_ineligible_blocked_count`
- `truth_or_provisional_blocked_count`
- `strongest_claim`
- `not_proven`
- `exit_status`

## Embedded Artifact Schema

Detrix must require these AgentXRD bridge fields:

- `langfuse_score_schema_version = "agentxrd_langfuse_judge_bridge_v0.1"`
- `langfuse_score_evidence[]`, with `trace_id`, `observation_id`, `sample_id`, `score_name`, `score_value`, `score_comment`, `judge_recommendation`, `must_not_promote`, and `missing_evidence`
- `langfuse_trace_fixture[]`, with `trace_id`, `observation_id`, `sample_id`, `input`, `output`, and `metadata`
- `deterministic_gate_reconciliation.rows[]`, with `sample_id`, `classification`, `block_reasons`, and `final_training_export_label`

Langfuse score evidence must not be inserted into `gate_history`, must not set trajectory `rejection_type`, and must not alter `training_eligibility`.

## Reconciliation Classes

- `judge_agrees_block`
- `judge_requests_more_data`
- `judge_over_promotes_blocked_row`
- `deterministic_gate_blocks`
- `deterministic_gate_allows`

## Acceptance Criteria

- `uv run pytest tests/test_agentxrd_langfuse_judge_bridge.py tests/test_agentxrd_yc_demo.py tests/test_axv2_adapter.py -q` passes.
- `uv run python scripts/demo_agentxrd_langfuse_judge_bridge.py ... --local` exits 0.
- Output includes one governed trajectory and one audit gate row per AgentXRD input row.
- `trace_scores.jsonl` preserves `trace_id`, `observation_id`, `sample_id`, `score_name`, `score_value`, `score_comment`, and `judge_recommendation`.
- `judge_over_promotes_blocked_row` is counted when a high/accept-like Langfuse judge score targets a support-only, accept-ineligible, or truth-blocked row.
- A clean deterministic-PXRD-eligible fixture with a low/adverse Langfuse judge score still exports as SFT-positive, proving Langfuse scores cannot demote deterministic gate-allowed rows.
- `sft_positive_count == 0` for the unsafe demo cohort.
- Export eligibility remains determined by explicit `training_eligibility` and deterministic gates, not Langfuse score.
- `export_eligibility_report.json` includes deterministic block reasons and Langfuse score evidence.
- A clean safe fixture can still be SFT-positive, proving the bridge is not hardcoded to reject all traces.
- Local tests pass without Langfuse credentials.
- Static tests confirm the local demo script does not import/call Langfuse clients, Qwen, BGMN, Ray, benchmark launchers, or process launchers in the required local path.

## Non-Goals

- No live Langfuse managed evaluator call in the required path.
- No Langfuse credential requirement for tests or local demo.
- No Qwen reliability claim.
- No autonomous self-improvement or training run.
- No AgentXRD production readiness claim.
- No support-only/public-CIF promotion.

## Proven vs Not Proven

Proven by this plan: Detrix can ingest Langfuse-style score evidence and preserve it alongside governed AgentXRD trajectories while keeping deterministic PXRD gates authoritative for training/export eligibility.

Not proven: live Langfuse managed evaluator reliability, Qwen judge reliability, autonomous self-improvement, production AgentXRD readiness, or benchmark-grade promotion.

## YC-Safe Narrative

Langfuse provides scalable score evidence. Detrix turns those scores into governed review evidence only after AgentXRD deterministic gates reconcile provenance, support-only status, truth grade, and explicit training eligibility. High judge scores remain advisory when domain gates block the row.

## Task 1: RED Test Langfuse Score Ingest

**Files:**
- Create: `tests/test_agentxrd_langfuse_judge_bridge.py`

- [ ] **Step 1: Write failing tests**

Test these behaviors:

```python
def test_langfuse_bridge_exits_zero_and_preserves_scores(tmp_path):
    result = run_bridge(tmp_path, unsafe_artifact_with_scores())
    assert result.returncode == 0
    scores = read_jsonl(tmp_path / "demo" / "trace_scores.jsonl")
    assert scores[0]["score_value"] == 0.95
    assert scores[0]["score_comment"]

def test_judge_over_promote_is_counted_but_not_exported(tmp_path):
    summary = run_bridge_summary(tmp_path, unsafe_artifact_with_scores())
    assert summary["judge_over_promote_count"] >= 1
    assert summary["sft_positive_count"] == 0

def test_clean_safe_fixture_can_still_be_sft_positive(tmp_path):
    summary = run_bridge_summary(tmp_path, clean_artifact_with_scores())
    assert summary["sft_positive_count"] == 1

def test_low_score_cannot_demote_clean_safe_fixture(tmp_path):
    summary = run_bridge_summary(tmp_path, clean_artifact_with_low_score())
    assert summary["sft_positive_count"] == 1

def test_embedded_langfuse_score_schema_required(tmp_path):
    result = run_bridge(tmp_path, artifact_missing_langfuse_schema())
    assert result.returncode == 1
    assert "langfuse_score_schema_version" in result.stderr

def test_local_script_has_no_external_service_launchers():
    source = SCRIPT.read_text()
    assert "subprocess" not in source
    assert "Langfuse(" not in source
    assert "qwen" not in source.lower()
    assert "benchmark_e2e" not in source
```

- [ ] **Step 2: Run RED**

Run:

```bash
uv run pytest tests/test_agentxrd_langfuse_judge_bridge.py -q
```

Expected: fail because `scripts/demo_agentxrd_langfuse_judge_bridge.py` does not exist.

## Task 2: Implement Local Bridge Command

**Files:**
- Create: `scripts/demo_agentxrd_langfuse_judge_bridge.py`

- [ ] **Step 1: Implement minimal script**

Implementation requirements:

- Parse `--artifact`, `--output-dir`, `--domain`, and `--local`.
- Fail closed if `--local` is absent.
- Load AgentXRD artifact and validate `langfuse_score_evidence` plus required AXV2 fields.
- Reuse `project_to_audit_log` and `run_artifact_to_trajectories`.
- Store trajectories in output-local DBs.
- Write `trace_scores.jsonl` from artifact score evidence without mutating it.
- Write `governed_trajectories.jsonl`, `audit_gates.jsonl`, `export_eligibility_report.json`, `demo_summary.json`, and `langfuse_judge_report.md`.
- Classify judge/gate agreement per score row.
- Count high accept-like scores on blocked rows as `judge_over_promote_count`.
- Keep export labels driven by `training_eligibility` and deterministic gates.

- [ ] **Step 2: Run GREEN**

Run:

```bash
uv run pytest tests/test_agentxrd_langfuse_judge_bridge.py tests/test_agentxrd_yc_demo.py tests/test_axv2_adapter.py -q
```

Expected: pass.

## Task 3: Run Cross-Repo Bridge Demo

**Files:**
- Read: AgentXRD bridge artifact.
- Write: `/tmp/detrix-agentxrd-langfuse-bridge/`
- Create: `docs/agentxrd-langfuse-judge-bridge-20260428.md`

- [ ] **Step 1: Run Detrix bridge command**

Run:

```bash
uv run python scripts/demo_agentxrd_langfuse_judge_bridge.py \
  --artifact /home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/agentxrd_langfuse_judge_bridge_v0/detrix_run_artifact.json \
  --output-dir /tmp/detrix-agentxrd-langfuse-bridge \
  --local
```

Expected: exits 0 and writes all required outputs.

- [ ] **Step 2: Validate JSON and summary invariants**

Run:

```bash
python -m json.tool /tmp/detrix-agentxrd-langfuse-bridge/demo_summary.json >/dev/null
python -m json.tool /tmp/detrix-agentxrd-langfuse-bridge/export_eligibility_report.json >/dev/null
python - <<'PY'
import json, pathlib
s = json.loads(pathlib.Path("/tmp/detrix-agentxrd-langfuse-bridge/demo_summary.json").read_text())
assert s["row_count"] >= 5, s
assert s["trace_count"] >= s["row_count"], s
assert s["score_count"] >= s["row_count"], s
assert s["governed_trajectory_count"] == s["row_count"], s
assert s["audit_gate_count"] == s["row_count"], s
assert s["sft_positive_count"] == 0, s
assert s["rejected_or_eval_only_count"] == s["row_count"], s
print("langfuse-bridge-demo-ok", s)
PY
```

Expected: all commands exit 0.

## Task 4: Optional Live Langfuse Path Design Only

**Files:**
- Document only in `docs/agentxrd-langfuse-judge-bridge-20260428.md` unless local demo is already complete and verified.

- [ ] **Step 1: Record default-off live design**

Document:

- Required env vars: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`.
- Inputs: explicit trace-id list or AgentXRD trace tag filter.
- Output: raw score JSONL and normalized score JSONL.
- Fail-closed behavior if credentials are missing.
- Hard rule: live scores never mutate training/export eligibility.

## Task 5: Verification And Commit

**Files:**
- Add only bridge script, tests, plan/report docs.

- [ ] **Step 1: Run quality gates**

Run:

```bash
uv run pytest tests/test_agentxrd_langfuse_judge_bridge.py tests/test_agentxrd_yc_demo.py tests/test_axv2_adapter.py -q
uv run pytest tests/test_bridge.py tests/test_exporter.py tests/test_promoter.py -q
uv run ruff check .
uv run mypy src/detrix
```

Expected: all commands exit 0.

- [ ] **Step 2: Commit and push**

Use a Lore-style message with the directive: score evidence is advisory unless a domain evaluator marks it eligible. Push branch and beads data per repo AGENTS.
