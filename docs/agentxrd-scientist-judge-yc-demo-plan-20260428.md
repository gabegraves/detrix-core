# AgentXRD Scientist Judge YC Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local repeatable Detrix command that replays AgentXRD scientist-judge artifacts into governed trajectories, audit gates, export eligibility, and a concise YC demo report without external services.

**Architecture:** The script wraps the existing local AXV2 ingest path with demo-specific output contracts that `scripts/ingest_axv2_run.py` does not provide: governed trajectory JSONL, audit gate JSONL, export eligibility report, deterministic summary metrics, and a YC-readable Markdown narrative. The command is local-only by default and does not require Langfuse, Qwen, GPUs, or live bridge services.

**Tech Stack:** Python stdlib argparse/json/pathlib/sqlite via existing stores, pytest, existing `detrix.adapters.axv2`, `AuditLog`, `TrajectoryStore`, and `TrainingExporter`.

---

## Hypothesis

Detrix can serve as a governed harness for domain-specific scientist judges if AgentXRD emits deterministic PXRD evidence packets and Detrix refuses promotion/export whenever provenance, truth quality, support-only status, or explicit `training_eligibility` says the trace is unsafe.

## Files

- Create: `scripts/demo_agentxrd_judge_yc.py`
- Create: `tests/test_agentxrd_yc_demo.py`
- Create: `docs/agentxrd-scientist-judge-yc-demo-20260428.md`
- Read: `src/detrix/adapters/axv2.py`
- Read: `src/detrix/runtime/trajectory_store.py`
- Read: `src/detrix/improvement/exporter.py`
- Read source artifact: `/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/agentxrd_detrix_scientist_judge_yc_demo_v0/detrix_run_artifact.json`

## Command Contract

```bash
uv run python scripts/demo_agentxrd_judge_yc.py \
  --artifact /home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/agentxrd_detrix_scientist_judge_yc_demo_v0/detrix_run_artifact.json \
  --output-dir /tmp/detrix-agentxrd-yc-demo \
  --local
```

Required outputs:

- `/tmp/detrix-agentxrd-yc-demo/demo_summary.json`
- `/tmp/detrix-agentxrd-yc-demo/governed_trajectories.jsonl`
- `/tmp/detrix-agentxrd-yc-demo/audit_gates.jsonl`
- `/tmp/detrix-agentxrd-yc-demo/export_eligibility_report.json`
- `/tmp/detrix-agentxrd-yc-demo/yc_demo_report.md`

## Seven Report Questions

`yc_demo_report.md` must answer these headings verbatim:

1. What did AgentXRD produce?
2. What did the judge recommend?
3. What did deterministic gates allow/block?
4. What did Detrix store?
5. What was export/training eligibility?
6. Why is this not generic trace logging?
7. What remains before Qwen/Langfuse/self-improvement claims?

## Acceptance Criteria

- AgentXRD build command has produced `/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/agentxrd_detrix_scientist_judge_yc_demo_v0/detrix_run_artifact.json`; the Detrix script must fail fast with a clear message if it is missing.
- Demo script exits 0 on the AgentXRD YC artifact.
- `row_count >= 5`.
- `governed_trajectory_count == row_count`.
- `audit_gate_count == row_count`.
- `sft_positive_count == 0` for the unsafe demo rows.
- `support_only`, `accept_eligible=false`, truth/provisional-blocked, and `training_eligibility.sft=false` rows remain rejected/eval-only.
- Deterministic gate conflicts are counted and visible.
- Summary includes `not_proven` entries for Qwen judge reliability, live Langfuse ingestion, autonomous self-improvement, AgentXRD production readiness, support-only/public-CIF promotion, and calibrated ACCEPT policy.
- A clean accepted fixture still exports as SFT-positive, proving the adapter does not reject all AgentXRD traces. The fixture must have `support_only=false`, `accept_eligible=true`, non-provisional truth flags, no truth blockers, deterministic gate `passed/continue`, and `training_eligibility.sft=true`.

## Non-Goals

- No live Langfuse import.
- No Qwen execution or training.
- No GPU training, SFT, DPO, GRPO, or RLVR experiment.
- No claim that trace logging alone is proof.
- No change to AgentXRD scientific verdict logic.

## YC-Safe Narrative

AgentXRD produces hard-domain evidence packets and advisory scientist-judge review. Detrix ingests the trace only as governed evidence, then deterministic PXRD gates decide whether it is SFT-positive, DPO-negative, GRPO-candidate, or eval-only. Unsafe support-only, accept-ineligible, and truth/provisional rows remain blocked even if the judge text sounds plausible.

## Task 1: RED Test Demo Script Outputs

**Files:**
- Create: `tests/test_agentxrd_yc_demo.py`
- Create fixture: `tests/fixtures/axv2/agentxrd_yc_demo_artifact.json`

