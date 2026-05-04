# AgentXRD_v2 Transition Admission Pack UI Contract — 2026-05-04

Detrix prevents unsupported AI materials-characterization results from becoming accepted lab state or training data.

Langfuse shows what happened. Detrix decides what is safe to learn from.

## Scope

Mission Control may render this pack, but it must not override admission status. Deterministic AgentXRD artifacts are authoritative; Langfuse process traces and Qwen/local-model proposals are advisory until joined to deterministic evidence and replay-promoted.

## Required artifacts

A Detrix AgentXRD pack directory contains:

- `reliability_pack.json` — canonical Materials Characterization Admission Pack summary.
- `transition_admissions.jsonl` — row-level proposed durable transitions and admission decisions.
- `allowed_consequences.jsonl` — consequences Detrix permits for each transition.
- `blocked_consequences.jsonl` — consequences Detrix forbids for each transition.
- `failure_patterns.jsonl` / `failure_pattern_summary.json` — deterministic failure and advisory trace pattern corpus.
- `governed_next_actions.jsonl` — policy-allowed follow-up actions with kill criteria.
- `provenance_dag.jsonl` — artifact provenance readback.
- `promotion_packet.json` — training/promotion gate verdict.
- `drift_replay_report.json` — incumbent-vs-candidate replay status.
- `raw_langfuse_traces.jsonl` and `normalized_observations.jsonl` — advisory process evidence.

## Cards

### Pack summary

Read `reliability_pack.json.summary`:

- AgentXRD row count
- failure-pattern row count
- admission-decision counts
- training-route counts
- top blocker classes
- promotion allowed/blocked

Empty state: if `reliability_pack.json` is missing, show “No admitted Detrix pack found; run `detrix agentxrd build-harness-evidence`.” Do not infer admission from Langfuse alone.

### Langfuse joinability

Read:

- `summary.langfuse_observation_count`
- `summary.joinable_langfuse_trace_count`
- `summary.unjoinable_langfuse_trace_count`
- `failure_pattern_summary.json.missing_join_key_reasons`

Copy: “Langfuse traces are process evidence. Missing sample IDs make them advisory-only until joined to deterministic AgentXRD row packets.”

### Admission and consequences

Read `transition_admissions.jsonl`, `allowed_consequences.jsonl`, and `blocked_consequences.jsonl`.

Show for each row:

- transition type
- proposer
- admission decision
- allowed consequences
- blocked consequences
- reason codes
- training eligibility

Important distinctions:

- `SUPPORT_ONLY` is a domain admission state.
- `eval_only` is a training route.
- Do not collapse them.

### What was safe to accept

Filter `transition_admissions.jsonl` where `admission_decision in ["ACCEPT", "SET"]`.

Display these only if deterministic evidence exists and blocked consequences do not include `MAY_UPDATE_LAB_STATE`.

### What was blocked

Filter rows where blocked consequences include any of:

- `MAY_UPDATE_LAB_STATE`
- `MAY_EXPORT_SFT_POSITIVE`
- `MAY_PROMOTE_MODEL`
- `MAY_PROMOTE_GATE`

Show leading reason code and evidence packet ref.

### What needs more data

Filter `admission_decision == "REQUEST_MORE_DATA"` or allowed consequences include `MUST_REQUEST_MORE_DATA`.

Recommended copy: “Detrix is abstaining because the evidence packet is incomplete, unjoinable, or insufficient for safe promotion.”

### What is support-only

Filter `admission_decision == "SUPPORT_ONLY"`.

Show that `MAY_STORE_EVAL_ONLY` / `DIAGNOSTIC_ONLY` can be allowed while `MAY_EXPORT_SFT_POSITIVE`, `MAY_UPDATE_LAB_STATE`, and promotion remain blocked.

### What can train the local model

Filter `training_eligibility == "sft_positive"` and ensure risk metrics stay within constraints:

- `false_accept_count <= max_false_accepts`
- `unsafe_sft_positive_count <= max_unsafe_sft_positive_rows`
- `promotion_regression_count <= max_promotion_regressions`

If no rows qualify, show: “No safe SFT-positive rows yet. Qwen/local-model output remains shadow/proposer-only.”

### What must be excluded

Filter `training_eligibility == "excluded"` or admission decision `HARD_STOP`.

These rows require human review or hard stop; do not export to training or promotion.

### Replay/promotion safety

Read `drift_replay_report.json` and `promotion_packet.json`.

Display:

- before/after metrics
- deltas
- release block status
- promotion allowed
- promotion block reasons

Copy: “Promotion requires held-out replay without false-accept or unsafe-training regression.”

## CLI readback

```bash
uv run detrix agentxrd show-pack /tmp/detrix-agentxrd-reliability-pack
uv run detrix agentxrd show-next-actions /tmp/detrix-agentxrd-reliability-pack --limit 5
uv run detrix agentxrd replay-report /tmp/detrix-agentxrd-reliability-pack --format md
```

## Demo-safe copy

- “Your agents work in demos. Detrix makes them work in production.”
- “Langfuse shows what happened. Detrix decides what is safe to learn from.”
- “OpenPipe trains on traces. Detrix trains on traces that survived domain physics evaluation.”
- “Built on pi. Works with any LLM provider. Skills distribute to 35+ products via Agent Skills standard.”

## Non-goals

- No live Langfuse mutation from this pack.
- No Mission Control admission override.
- No Qwen/local-model reliability claim without held-out replay proof.
- No promotion from support-only or unjoinable process evidence.
