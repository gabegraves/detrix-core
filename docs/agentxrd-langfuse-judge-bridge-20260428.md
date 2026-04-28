# AgentXRD Langfuse Judge Bridge

## Purpose

This demo proves Detrix can ingest Langfuse-style LLM-as-a-Judge score evidence for AgentXRD traces without letting those scores control training/export eligibility.

## Command

```bash
uv run python scripts/demo_agentxrd_langfuse_judge_bridge.py \
  --artifact /home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/agentxrd_langfuse_judge_bridge_v0/detrix_run_artifact.json \
  --output-dir /tmp/detrix-agentxrd-langfuse-bridge \
  --local
```

## Output Path

`/tmp/detrix-agentxrd-langfuse-bridge/`

Files:

- `demo_summary.json`
- `trace_scores.jsonl`
- `governed_trajectories.jsonl`
- `audit_gates.jsonl`
- `export_eligibility_report.json`
- `langfuse_judge_report.md`

## Metrics

- `row_count`: 5
- `trace_count`: 5
- `score_count`: 5
- `governed_trajectory_count`: 5
- `audit_gate_count`: 5
- `sft_positive_count`: 0
- `rejected_or_eval_only_count`: 5
- `support_only_blocked_count`: 1
- `accept_ineligible_blocked_count`: 3
- `truth_or_provisional_blocked_count`: 1
- `judge_gate_conflict_count`: 2
- `judge_over_promote_count`: 1

## What Is Proven

Detrix can preserve Langfuse-style score evidence and attach it to governed AgentXRD trajectories while keeping deterministic PXRD gates authoritative for training/export eligibility. A high accept-like score on a blocked row is counted as over-promotion pressure and remains rejected/eval-only.

## What Is Not Proven

- Live Langfuse managed evaluator reliability
- Qwen judge reliability
- Autonomous self-improvement
- Production AgentXRD readiness
- Support-only/public-CIF promotion
- Calibrated ACCEPT policy

## Live Langfuse Path

The live Langfuse path is not implemented in this checkpoint. The intended default-off path should require `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_HOST`, fetch only explicit AgentXRD trace IDs or an AgentXRD trace tag filter, write raw and normalized score JSONL, and never mutate deterministic training/export eligibility.

## Next Step

Build a larger AgentXRD judge-evaluation cohort over binary20 failure buckets, then add an optional Langfuse import command. Qwen/Detrix RLVR or SFT experiments should wait until after that governed cohort exists and the live import is replayable.
