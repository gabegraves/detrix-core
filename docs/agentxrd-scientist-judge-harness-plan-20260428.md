# AgentXRD Scientist Judge Harness Plan 20260428

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make detrix-core accept the AgentXRD scientist-judge demo artifact as governed trajectory evidence without allowing support-only or accept-ineligible rows into SFT/export-positive training paths.

**Architecture:** AgentXRD owns PXRD packet generation and deterministic gate truth. detrix-core owns artifact ingestion, audit projection, trajectory storage, and training/export eligibility enforcement. The AXV2 adapter must preserve explicit `training_eligibility`, `support_only`, `accept_eligible`, and truth/provenance blockers instead of inferring training status from terminal verdict alone.

**Tech Stack:** Python, Pydantic v2, pytest, SQLite `AuditLog`, SQLite `TrajectoryStore`, existing `src/detrix/adapters/axv2.py`.

---

## Hypothesis

Detrix can serve as the governed harness for AgentXRD scientist judge agents if the AXV2 adapter treats deterministic domain gate evidence as the source of training eligibility and stores judge output only as scored trajectory context.

## Demo Slice

The detrix-core side consumes:

`/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_scientist_judge_packets_v0/detrix_run_artifact.json`

The artifact contains binary20 rows representing support-only/accept-ineligible UNKNOWN, ambiguous SET, truth-blocked UNKNOWN, and candidate/refinement failed UNKNOWN.

## Success Criteria

- Local ingest command exits 0.
- `governed_trajectories` contains one row per sampled AgentXRD row.
- `step_executions` contains gate verdict JSON with deterministic evidence.
- No row with `training_eligibility.sft=false`, `support_only=true`, or `accept_eligible=false` has `rejection_type is None`.
- A clean accepted fixture in tests remains export/SFT eligible.

## Kill Criteria

- Terminal verdict alone makes a support-only or accept-ineligible row SFT-positive.
- Adapter drops `training_eligibility` evidence.
- Adapter reinterprets AgentXRD PXRD physics instead of storing AgentXRD gate evidence.
- Detrix report claims Qwen reliability or completed self-improvement.

## Tasks

### Task 1: RED Test Current Adapter Mismatch

**Files:**
- Modify: `tests/test_axv2_adapter.py`

- [ ] **Step 1: Add tests for explicit AgentXRD eligibility blockers**

Required cases:

- `training_eligibility.sft=false` with terminal verdict `SET` produces non-null `rejection_type`.
- `support_only=true` with terminal verdict `ACCEPT` produces non-null `rejection_type`.
- `accept_eligible=false` with terminal verdict `ACCEPT` produces non-null `rejection_type`.
- clean accepted fixture with `sft=true` remains `rejection_type is None`.

- [ ] **Step 2: Run RED**

Run:

```bash
uv run pytest tests/test_axv2_adapter.py -q
```

Expected: current adapter fails at least one eligibility test because it maps from terminal verdict alone.

### Task 2: Patch AXV2 Adapter

**Files:**
- Modify: `src/detrix/adapters/axv2.py`

- [ ] **Step 1: Implement smallest eligibility-aware rejection classifier**

Implementation notes:

- collect terminal `training_eligibility`
- inspect sample gate evidence for `training_eligibility`, `support_only`, `accept_eligible`, `truth_grade`, and `provisional`
- if `sft=false`, `support_only=true`, or `accept_eligible=false`, set `rejection_type` non-null
- prefer `input_quality` for missing/provisional truth or request-more-data reasons; prefer `output_quality` for unsafe judge/promotion conflict
- leave clean terminal `ACCEPT` with `sft=true` as SFT-positive

- [ ] **Step 2: Run GREEN**

Run:

```bash
uv run pytest tests/test_axv2_adapter.py -q
```

Expected: all adapter tests pass.

### Task 3: Ingest AgentXRD Artifact

**Files:**
- Read: AgentXRD `detrix_run_artifact.json`
- Write: `/tmp/agentxrd_scientist_judge_evidence.db`
- Write: `/tmp/agentxrd_scientist_judge_audit.db`

- [ ] **Step 1: Run ingest**

Run:

```bash
uv run python scripts/ingest_axv2_run.py \
  /home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_scientist_judge_packets_v0/detrix_run_artifact.json \
  --local \
  --domain xrd \
  --evidence-db /tmp/agentxrd_scientist_judge_evidence.db \
  --audit-db /tmp/agentxrd_scientist_judge_audit.db \
  --json-output
```

Expected: ingest exits 0 and prints JSON with trajectory IDs.

- [ ] **Step 2: Inspect SQLite counts**

Run:

```bash
sqlite3 /tmp/agentxrd_scientist_judge_evidence.db 'select count(*), sum(case when rejection_type is null then 1 else 0 end) from governed_trajectories;'
sqlite3 /tmp/agentxrd_scientist_judge_audit.db 'select count(*) from step_executions where gate_verdict_json is not null;'
```

Expected: trajectory count matches sampled rows; SFT-positive count is zero for support-only/accept-ineligible demo rows; gate rows are present.

### Task 4: Report And Verify

**Files:**
- Create if code changed: `docs/agentxrd-scientist-judge-demo-20260428.md`

- [ ] **Step 1: Write report**

Report must state what was proven, what was not proven, the exact ingest command, SQLite counts, and why deterministic gates are the source of training eligibility.

- [ ] **Step 2: Run repo verification**

Run:

```bash
uv run pytest tests/test_bridge.py tests/test_exporter.py tests/test_promoter.py
uv run ruff check .
uv run mypy src/detrix
```

Expected: all commands exit 0 or exact unrelated pre-existing failures are documented.

- [ ] **Step 3: Commit with Lore-style message**

Intent line: explain why Detrix now respects AgentXRD domain eligibility evidence before exporting training positives.
