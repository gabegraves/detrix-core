# Binary20 Governed Judge Cohort Replay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use test-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Detrix local replay command for the full binary20 governed judge cohort, preserving advisory scores while deterministic AgentXRD PXRD gates decide export eligibility.

**Architecture:** Extend the existing local Langfuse judge replay pattern with a binary20 cohort schema. Detrix accepts a Detrix-compatible AgentXRD artifact, writes trace scores, governed trajectories, audit gates, export eligibility, disagreement matrix, route recommendations, and a concise markdown report.

**Tech Stack:** Python stdlib CLI, existing `detrix.adapters.axv2`, `AuditLog`, `TrajectoryStore`, `TrainingExporter`, pytest, ruff, mypy.

---

## Files

- Create: `scripts/demo_binary20_governed_judge_cohort.py`
- Create: `tests/test_binary20_governed_judge_cohort.py`
- Create: `docs/binary20-governed-judge-cohort-20260428.md`
- Read existing: `scripts/demo_agentxrd_langfuse_judge_bridge.py`
- Read existing: `src/detrix/adapters/axv2.py`
- Read existing: `src/detrix/improvement/exporter.py`
- Input artifact: `/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_governed_judge_cohort_v0/detrix_run_artifact.json`
- Output dir: `/tmp/detrix-binary20-governed-judge-cohort/`

## Non-Goals

- No live Langfuse API calls.
- No Qwen execution.
- No GPU training, SFT, RLVR, or GRPO run.
- No benchmark/BGMN/Ray launch.
- No change to AXV2 gate precedence semantics unless tests prove a defect.

## Proven vs Not Proven

Proven if complete:
- Detrix can replay 20 AgentXRD binary20 judge-score rows locally.
- Advisory score evidence and over-promotion pressure are preserved.
- Export labels remain deterministic-gate driven.
- Row recommendations are emitted for eval-only, DPO-negative, calibration, truth audit, and possible promotion audit.

Not proven:
- Live Langfuse evaluator reliability.
- Qwen judge reliability.
- Autonomous self-improvement.
- Production AgentXRD readiness.
- Calibrated ACCEPT policy.

## Task 1: Detrix Replay Tests

**Files:**
- Create: `tests/test_binary20_governed_judge_cohort.py`
- Target implementation: `scripts/demo_binary20_governed_judge_cohort.py`

- [ ] Write a failing test that a binary20 fixture artifact exits 0 and writes `demo_summary.json`, `trace_scores.jsonl`, `governed_trajectories.jsonl`, `audit_gates.jsonl`, `export_eligibility_report.json`, `judge_gate_disagreement_matrix.json`, `training_route_recommendations.json`, and `binary20_governed_judge_report.md`.
- [ ] Write a failing test that `row_count == 20`, `governed_trajectory_count == 20`, `audit_gate_count == 20`, and `sft_positive_count == 0` for unsafe demo rows.
- [ ] Write a failing test that high `accept_like` scores on blocked rows count as over-promotion but do not produce `sft_positive`.
- [ ] Write a failing test that a clean safe fixture remains SFT-positive even if the advisory judge score is low.
- [ ] Write a failing static test that no live Langfuse/Qwen/BGMN/Ray/benchmark subprocess path exists.

Run:

```bash
cd /home/gabriel/Desktop/detrix-core
uv run pytest tests/test_binary20_governed_judge_cohort.py -q
```

Expected RED: fails because the script does not exist yet.

## Task 2: Detrix Replay CLI

**Files:**
- Create: `scripts/demo_binary20_governed_judge_cohort.py`

- [ ] Validate required artifact fields including `binary20_cohort_schema_version`, `langfuse_score_evidence`, `langfuse_trace_fixture`, `deterministic_gate_reconciliation`, `judge_gate_disagreement_matrix`, and `training_route_recommendations`.
- [ ] Reuse `project_to_audit_log`, `run_artifact_to_trajectories`, `AuditLog`, `TrajectoryStore`, and `TrainingExporter`.
- [ ] Preserve score evidence in `trace_scores.jsonl`.
- [ ] Preserve row-level deterministic reasons in `export_eligibility_report.json`.
- [ ] Write disagreement matrix and route recommendation JSON directly from the artifact.
- [ ] Write `binary20_governed_judge_report.md` answering what Detrix stored, where judge pressure appeared, and why export eligibility stayed gated.

Run:

```bash
uv run python scripts/demo_binary20_governed_judge_cohort.py \
  --artifact /home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_governed_judge_cohort_v0/detrix_run_artifact.json \
  --output-dir /tmp/detrix-binary20-governed-judge-cohort \
  --local
```

Expected GREEN: exits 0 and emits 20 governed trajectories with 0 SFT-positive rows.

## Task 3: Docs and Verification

**Files:**
- Create: `docs/binary20-governed-judge-cohort-20260428.md`

- [ ] Document inputs, outputs, metrics, disagreement matrix, route recommendations, and not-proven claims.
- [ ] Include exact local replay command.

Run:

```bash
uv run pytest tests/test_binary20_governed_judge_cohort.py tests/test_agentxrd_langfuse_judge_bridge.py tests/test_axv2_adapter.py -q
uv run pytest tests/test_bridge.py tests/test_exporter.py tests/test_promoter.py -q
uv run ruff check .
uv run mypy src/detrix
uv run python scripts/demo_binary20_governed_judge_cohort.py \
  --artifact /home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_governed_judge_cohort_v0/detrix_run_artifact.json \
  --output-dir /tmp/detrix-binary20-governed-judge-cohort \
  --local
python -m json.tool /tmp/detrix-binary20-governed-judge-cohort/demo_summary.json >/dev/null
python -m json.tool /tmp/detrix-binary20-governed-judge-cohort/export_eligibility_report.json >/dev/null
pgrep -af 'benchmark_e2e.py|BGMN|eflech|raylet|gcs_server|ray::' | rg -v 'pgrep|rg' || true
```

Acceptance:
- Tests, ruff, and mypy pass.
- Demo exits 0.
- 20 rows are represented.
- No unsafe row is SFT-positive.
- Over-promotion pressure is visible.
