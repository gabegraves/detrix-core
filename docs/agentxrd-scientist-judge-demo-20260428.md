# AgentXRD Scientist Judge Harness Demo

Date: 2026-04-28

## Purpose

This document records the Detrix side of
`agentxrd_detrix_scientist_judge_demo_v0`.

The demo proves a narrow governance harness claim: Detrix can ingest and store
AgentXRD scientist-judge trajectories only after deterministic PXRD gates score
support/provenance status, truth quality, and training eligibility.

Detrix does not perform PXRD physics. AgentXRD remains the domain truth source.

## Input Artifact

AgentXRD emits:

`/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_scientist_judge_packets_v0/detrix_run_artifact.json`

The artifact includes:

- `run_id`
- `workflow_name=agentxrd_detrix_scientist_judge_demo_v0`
- `gate_history`
- `terminal_routes`
- `sample_prompts`
- explicit `training_eligibility` under gate evidence and terminal routes

The five-row slice intentionally includes no SFT-positive examples. It covers
support-only, ambiguous SET, truth-blocked, and candidate/refinement-failed
rows.

## Detrix Adapter Requirement

The key adapter rule is that training/export admission cannot be inferred from
terminal verdict alone.

Terminal `SET` or `ACCEPT`-like rows can still be rejected when explicit domain
evidence says:

- `support_only=true`
- `accept_eligible=false`
- provisional or truth-blocked row
- `training_eligibility.sft=false`

The adapter now checks explicit training and provenance fields before falling
back to terminal verdict.

## Local Ingest Evidence

Command:

```bash
uv run python scripts/ingest_axv2_run.py \
  /home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_scientist_judge_packets_v0/detrix_run_artifact.json \
  --local \
  --domain xrd \
  --evidence-db /tmp/agentxrd_scientist_judge_evidence.db \
  --audit-db /tmp/agentxrd_scientist_judge_audit.db \
  --json-output
```

Observed checks:

- `trajectory_count=5`
- `sft_positive_count=0`
- `audit_gate_rows=5`

Representative trajectory routing:

- `dara_Bi2O3-2MoO3_400C_60min`: `UNKNOWN`, rejected for support-only evidence
- `dara_CoO-ZnO_1100C_60min`: `SET`, rejected because `accept_eligible=false`
- `dara_CaCO3-NH4H2PO4_200C_60min`: `REQUEST_MORE_DATA`, rejected for
  truth/provisional blockage
- `dara_GeO2-ZnO_700C_60min`: `UNKNOWN`, rejected for failed candidate evidence
- `dara_2Fe3O4-3Y2O3_1000C_60min`: `UNKNOWN`, rejected because
  `accept_eligible=false`

## Why This Is YC-Relevant

This is the minimum credible Detrix proof:

- governed trajectory storage
- domain evaluator output preserved
- support-only and accept-ineligible rows blocked
- training eligibility explicit and auditable
- audit trail stored locally
- improvement loop ready for Langfuse and future training/export surfaces

The result is not a generic trace collector. It shows why deterministic domain
gates are required before LLM/agent traces can become reliable improvement
signal.

## Not Proven

- Detrix has not completed autonomous self-improvement.
- Qwen 3.6 has not been trained or validated.
- AgentXRD binary20 diagnostic recovery is not production-ready.
- Support-only or accept-ineligible rows are not positive training data.
- Trace volume alone is not scientific progress.
