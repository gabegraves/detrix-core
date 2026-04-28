# AgentXRD Scientist Judge YC Demo

Date: 2026-04-28

## Purpose

This records the Detrix side of
`agentxrd_detrix_scientist_judge_yc_demo_v0`.

The demo proves a narrow governance claim: Detrix can replay local AgentXRD
scientist-judge artifacts into governed trajectories only after deterministic
PXRD gates expose support/provenance status, truth quality, and training/export
eligibility.

## Command

```bash
uv run python scripts/demo_agentxrd_judge_yc.py \
  --artifact /home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/agentxrd_detrix_scientist_judge_yc_demo_v0/detrix_run_artifact.json \
  --output-dir /tmp/detrix-agentxrd-yc-demo \
  --local
```

## Outputs

`/tmp/detrix-agentxrd-yc-demo/`

- `demo_summary.json`
- `governed_trajectories.jsonl`
- `audit_gates.jsonl`
- `export_eligibility_report.json`
- `yc_demo_report.md`
- local `evidence.db` and `audit.db`

## Observed Metrics

- row_count: 5
- governed_trajectory_count: 5
- audit_gate_count: 5
- sft_positive_count: 0
- rejected_or_eval_only_count: 5
- support_only_blocked_count: 1
- accept_ineligible_blocked_count: 3
- truth_or_provisional_blocked_count: 1
- deterministic_gate_conflict_count: 0

## Why This Is Not Generic Trace Logging

The command does not just store traces. It writes governed trajectories,
audit-gate rows, per-row export eligibility, and a concise report showing why
unsafe rows stay rejected or eval-only. Explicit `training_eligibility`,
`support_only`, `accept_eligible`, and truth/provisional fields stay
authoritative over terminal verdict fallback.

## Strongest Legitimate Claim

Detrix now has a replayable local demo proving that AgentXRD scientist-judge
traces become governed trajectories only after explicit deterministic PXRD
eligibility gates decide whether they are training/export eligible. Unsafe
support-only, accept-ineligible, and truth/provisional rows remain
blocked/eval-only even if judge text looks plausible.

## Not Proven

- Qwen judge reliability
- live Langfuse ingestion
- autonomous self-improvement
- AgentXRD production readiness
- support-only/public-CIF promotion
- calibrated ACCEPT policy

## Next Step

Build a larger AgentXRD judge-evaluation cohort over binary20 failure buckets
and then wire optional offline-to-Langfuse trace import. Qwen/Detrix RLVR or
SFT experiments should wait until the larger cohort and import path are stable.