- [ ] **Step 1: Write failing tests**

Test cases must assert all required output files, one governed trajectory per input row, one audit gate row per input row, exact per-row rejection/export reasons, required `not_proven` entries, visible deterministic conflict counts, and the seven Markdown headings.

```python
def test_demo_script_exits_zero_and_writes_reports(tmp_path):
    result = subprocess.run([...], check=False)
    assert result.returncode == 0
    assert (tmp_path / "demo_summary.json").exists()
    assert (tmp_path / "yc_demo_report.md").read_text()

def test_demo_summary_blocks_unsafe_agentxrd_rows(tmp_path):
    summary = run_demo(tmp_path)
    assert summary["row_count"] >= 5
    assert summary["governed_trajectory_count"] == summary["row_count"]
    assert summary["audit_gate_count"] == summary["row_count"]
    assert summary["sft_positive_count"] == 0

def test_clean_reference_fixture_can_still_be_sft_positive(tmp_path):
    summary = run_demo(tmp_path, artifact=CLEAN_FIXTURE)
    assert summary["sft_positive_count"] == 1
```

- [ ] **Step 2: Run RED**

Run:

```bash
uv run pytest tests/test_agentxrd_yc_demo.py -q
```

Expected: fail because `scripts/demo_agentxrd_judge_yc.py` does not exist.

## Task 2: Implement Local Replay Command

**Files:**
- Create: `scripts/demo_agentxrd_judge_yc.py`

- [ ] **Step 1: Implement minimal script**

Implementation requirements:

- Parse `--artifact`, `--output-dir`, `--domain`, and `--local`.
- Load artifact and validate required fields.
- Project audit rows via `project_to_audit_log`.
- Convert trajectories via `run_artifact_to_trajectories`.
- Store trajectories in a fresh output-local evidence DB.
- Emit `governed_trajectories.jsonl` from trajectory model JSON.
- Emit `audit_gates.jsonl` by reading audit `step_executions` rows where gate verdict JSON exists.
- Export SFT and GRPO rows to temp/output files only to count positives; do not claim training happened.
- Emit `export_eligibility_report.json` with one row per trajectory and explicit rejection reason.
- Emit `demo_summary.json` with the required metrics.
- Emit `yc_demo_report.md` answering the seven required questions.

- [ ] **Step 2: Run GREEN**

Run:

```bash
uv run pytest tests/test_agentxrd_yc_demo.py tests/test_axv2_adapter.py -q
```

Expected: pass.

## Task 3: Run Cross-Repo Demo

**Files:**
- Read: AgentXRD output artifact.
- Write: `/tmp/detrix-agentxrd-yc-demo/`
- Create: `docs/agentxrd-scientist-judge-yc-demo-20260428.md`

- [ ] **Step 1: Build or refresh AgentXRD artifact first**

Run from AgentXRD:

```bash
PYTHONPATH=src python scripts/build_agentxrd_detrix_yc_demo_artifact_v0.py \
  --source-dir outputs/diagnostics/binary20_scientist_judge_packets_v0 \
  --output-dir outputs/diagnostics/agentxrd_detrix_scientist_judge_yc_demo_v0
```

Expected: artifact exists at the path consumed by Detrix.

- [ ] **Step 2: Run Detrix demo command**

Run:

```bash
uv run python scripts/demo_agentxrd_judge_yc.py \
  --artifact /home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/agentxrd_detrix_scientist_judge_yc_demo_v0/detrix_run_artifact.json \
  --output-dir /tmp/detrix-agentxrd-yc-demo \
  --local
```

Expected: exits 0 and writes all required outputs.

- [ ] **Step 3: Validate JSON**

Run:

```bash
python -m json.tool /tmp/detrix-agentxrd-yc-demo/demo_summary.json >/dev/null
python -m json.tool /tmp/detrix-agentxrd-yc-demo/export_eligibility_report.json >/dev/null
```

Expected: both commands exit 0.

## Task 4: Verification And Commit

**Files:**
- Add only `scripts/demo_agentxrd_judge_yc.py`, `tests/test_agentxrd_yc_demo.py`, fixture files, and YC plan/report docs.

- [ ] **Step 1: Run quality gates**

Run:

```bash
uv run pytest tests/test_agentxrd_yc_demo.py tests/test_axv2_adapter.py -q
uv run pytest tests/test_bridge.py tests/test_exporter.py tests/test_promoter.py -q
uv run ruff check .
uv run mypy src/detrix
```

Expected: all commands exit 0.

- [ ] **Step 2: Commit**

Use a Lore-style message with the directive: explicit `training_eligibility` and domain gate outcomes stay authoritative over terminal verdict fallback.
