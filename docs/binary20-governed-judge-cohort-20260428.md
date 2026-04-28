# Binary20 Governed Judge Cohort Replay

## Purpose

This replay is the local bridge before Qwen or RLVR. It proves Detrix can ingest the full binary20 AgentXRD judge cohort, preserve advisory score evidence, expose judge/gate disagreement, and keep training/export eligibility governed by deterministic AgentXRD PXRD gates.

## Command

```bash
uv run python scripts/demo_binary20_governed_judge_cohort.py \
  --artifact /home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_governed_judge_cohort_v0/detrix_run_artifact.json \
  --output-dir /tmp/detrix-binary20-governed-judge-cohort \
  --local
```

## Outputs

`/tmp/detrix-binary20-governed-judge-cohort/`

- `demo_summary.json`
- `trace_scores.jsonl`
- `governed_trajectories.jsonl`
- `audit_gates.jsonl`
- `export_eligibility_report.json`
- `judge_gate_disagreement_matrix.json`
- `training_route_recommendations.json`
- `binary20_governed_judge_report.md`

## Metrics

- `row_count`: 20
- `trace_count`: 20
- `score_count`: 20
- `governed_trajectory_count`: 20
- `audit_gate_count`: 20
- `sft_positive_count`: 0
- `rejected_or_eval_only_count`: 20
- `judge_gate_conflict_count`: 8
- `judge_over_promote_count`: 1
- `support_only_blocked_count`: 4
- `accept_ineligible_blocked_count`: 16
- `truth_or_provisional_blocked_count`: 5

## What Detrix Adds

Detrix is not treating Langfuse-style score evidence as export authority. The replay preserves scores, traces, terminal routes, and audit gates, then emits row-level export labels from deterministic eligibility fields. The over-promotion row remains blocked.

## Not Proven

- Live Langfuse evaluator reliability
- Qwen judge reliability
- Autonomous self-improvement
- Production AgentXRD readiness
- Support-only/public-CIF promotion
- Calibrated ACCEPT policy

## Next Step

Use this cohort as the fixed local comparison surface for optional live Langfuse import. After local-vs-live score normalization is stable, run Qwen as one judge backend and measure over-promotion rate against deterministic gates.
